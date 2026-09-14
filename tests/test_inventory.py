import io
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from PIL import Image
from sqlalchemy import select, func

from inventory import (Inventory, InventoryError, ROOT, cents, metadata, movements,
                       password_hash, products, sale_items, sales, verify_password)


@pytest.fixture
def db(tmp_path):
    result = Inventory(f"sqlite:///{(tmp_path / 'test.db').as_posix()}")
    result.seed()
    return result


def cart(qty=1, price=300, sku="A06-01"):
    return {sku: {"quantity": qty, "price_cents": price}}


def sell(db, items=None, key="request-1"):
    return db.confirm_sale(items or cart(), "Cliente de prueba", "Efectivo", "", key)


def test_catalog_totals_and_every_reference(db):
    items = db.list_products()
    assert len(items) == 24
    assert sum(p["stock"] for p in items) == 360
    assert sum(p["stock"] * p["price_cents"] for p in items) == 90250
    assert all((ROOT / p["image_path"]).is_file() for p in items)
    assert db.get_product("A17-03")["compatibility"] == "GALAXY A16/A17/A26"
    assert db.get_product("IP17PM-01")["compatibility"] == "iPhone 17PM/ 18PM"


def test_sale_decrements_stock_and_has_price_snapshot(db):
    sale_id = sell(db, cart(3))
    assert db.get_product("A06-01")["stock"] == 7
    sale = db.get_sale(sale_id)
    assert sale["total_cents"] == 900
    assert sale["items"][0]["quantity"] == 3
    assert db.list_movements("A06-01")[0]["balance"] == 7


def test_catalog_does_not_reset_after_sale_or_restart(db):
    sell(db)
    assert db.seed() is False
    restarted = Inventory(str(db.engine.url))
    restarted.seed()
    assert restarted.get_product("A06-01")["stock"] == 9


def test_idempotent_sale_and_void(db):
    first = sell(db, cart(2))
    assert sell(db, cart(2)) == first
    assert db.get_product("A06-01")["stock"] == 8
    assert len(db.list_sales()) == 1
    assert db.void_sale(first, "Prueba") is True
    assert db.void_sale(first, "Prueba otra vez") is False
    assert db.get_product("A06-01")["stock"] == 10


def test_multi_product_sale_rolls_back_everything(db):
    with pytest.raises(InventoryError):
        sell(db, {**cart(2), **cart(11, sku="A06-02")})
    assert db.get_product("A06-01")["stock"] == 10
    assert db.list_sales() == []
    assert len(db.list_movements()) == 24


def test_concurrent_sales_cannot_oversell(db):
    barrier = threading.Barrier(2)
    def attempt(n):
        barrier.wait()
        try:
            sell(db, cart(7), key=f"concurrent-{n}")
            return True
        except InventoryError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == [False, True]
    assert db.get_product("A06-01")["stock"] == 3
    assert len(db.list_sales()) == 1


def test_concurrent_same_sale_is_not_duplicated(db):
    barrier = threading.Barrier(2)
    def attempt(_):
        barrier.wait()
        return sell(db, cart(2))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert results[0] == results[1]
    assert db.get_product("A06-01")["stock"] == 8


def test_concurrent_void_returns_stock_once(db):
    sale_id = sell(db, cart(2))
    barrier = threading.Barrier(2)
    def attempt(_):
        barrier.wait()
        return db.void_sale(sale_id, "Devolución")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, range(2)))
    assert sorted(results) == [False, True]
    assert db.get_product("A06-01")["stock"] == 10


def test_adjustments_are_audited_idempotent_and_never_negative(db):
    db.adjust_stock("A06-01", 5, "Reposición", "replenish-1")
    db.adjust_stock("A06-01", 5, "Reposición", "replenish-1")
    assert db.get_product("A06-01")["stock"] == 15
    with pytest.raises(InventoryError):
        db.adjust_stock("A06-01", -16, "Pérdida", "adjust-2")
    assert db.get_product("A06-01")["stock"] == 15
    assert db.list_movements("A06-01")[0]["reason"] == "Reposición"


@pytest.mark.parametrize("qty", [0, -1, 1.5, True, "2"])
def test_bad_quantity_rejected(db, qty):
    with pytest.raises(InventoryError):
        sell(db, cart(qty))
    assert db.list_sales() == []


def test_stale_price_and_archived_product_rejected(db):
    p = db.get_product("A06-01")
    p["price_cents"] = 450
    db.save_product(p, p["version"])
    with pytest.raises(InventoryError):
        sell(db)
    p = db.get_product("A06-01")
    p["active"] = False
    db.save_product(p, p["version"])
    with pytest.raises(InventoryError):
        sell(db, cart(price=450))
    assert db.get_product("A06-01")["stock"] == 10


def test_edit_rejects_stale_version_and_does_not_overwrite_stock(db):
    p = db.get_product("A06-01")
    sell(db)
    with pytest.raises(InventoryError):
        db.save_product(p, p["version"])
    p = db.get_product("A06-01")
    p["name"] = "Nombre editado"
    p["stock"] = 1000
    db.save_product(p, p["version"])
    assert db.get_product("A06-01")["stock"] == 9


def test_new_category_photo_survives_backup_restore(db, tmp_path):
    photo = io.BytesIO()
    Image.new("RGB", (30, 30), "blue").save(photo, format="PNG")
    db.save_product(dict(sku="CABLE-01", name="Cable USB", compatibility="USB-C", brand="Genérica",
        category="Cables", price_cents=225, stock=40), image=photo.getvalue())
    sell(db)
    raw = db.backup()
    fresh = Inventory(f"sqlite:///{(tmp_path / 'restored.db').as_posix()}")
    fresh.restore_into_empty(raw)
    assert fresh.get_product("CABLE-01")["image_data"] == db.get_product("CABLE-01")["image_data"]
    assert fresh.get_product("A06-01")["stock"] == 9
    assert fresh.list_sales() == db.list_sales()
    assert fresh.seed() is False
    with pytest.raises(InventoryError):
        fresh.restore_into_empty(raw)


def test_currency_and_password_validation():
    assert cents("2.25") == 225
    for value in ("-1", "nan", "Infinity", "1.005", "bad"):
        with pytest.raises(InventoryError):
            cents(value)
    encoded = password_hash("a-secure-test-password")
    assert verify_password("a-secure-test-password", encoded)
    assert not verify_password("wrong", encoded)
    assert not verify_password("anything", "malformed")


def test_production_refuses_ephemeral_database():
    with pytest.raises(InventoryError):
        Inventory("sqlite:///:memory:", production=True)
