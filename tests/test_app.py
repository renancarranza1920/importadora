"""Exercise the actual Streamlit forms on isolated disposable databases."""
import pytest
from streamlit.testing.v1 import AppTest

from inventory import Inventory, ROOT, password_hash

PASSWORD = "test-password-123456"


def button(app, prefix):
    return next(b for b in app.button if b.label.startswith(prefix))


def field(elements, label):
    return next(e for e in elements if e.label == label)


def no_errors(app):
    assert not app.exception, [e.message for e in app.exception]
    return app


@pytest.fixture
def ui(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'ui.db').as_posix()}"
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", password_hash(PASSWORD))
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    app.query_params["vista"] = "admin"
    no_errors(app.run())
    app.radio(key="nav").set_value("Catálogo").run()  # Exercise the internal catalog preview too.
    return app, Inventory(url)


def login(app):
    app.radio(key="nav").set_value("Acceso administrador").run()
    field(app.text_input, "Contraseña").set_value(PASSWORD)
    no_errors(button(app, "Entrar").click().run())


def navigate(app, page):
    return no_errors(app.radio(key="nav").set_value(page).run())


def test_public_catalog_login_required_and_compatibility_search(ui):
    app, db = ui
    assert not [b for b in app.button if b.key and b.key.startswith("add_")]
    app.text_input(key="search").set_value("Galaxy A26").run()
    assert len(app.expander) == 4
    app.text_input(key="search").set_value("iPhone 14").run()
    assert len(app.expander) == 2
    navigate(app, "Acceso administrador")
    field(app.text_input, "Contraseña").set_value("wrong")
    button(app, "Entrar").click().run()
    assert "Contraseña incorrecta" in app.error[0].value
    assert not db.list_sales()


def test_real_sale_form_confirmation_and_logout(ui):
    app, db = ui
    login(app)
    app.button(key="add_A06-01").click().run()
    navigate(app, "Nueva venta")
    app.number_input(key="qty_A06-01").set_value(3).run()
    button(app, "Confirmar venta").click().run()
    assert not db.list_sales()
    assert any("Marca la confirmación" in e.value for e in app.error)
    field(app.text_input, "Cliente (opcional)").set_value("Cliente UI")
    app.checkbox[0].check()
    no_errors(button(app, "Confirmar venta").click().run())
    assert db.get_product("A06-01")["stock"] == 7
    assert len(db.list_sales()) == 1
    assert db.list_sales()[0]["customer"] == "Cliente UI"
    assert any("confirmada" in s.value for s in app.success)
    assert app.session_state["cart"] == {}
    assert any(e.label == "Descargar ticket en imagen" for e in app.get("download_button"))
    assert "download_sale" not in app.session_state
    no_errors(button(app, "Cerrar sesión").click().run())
    assert "Inventario" not in app.radio(key="nav").options


def test_add_after_visiting_cart_preserves_quantity(ui):
    app, _ = ui
    login(app)
    app.button(key="add_A06-01").click().run()
    navigate(app, "Nueva venta")
    assert app.number_input[0].value == 1
    navigate(app, "Catálogo")
    app.button(key="add_A06-01").click().run()
    navigate(app, "Nueva venta")
    assert app.number_input[0].value == 2


def test_inventory_adjust_and_all_private_pages(ui):
    app, db = ui
    login(app)
    navigate(app, "Inventario")
    field(app.radio, "Gestión").set_value("Reponer / ajustar").run()
    field(app.number_input, "Unidades del movimiento").set_value(8)
    field(app.text_input, "Motivo obligatorio").set_value("Llegada de mercancía")
    app.checkbox[0].check()
    no_errors(button(app, "Registrar movimiento").click().run())
    assert db.get_product("A06-01")["stock"] == 18
    for page in ("Ventas", "Movimientos", "Ayuda y respaldo"):
        navigate(app, page)


def test_create_different_product_category(ui):
    app, db = ui
    login(app)
    navigate(app, "Inventario")
    field(app.radio, "Gestión").set_value("Nuevo artículo").run()
    field(app.text_input, "Referencia única").set_value("USB-01")
    field(app.text_input, "Nombre del artículo").set_value("Cable USB")
    field(app.text_input, "Marca").set_value("Genérica")
    field(app.text_input, "Categoría").set_value("Cables")
    field(app.number_input, "Precio de venta (USD)").set_value(2.25)
    field(app.number_input, "Unidades iniciales").set_value(25)
    no_errors(button(app, "Crear artículo").click().run())
    product = db.get_product("USB-01")
    assert product["category"] == "Cables"
    assert product["stock"] == 25
    assert product["price_cents"] == 225


def test_void_via_ui_restocks(ui):
    app, db = ui
    sale = db.confirm_sale({"A06-01": {"quantity": 2, "price_cents": 300}}, "Cliente", "Efectivo", "", "void-ui")
    login(app)
    navigate(app, "Ventas")
    field(app.text_input, "Motivo de anulación").set_value("Devolución completa")
    app.checkbox[0].check()
    no_errors(button(app, "Anular y reingresar").click().run())
    assert db.get_product("A06-01")["stock"] == 10
    assert db.get_sale(sale)["status"] == "voided"


def test_edit_concurrent_change_requires_reload(ui):
    app, db = ui
    login(app)
    navigate(app, "Inventario")
    field(app.radio, "Gestión").set_value("Editar artículo").run()
    field(app.text_input, "Nombre del artículo").set_value("Cambio de nombre")
    db.adjust_stock("A06-01", 1, "Otra sesión", "other-session")
    no_errors(button(app, "Guardar cambios").click().run())
    assert any("Este artículo cambió" in e.value for e in app.error)
    assert db.get_product("A06-01")["name"] == "GALAXY A06"


def test_production_missing_configuration_is_closed(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "")
    app = no_errors(AppTest.from_file(str(ROOT / "app.py")).run())
    assert app.error
    assert not app.radio


def test_catalog_filters_reset_page_and_empty_results(ui):
    app, _ = ui
    app.selectbox(key="catalog_page").set_value(2).run()
    app.selectbox(key="catalog_order").set_value("Mayor precio").run()
    assert app.selectbox(key="catalog_page").value == 1
    app.text_input(key="search").set_value("modelo inexistente").run()
    assert not app.expander
    no_errors(button(app, "Limpiar filtros").click().run())
    assert app.text_input(key="search").value == ""
    assert app.selectbox(key="catalog_order").value == "Referencia"
    assert len(app.expander) == 12


def test_catalog_search_ignores_accents(ui):
    app, db = ui
    db.save_product(dict(sku="USB-TEST", name="Cable edición especial", compatibility="USB",
                         brand="Genérica", category="Cables", price_cents=200,
                         low_stock=1, stock=5, notes="", active=True))
    no_errors(app.text_input(key="search").set_value("generica edicion").run())
    assert len(app.expander) == 1


def test_visual_inventory_shortcuts_and_real_photo_cart(ui):
    from test_photos import photo
    app, db = ui
    p = db.get_product("A06-01")
    db.save_product(p, p["version"], real_photos=[photo(), photo()])
    login(app)
    navigate(app, "Inventario")
    no_errors(app.button(key="edit_A06-01").click().run())
    assert field(app.text_input, "Referencia única").value == "A06-01"
    assert len(app.multiselect[0].options) == 2
    navigate(app, "Catálogo")
    app.button(key="add_A06-01").click().run()
    navigate(app, "Nueva venta")
    assert any(e.label == "Foto real · 2 fotos" for e in app.expander)


def test_edit_image_zoom_and_reopen(ui):
    app, db = ui
    login(app)
    navigate(app, "Inventario")
    app.button(key="edit_A06-01").click().run()
    field(app.slider, "Zoom de la imagen (%)").set_value(150).run()
    field(app.slider, "Centro horizontal (%)").set_value(25).run()
    no_errors(button(app, "Guardar cambios").click().run())
    assert db.get_product("A06-01")["image_zoom"] == 150
    assert field(app.slider, "Zoom de la imagen (%)").value == 150
    assert field(app.slider, "Centro horizontal (%)").value == 25


def test_public_request_shortage_admin_review_and_sale(ui):
    app, db = ui
    assert "Solicitudes" not in app.radio(key="nav").options
    app.button(key="request_add_A06-01").click().run()
    navigate(app, "Mi pedido")
    field(app.number_input, "Cantidad · A06-01").set_value(8).run()
    field(app.text_input, "Tu nombre (opcional)").set_value("Ana UI")
    no_errors(button(app, "Pedir por WhatsApp").click().run())
    assert db.get_product("A06-01")["stock"] == 10
    assert len(db.list_inquiries()) == 1
    assert "50373113611" in app.get("link_button")[0].proto.url
    login(app)
    db.adjust_stock("A06-01", -5, "Cambio de stock", "ui-shortage")
    navigate(app, "Solicitudes")
    assert button(app, "Confirmar venta del pedido").disabled
    no_errors(button(app, "Usar disponibles (5)").click().run())
    no_errors(button(app, "Guardar ajustes del pedido").click().run())
    assert not button(app, "Confirmar venta del pedido").disabled
    field(app.checkbox, "El cliente aceptó estos productos y precios; recibí el pago y confirmo la venta.").check()
    no_errors(button(app, "Confirmar venta del pedido").click().run())
    assert db.get_product("A06-01")["stock"] == 0
    assert db.list_inquiries()[0]["status"] == "converted"
    assert app.radio(key="nav").value == "Nueva venta"
    assert any(e.label == "Descargar ticket en imagen" for e in app.get("download_button"))


def test_public_cart_sold_out_and_changed_price(ui):
    app, db = ui
    app.button(key="request_add_A06-01").click().run()
    p = db.get_product("A06-01")
    db.save_product(dict(p, price_cents=400), p["version"])
    navigate(app, "Mi pedido")
    assert button(app, "Pedir por WhatsApp").disabled
    field(app.checkbox, "Aceptar precio actual").check().run()
    assert not button(app, "Pedir por WhatsApp").disabled
    db.adjust_stock("A06-01", -10, "Agotado", "empty-public")
    no_errors(app.run())
    assert button(app, "Pedir por WhatsApp").disabled
    no_errors(button(app, "Usar disponibles (0)").click().run())
    assert not db.list_inquiries()
    assert not db.list_sales()


def test_private_request_alternative_and_cancel(ui):
    app, db = ui
    row = db.create_inquiry({"A06-01": dict(quantity=1, price_cents=300)}, "Cliente", "+50370000000", "alt", "browser")
    login(app)
    navigate(app, "Solicitudes")
    no_errors(button(app, "Guardar ajustes y agregar alternativa").click().run())
    import json
    assert len(json.loads(db.list_inquiries()[0]["items"])) == 2
    field(app.checkbox, "Confirmo que deseo cancelar esta solicitud.").check()
    no_errors(button(app, "Cancelar pedido").click().run())
    assert db.list_inquiries()[0]["status"] == "cancelled"
    assert db.get_product("A06-01")["stock"] == 10


def test_separate_storefront_needs_no_phone_or_login(ui):
    app, db = ui
    app.query_params["vista"] = "pedidos"
    no_errors(app.run())
    assert not app.sidebar.radio
    assert app.radio(key="public_nav").options == ["Catálogo", "Mi pedido (0)"]
    assert not any(e.label == "Acceso administrador" for e in app.button)
    app.button(key="request_add_A06-01").click().run()
    app.radio(key="public_nav").set_value("Mi pedido").run()
    assert not any("teléfono" in e.label.lower() or "código de país" in e.label for e in app.text_input)
    assert not app.checkbox
    no_errors(button(app, "Pedir por WhatsApp").click().run())
    row = db.list_inquiries()[0]
    assert row["phone"] == "" and row["customer"] == "Cliente de WhatsApp"
    assert db.get_product("A06-01")["stock"] == 10
    assert app.get("link_button")[0].proto.url.startswith("https://wa.me/50373113611?")
