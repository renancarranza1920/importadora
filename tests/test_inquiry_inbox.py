import json

from test_app import button, login, navigate, no_errors, ui


def inquiry(db, customer, key):
    return db.create_inquiry({"A06-01": dict(quantity=1, price_cents=300)}, customer, "", key, f"browser-{key}")


def visible_requests(app):
    return [b.key.removeprefix("open_inquiry_") for b in app.button if b.key and b.key.startswith("open_inquiry_")]


def open_request(app, row):
    return no_errors(app.button(key=f"open_inquiry_{row['id']}").click().run())


def test_inbox_starts_with_new_requests_and_filters_all_states(ui):
    app, db = ui
    pending = inquiry(db, "Ana", "pending")
    contacted = inquiry(db, "Beatriz", "contacted")
    cancelled = inquiry(db, "Carla", "cancelled")
    converted = inquiry(db, "Diana", "converted")
    for row, status in ((contacted, "contacted"), (cancelled, "cancelled")):
        db.update_inquiry(row["id"], row["version"], json.loads(row["items"]), status)
    db.confirm_sale(json.loads(converted["items"]), converted["customer"], "Efectivo", "", "converted-sale",
                    inquiry_id=converted["id"], inquiry_version=converted["version"])
    before = db.list_inquiries()
    login(app)
    navigate(app, "Solicitudes")
    assert visible_requests(app) == [pending["id"]]
    assert not app.selectbox  # No combo for selecting requests or their state.
    assert "Nuevas (1)" in app.radio(key="_inquiry_status").options
    assert "Todas (4)" in app.radio(key="_inquiry_status").options
    assert "inquiry_selected" not in app.session_state
    for row, status in ((contacted, "contacted"), (cancelled, "cancelled"), (converted, "converted")):
        no_errors(app.radio(key="_inquiry_status").set_value(status).run())
        assert visible_requests(app) == [row["id"]]
        open_request(app, row)
        if status == "converted":
            assert any(item.label == "Descargar ticket en imagen" for item in app.get("download_button"))
        if status == "cancelled":
            assert any("Solicitud cancelada" in item.value for item in app.info)
        no_errors(button(app, "Volver a solicitudes").click().run())
        assert app.radio(key="_inquiry_status").value == status
    assert db.list_inquiries() == before


def test_detail_navigation_keeps_filtered_queue_and_return_search(ui):
    app, db = ui
    rows = [inquiry(db, "José Pérez", f"jose-{i}") for i in range(3)]
    inquiry(db, "Otro cliente", "outside-search")
    login(app)
    navigate(app, "Solicitudes")
    no_errors(app.text_input(key="_inquiry_search").set_value("jose perez").run())
    expected = [row["id"] for row in sorted(rows, key=lambda r: (r["created_at"], r["id"]), reverse=True)]
    assert visible_requests(app) == expected
    app.button(key=f"open_inquiry_{expected[0]}").click().run()
    assert app.button(key="inquiry_previous").disabled
    no_errors(app.button(key="inquiry_next").click().run())
    assert app.session_state["inquiry_selected"] == expected[1]
    no_errors(app.button(key="inquiry_next").click().run())
    assert app.session_state["inquiry_selected"] == expected[2]
    assert app.button(key="inquiry_next").disabled
    no_errors(app.button(key="inquiry_previous").click().run())
    assert app.session_state["inquiry_selected"] == expected[1]
    no_errors(button(app, "Volver a solicitudes").click().run())
    assert app.text_input(key="_inquiry_search").value == "jose perez"
    assert visible_requests(app) == expected


def test_inbox_pagination_returns_to_same_page_and_search_resets_it(ui):
    app, db = ui
    for i in range(13):
        inquiry(db, f"Cliente {i}", f"page-{i}")
    login(app)
    navigate(app, "Solicitudes")
    first_page = visible_requests(app)
    assert len(first_page) == 12
    app.button(key="inquiry_next_page").click().run()
    second_page = visible_requests(app)
    assert len(second_page) == 1 and not set(first_page) & set(second_page)
    assert app.button(key="inquiry_next_page").disabled
    app.button(key=f"open_inquiry_{second_page[0]}").click().run()
    button(app, "Volver a solicitudes").click().run()
    assert visible_requests(app) == second_page
    assert app.session_state["inquiry_page"] == 2
    no_errors(app.text_input(key="_inquiry_search").set_value(first_page[0][:8]).run())
    assert visible_requests(app) == [first_page[0]]
    assert app.session_state["inquiry_page"] == 1
    no_errors(button(app, "Limpiar búsqueda").click().run())
    assert visible_requests(app) == first_page
    no_errors(app.radio(key="_inquiry_status").set_value("cancelled").run())
    assert not visible_requests(app)
    assert any("No hay solicitudes" in item.value for item in app.info)


def test_status_change_stays_open_then_moves_to_its_inbox(ui):
    app, db = ui
    row = inquiry(db, "Ana", "move-state")
    login(app)
    navigate(app, "Solicitudes")
    open_request(app, row)
    no_errors(button(app, "Marcar como contactado").click().run())
    assert app.session_state["inquiry_selected"] == row["id"]
    assert button(app, "Marcar como contactado").disabled
    button(app, "Volver a solicitudes").click().run()
    assert not visible_requests(app)
    assert "Contactadas (1)" in app.radio(key="_inquiry_status").options
    app.radio(key="_inquiry_status").set_value("contacted").run()
    assert visible_requests(app) == [row["id"]]
    open_request(app, row)
    assert button(app, "Marcar como contactado").disabled
