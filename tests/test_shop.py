"""Public model selection, fixed help and wholesale ordering behavior."""
from shop import available_models, assistant_markup, model_names
from test_app import button, field, navigate, no_errors, ui


def test_public_model_filter_only_shows_explicit_compatibility(ui):
    app, _ = ui
    app.selectbox(key="catalog_model").set_value("Galaxy A26").run()
    assert {b.key for b in app.button if b.key and b.key.startswith("request_add_")} == {
        f"request_add_A17-{n:02}" for n in range(3, 7)}
    app.selectbox(key="catalog_model").set_value("Galaxy A17").run()
    assert len([b for b in app.button if b.key and b.key.startswith("request_add_")]) == 6
    button(app, "Limpiar filtros").click().run()
    assert app.selectbox(key="catalog_model").value == "Todos los modelos"


def test_public_order_minimum_blocks_writes_until_three_units(ui):
    app, store = ui
    app.button(key="request_add_A06-01").click().run()
    navigate(app, "Mi pedido")
    assert button(app, "Pedir por WhatsApp").disabled
    field(app.number_input, "Cantidad · A06-01").set_value(2).run()
    assert button(app, "Pedir por WhatsApp").disabled
    assert not store.list_inquiries()
    field(app.number_input, "Cantidad · A06-01").set_value(3).run()
    assert not button(app, "Pedir por WhatsApp").disabled
    no_errors(button(app, "Pedir por WhatsApp").click().run())
    assert len(store.list_inquiries()) == 1
    assert store.get_product("A06-01")["stock"] == 10


def test_campaign_link_filters_catalog_without_resetting_customer_choice(ui):
    app, _ = ui
    app.query_params.update(vista="pedidos", modelo="Galaxy A13", ref="A13-02")
    no_errors(app.run())
    assert app.selectbox(key="catalog_model").value == "Galaxy A13"
    assert [b.key for b in app.button if b.key and b.key.startswith("request_add_")] == ["request_add_A13-02"]
    button(app, "Limpiar filtros").click().run()
    assert app.selectbox(key="catalog_model").value == "Todos los modelos"
    assert app.text_input(key="search").value == ""


def test_fixed_help_uses_current_stock_and_escapes_product_labels():
    products = [dict(name="Galaxy A06", stock=0, active=True),
                dict(name="Galaxy A16/A17/A26", stock=2, active=True),
                dict(name='<script>bad</script>', stock=2, active=False)]
    assert available_models(products) == ["Galaxy A16", "Galaxy A17", "Galaxy A26"]
    assert model_names(dict(compatibility="iPhone 13/14")) == ["iPhone 13", "iPhone 14"]
    markup = assistant_markup(products, "50373113611")
    assert "Galaxy A06" not in markup and "Galaxy A26" in markup
    assert "sin local físico" in markup and "3 unidades" in markup
    assert "<script>" not in markup
    assert 'class="shop-faq"' in markup and "https://wa.me/50373113611?" in markup
