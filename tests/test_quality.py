"""Regression checks for the quality audit, using disposable databases."""
import json
import io

import pytest
from PIL import Image

import inventory
from inventory import InventoryError
from test_app import button, field, login, navigate, no_errors, ui
from test_inventory import db, sell, cart


def test_add_another_item_preserves_price_until_accepted(ui):
    app, store = ui
    login(app)
    app.button(key="add_A06-01").click().run()
    p = store.get_product("A06-01")
    store.save_product(dict(p, price_cents=400), p["version"])
    app.run()
    app.button(key="add_A06-01").click().run()
    navigate(app, "Nueva venta")
    assert app.session_state["cart"]["A06-01"] == dict(quantity=2, price_cents=300)
    assert button(app, "Confirmar venta").disabled
    no_errors(button(app, "Aceptar precio actualizado").click().run())
    assert app.session_state["cart"]["A06-01"]["price_cents"] == 400
    assert not button(app, "Confirmar venta").disabled


def test_private_cart_stock_shortcut_and_navigation(ui):
    app, store = ui
    login(app)
    app.button(key="add_A06-01").click().run()
    navigate(app, "Nueva venta")
    app.number_input(key="qty_A06-01").set_value(8).run()
    store.adjust_stock("A06-01", -5, "Otra venta", "quality-shortage")
    app.button(key="refresh_sale").click().run()
    assert button(app, "Confirmar venta").disabled
    no_errors(button(app, "Usar disponibles (5)").click().run())
    assert app.session_state["cart"]["A06-01"]["quantity"] == 5
    assert not button(app, "Confirmar venta").disabled
    button(app, "Seguir agregando productos").click().run()
    assert app.radio(key="nav").value == "Catálogo"


def test_invalid_product_preserves_fields_until_corrected(ui):
    app, store = ui
    login(app)
    navigate(app, "Inventario")
    app.radio(key="inventory_action").set_value("Nuevo artículo").run()
    field(app.text_input, "Referencia única").set_value("QUALITY-01")
    field(app.text_input, "Nombre del artículo").set_value("Protector de prueba")
    field(app.number_input, "Unidades iniciales").set_value(7)
    no_errors(button(app, "Crear artículo").click().run())
    assert app.error
    assert field(app.text_input, "Nombre del artículo").value == "Protector de prueba"
    assert field(app.number_input, "Unidades iniciales").value == 7
    field(app.text_input, "Marca").set_value("Genérica")
    no_errors(button(app, "Crear artículo").click().run())
    assert store.get_product("QUALITY-01")["stock"] == 7
    assert field(app.text_input, "Referencia única").value == ""


def test_adjustment_keeps_invalid_input_and_resets_after_success(ui):
    app, store = ui
    login(app)
    navigate(app, "Inventario")
    app.radio(key="inventory_action").set_value("Reponer / ajustar").run()
    assert not any(e.label == "Selecciona el artículo" for e in app.selectbox)
    assert not [e for e in app.number_input if e.label == "Unidades del movimiento"]
    app.button(key="inventory_sku_choose_A06-01").click().run()
    field(app.number_input, "Unidades del movimiento").set_value(8)
    field(app.text_input, "Motivo obligatorio").set_value("Reposición de prueba")
    no_errors(button(app, "Registrar movimiento").click().run())
    assert store.get_product("A06-01")["stock"] == 10
    assert field(app.number_input, "Unidades del movimiento").value == 8
    app.checkbox[0].check()
    no_errors(button(app, "Registrar movimiento").click().run())
    assert store.get_product("A06-01")["stock"] == 18
    assert field(app.number_input, "Unidades del movimiento").value == 1
    assert not app.checkbox[0].value
    field(app.number_input, "Unidades del movimiento").set_value(9)
    app.button(key="inventory_sku_choose_A06-02").click().run()
    assert field(app.number_input, "Unidades del movimiento").value == 1


def test_inventory_search_page_and_accented_category(ui):
    app, store = ui
    from test_app import add_extra_products
    add_extra_products(store, 7)
    login(app)
    navigate(app, "Inventario")
    app.button(key="inventory_page_next").click().run()
    assert app.session_state["inventory_page"] == 2
    app.text_input(key="inventory_search").set_value("protectores").run()
    assert app.session_state["inventory_page"] == 1
    p = store.get_product("A06-01")
    store.save_product(dict(p, brand="Genérica", category="Edición especial"), p["version"])
    app.text_input(key="inventory_search").set_value("generica edicion").run()
    assert len([b for b in app.button if b.key and b.key.startswith("edit_")]) == 1
    no_errors(button(app, "Limpiar filtros de inventario").click().run())
    assert app.text_input(key="inventory_search").value == ""


def test_public_removal_immediately_updates_navigation(ui):
    app, _ = ui
    app.query_params["vista"] = "pedidos"
    app.run()
    app.button(key="request_add_A06-01").click().run()
    app.radio(key="public_nav").set_value("Mi pedido").run()
    no_errors(button(app, "Quitar del pedido").click().run())
    assert app.session_state["public_cart"] == {}
    assert app.radio(key="public_nav").options == ["Catálogo", "Mi pedido (0)"]
    assert not any(b.label == "Pedir por WhatsApp" for b in app.button)
    assert button(app, "Ver catálogo")


def test_new_order_keeps_previous_whatsapp_link_in_collapsed_history(ui):
    app, store = ui
    app.button(key="request_add_A06-01").click().run()
    navigate(app, "Mi pedido")
    button(app, "Pedir por WhatsApp").click().run()
    button(app, "Ver catálogo").click().run()
    app.button(key="request_add_A06-02").click().run()
    navigate(app, "Mi pedido")
    previous = next(e for e in app.expander if e.label == "Solicitud anterior")
    assert not previous.proto.expanded
    assert not button(app, "Pedir por WhatsApp").disabled
    assert len(store.list_inquiries()) == 1


def test_void_over_stock_limit_rolls_back_sale_and_all_products(db):
    sale = sell(db, {**cart(2), **cart(2, sku="A06-02")})
    db.adjust_stock("A06-02", 9999992, "Reposición máxima", "quality-max")
    before = db.list_movements()
    with pytest.raises(InventoryError, match="límite de existencias"):
        db.void_sale(sale, "Devolución")
    assert db.get_sale(sale)["status"] == "confirmed"
    assert db.get_product("A06-01")["stock"] == 8
    assert db.get_product("A06-02")["stock"] == 10000000
    assert db.list_movements() == before


def test_movements_remain_in_balance_order_when_clock_repeats(db, monkeypatch):
    stamp = db.list_movements("A06-01")[0]["created_at"]
    monkeypatch.setattr(inventory, "now", lambda: stamp)
    db.adjust_stock("A06-01", 3, "Entrada", "same-time-1")
    db.adjust_stock("A06-01", -2, "Salida", "same-time-2")
    rows = db.list_movements("A06-01")
    assert [r["balance"] for r in rows] == [11, 13, 10]
    assert rows[0]["created_at"] > rows[1]["created_at"] > rows[2]["created_at"]


def test_inquiries_reject_unconfirmable_totals_without_writing(db):
    p = db.get_product("A06-01")
    db.save_product(dict(p, price_cents=999999999), p["version"])
    with pytest.raises(InventoryError, match="total del pedido"):
        db.create_inquiry(cart(3, 999999999), "Ana", "", "huge", "test")
    assert not db.list_inquiries()
    row = db.create_inquiry(cart(1, 999999999), "Ana", "", "allowed", "test")
    items = json.loads(row["items"])
    items["A06-01"]["quantity"] = 3
    with pytest.raises(InventoryError, match="total del pedido"):
        db.update_inquiry(row["id"], row["version"], items, "pending")
    assert db.list_inquiries()[0]["items"] == row["items"]
    assert db.get_product("A06-01")["stock"] == 10


def test_transparent_upload_has_white_background():
    raw = io.BytesIO()
    source = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    source.save(raw, "PNG")
    with Image.open(io.BytesIO(inventory.clean_image(raw.getvalue()))) as cleaned:
        assert cleaned.mode == "RGB"
        assert cleaned.getpixel((50, 50)) == (255, 255, 255)


def test_gallery_edit_preserves_existing_image_bytes(db):
    source = io.BytesIO()
    # A detailed image exposes progressive JPEG loss that a solid color hides.
    Image.effect_noise((100, 100), 100).save(source, "PNG")
    p = db.get_product("A06-01")
    db.save_product(p, p["version"], real_photos=[source.getvalue()])
    original = db.list_photos(p["sku"])[0]["image_data"]
    p = db.get_product(p["sku"])
    db.save_product(p, p["version"], real_photos=[original, source.getvalue()])
    assert db.list_photos(p["sku"])[0]["image_data"] == original
