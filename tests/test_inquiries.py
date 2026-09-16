import json
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlparse

import pytest

from inventory import Inventory, InventoryError
from order_views import whatsapp_link


@pytest.fixture
def db(tmp_path):
    db = Inventory(f"sqlite:///{(tmp_path / 'requests.db').as_posix()}")
    db.seed()
    return db


def request(db, key="request", quantity=3):
    return db.create_inquiry({"A06-01": dict(quantity=quantity, price_cents=300)}, "Ana", "+503 7000 0000", key, "browser")


def confirm(db, row):
    return db.confirm_sale(json.loads(row["items"]), row["customer"], "Efectivo", "", "ignored",
                           inquiry_id=row["id"], inquiry_version=row["version"])


def test_pending_request_does_not_change_stock_and_retries_are_unique(db):
    row = request(db)
    assert request(db)["id"] == row["id"]
    assert len(db.list_inquiries()) == 1
    assert not db.list_sales()
    assert db.get_product("A06-01")["stock"] == 10
    link = urlparse(whatsapp_link(row))
    assert link.netloc == "wa.me" and link.path == "/50373113611"
    text = parse_qs(link.query)["text"][0]
    assert "$9.00" in text and "A06-01" in text and "Ana" in text


def test_shortage_then_adjust_then_confirm_once(db):
    row = request(db, quantity=8)
    db.adjust_stock("A06-01", -5, "Otra venta", "other")
    with pytest.raises(InventoryError):
        confirm(db, row)
    assert db.list_inquiries()[0]["status"] == "pending"
    assert not db.list_sales()
    cart = json.loads(row["items"])
    cart["A06-01"]["quantity"] = 5
    db.update_inquiry(row["id"], row["version"], cart, "contacted")
    updated = db.list_inquiries()[0]
    assert json.loads(updated["original_items"])["A06-01"]["quantity"] == 8
    sale = confirm(db, updated)
    assert confirm(db, updated) == sale
    assert db.get_product("A06-01")["stock"] == 0
    assert db.list_inquiries()[0]["sale_id"] == sale


def test_cancelled_or_concurrently_edited_request_cannot_confirm(db):
    row = request(db)
    db.update_inquiry(row["id"], row["version"], json.loads(row["items"]), "cancelled")
    with pytest.raises(InventoryError):
        confirm(db, row)
    assert db.get_product("A06-01")["stock"] == 10


def test_simultaneous_conversion_creates_one_sale(db):
    row = request(db)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(confirm, db, row) for _ in range(2)]
        results = []
        for future in futures:
            try:
                results.append(future.result())
            except InventoryError:
                pass  # A stale review is also a safe outcome.
    assert results and len(set(results)) == 1
    assert len(db.list_sales()) == 1
    assert db.get_product("A06-01")["stock"] == 7


def test_price_change_blocks_and_requests_survive_backup(db, tmp_path):
    row = request(db)
    p = db.get_product("A06-01")
    db.save_product(dict(p, price_cents=400), p["version"])
    with pytest.raises(InventoryError):
        confirm(db, row)
    with pytest.raises(InventoryError):
        request(db, key="new")
    restored = Inventory(f"sqlite:///{(tmp_path / 'restore.db').as_posix()}")
    restored.restore_into_empty(db.backup())
    assert restored.list_inquiries() == db.list_inquiries()


def test_request_limits_and_contact_validation(db):
    for i in range(5):
        request(db, key=str(i))
    with pytest.raises(InventoryError):
        request(db, key="sixth")
    with pytest.raises(InventoryError):
        db.create_inquiry({"A06-01": dict(quantity=1, price_cents=300)}, "Ana", "--------", "bad", "other-browser")
