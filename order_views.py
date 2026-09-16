"""Public request cart and private review; requests never reserve stock."""
import json
import hashlib
from pathlib import Path
from urllib.parse import urlencode, parse_qs, urlparse
from uuid import uuid4

import streamlit as st

from inventory import MAX_TOTAL_CENTS

WHATSAPP = "50373113611"
API_VERSION = 2
IMPLEMENTATION_REVISION = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
STATUSES = {"pending": "Pendiente", "contacted": "Contactado", "cancelled": "Cancelado", "converted": "Venta registrada"}


def money(value):
    return f"${value / 100:,.2f}"


def total(cart):
    return sum(i["quantity"] * i["price_cents"] for i in cart.values())


def whatsapp_link(row, cart=None, recipient=WHATSAPP):
    cart = cart if cart is not None else json.loads(row["items"])
    lines = [f"Solicitud {row['id'][:8].upper()}", f"Cliente: {row['customer']}"]
    for sku, item in cart.items():
        lines.append(f"{sku} · {item.get('name', sku)[:60]} · {item['quantity']} x {money(item['price_cents'])} = {money(item['quantity'] * item['price_cents'])}")
    lines.extend([f"Total estimado: {money(total(cart))} USD", "Sujeto a confirmación de disponibilidad y precio."])
    return f"https://wa.me/{recipient}?{urlencode({'text': chr(10).join(lines)})}"


def set_value(key, value):
    st.session_state[key] = value


def review_items(db, cart, prefix, summary, reel=None):
    revised, invalid = {}, False
    for sku, entry in cart.items():
        p = db.get_product(sku)
        available = p["stock"] if p["active"] else 0
        with st.container(border=True, key=f"cart_item_{prefix}_{sku}"):
            summary(p)
            photos = db.list_photos(sku)
            if photos and reel:
                with st.expander(f"Foto real · {len(photos)} fotos"):
                    reel([photo["image_data"] for photo in photos])
            key = f"request_qty_{prefix}_{sku}"
            st.session_state.setdefault(key, entry["quantity"])
            qty = st.number_input(f"Cantidad · {sku}", min_value=0, max_value=10000,
                                  step=1, key=key)
            st.caption(f"En este pedido: {qty} · Disponibles ahora: {available}")
            if qty > available:
                st.warning("Agotado o archivado. Quita este artículo para continuar." if not available else f"Solo quedan {available}. Puedes ajustar la cantidad.")
                st.button(f"Usar disponibles ({available})", key=f"fit_{prefix}_{sku}", on_click=set_value,
                          args=(key, available), width="stretch")
                invalid = True
            price = entry["price_cents"]
            if qty and price != p["price_cents"]:
                st.warning(f"Precio anterior: {money(price)}. Precio actual: {money(p['price_cents'])}.")
                if st.checkbox("Aceptar precio actual", key=f"accept_{prefix}_{sku}_{p['price_cents']}"):
                    price = p["price_cents"]
                else:
                    invalid = True
            st.button("Quitar del pedido", key=f"drop_{prefix}_{sku}", on_click=set_value, args=(key, 0), width="stretch")
            if qty:
                revised[sku] = dict(quantity=qty, price_cents=price, name=entry.get("name", p["name"]))
                st.write(f"**Subtotal: {money(qty * price)}**")
            else:
                st.caption("Este artículo no se incluirá.")
    st.html(f'<div class="cart-total"><div><div class="eyebrow">Total estimado · USD</div>'
            f'<div class="muted">{sum(item["quantity"] for item in revised.values())} unidades · {len(revised)} productos</div></div>'
            f'<div class="receipt-total">{money(total(revised))}</div></div>')
    if total(revised) > MAX_TOTAL_CENTS:
        st.error("El total del pedido supera el límite permitido. Reduce las cantidades para continuar.")
        invalid = True
    return revised, invalid or not revised


def public_order(db, summary, reel=None, nav_key="nav"):
    st.title("Mi pedido")
    st.caption("Revisa tus productos. El pedido no reserva unidades ni confirma una compra.")
    cart = st.session_state["public_cart"]
    last = st.session_state.get("last_inquiry")
    if last:
        with st.expander("Solicitud anterior" if cart else "Solicitud registrada", expanded=not bool(cart)):
            st.success(f"Solicitud {last['id'][:8].upper()} registrada.")
            for sku, item in json.loads(last["items"]).items():
                st.text(f"{sku} · {item['name']} · {item['quantity']} × {money(item['price_cents'])}")
            st.write(f"**Total estimado: {money(total(json.loads(last['items'])))} USD**")
            st.link_button("Continuar en WhatsApp", whatsapp_link(last), type="primary", width="stretch")
            st.caption("Si WhatsApp no se abrió, toca «Continuar en WhatsApp» y pulsa Enviar en el chat. Registrar la solicitud no envía el mensaje automáticamente.")
        if st.session_state.pop("open_order_whatsapp", False):
            target = json.dumps(whatsapp_link(last))
            st.iframe(f'''<script>
            const a = window.parent.document.createElement('a');
            a.href = {target}; a.target = '_blank'; a.rel = 'noopener noreferrer';
            window.parent.document.body.appendChild(a); a.click(); a.remove();
            </script>''', height=1, tab_index=-1)
    st.button("Seguir agregando productos" if cart else "Ver catálogo", on_click=set_value, args=(nav_key, "Catálogo"), width="stretch")
    if not cart:
        if not last:
            st.info("Agrega productos desde el catálogo para preparar un pedido.")
        return
    st.button("Actualizar disponibilidad", key="refresh_public")
    revised, invalid = review_items(db, cart, "public", summary, reel)
    if revised != cart:
        st.session_state["public_cart"] = revised
        st.session_state["public_request"] = str(uuid4())
        st.rerun()
    with st.form("public_order"):
        customer = st.text_input("Tu nombre (opcional)", max_chars=100)
        st.caption("Al continuar se guarda tu solicitud y se abre WhatsApp con el pedido preparado.")
        if st.form_submit_button("Pedir por WhatsApp", type="primary", disabled=invalid, width="stretch"):
            row = db.create_inquiry(revised, customer.strip() or "Cliente de WhatsApp", "", st.session_state["public_request"], st.session_state["public_source"])
            st.session_state["last_inquiry"] = row
            st.session_state["open_order_whatsapp"] = True
            st.session_state["public_cart"] = {}
            st.session_state["public_request"] = str(uuid4())
            for key in list(st.session_state):
                if key.startswith(("request_qty_public_", "accept_public_")):
                    del st.session_state[key]
            st.rerun()


def inquiries_page(db, summary, sale_view, reel=None):
    st.title("Solicitudes")
    st.caption("Pedidos pendientes de confirmación. El mensaje de WhatsApp puede no haberse enviado.")
    st.button("Actualizar disponibilidad")
    rows = db.list_inquiries()
    status = st.selectbox("Estado de solicitud", ["Abiertas", "Todas"] + list(STATUSES.values()))
    search = st.text_input("Buscar solicitud o cliente").casefold().strip()
    rows = [r for r in rows if (status == "Todas" or status == "Abiertas" and r["status"] in ("pending", "contacted") or STATUSES[r["status"]] == status)
            and search in f"{r['id']} {r['customer']} {r['phone']}".casefold()]
    if not rows:
        st.info("No hay solicitudes para estos filtros.")
        return
    selected = st.selectbox("Selecciona una solicitud", [r["id"] for r in rows],
        format_func=lambda value: next(f"{r['id'][:8].upper()} · {r['customer']} · {STATUSES[r['status']]}" for r in rows if r["id"] == value))
    row = next(r for r in rows if r["id"] == selected)
    st.text(row["customer"] + (f" · {row['phone']}" if row["phone"] else ""))
    st.caption(f"Solicitud {selected[:8].upper()} · {STATUSES[row['status']]}")
    original, cart = json.loads(row["original_items"]), json.loads(row["items"])
    with st.expander("Pedido original del cliente"):
        st.dataframe([dict(Referencia=sku, Producto=i["name"], Cantidad=i["quantity"], Precio=money(i["price_cents"])) for sku, i in original.items()], hide_index=True, width="stretch")
    if row["status"] == "converted":
        sale_view(db.get_sale(row["sale_id"]))
        return
    if row["status"] == "cancelled":
        st.info("Solicitud cancelada. No se descontaron existencias.")
        return
    revised, invalid = review_items(db, cart, f"{selected}_{row['version']}", summary, reel)
    changed = revised != cart
    if changed:
        st.info("Guarda los cambios antes de confirmar la venta. Acuerda los ajustes con el cliente.")
    if st.button("Guardar ajustes del pedido", disabled=not revised or not changed, width="stretch"):
        db.update_inquiry(selected, row["version"], revised, row["status"])
        st.rerun()
    with st.expander("Ofrecer otro producto disponible"):
        alternatives = [p for p in db.list_products() if p["stock"] > 0 and p["sku"] not in revised]
        if alternatives:
            sku = st.selectbox("Producto alternativo", [p["sku"] for p in alternatives],
                               format_func=lambda value: next(f"{p['sku']} · {p['name']}" for p in alternatives if p["sku"] == value))
            p = next(p for p in alternatives if p["sku"] == sku)
            summary(p)
            if st.button("Guardar ajustes y agregar alternativa", disabled=len(revised) >= 20, width="stretch"):
                revised[sku] = dict(quantity=1, price_cents=p["price_cents"], name=p["name"])
                db.update_inquiry(selected, row["version"], revised, row["status"])
                st.rerun()
            st.caption("Se agrega una unidad. Acuerda el cambio con el cliente antes de confirmar la venta.")
        else:
            st.info("No hay otros productos disponibles.")
    phone = ''.join(c for c in row["phone"] if c.isdigit())
    if phone:
        st.link_button("Revisar pedido con el cliente por WhatsApp", whatsapp_link(row, revised, phone), width="stretch")
    else:
        st.caption(f"Busca la solicitud {selected[:8].upper()} en el chat recibido por WhatsApp para responder al cliente.")
        message = parse_qs(urlparse(whatsapp_link(row, revised)).query)["text"][0]
        with st.expander("Copiar resumen actualizado para el chat"):
            st.code(message, language=None)
    if st.button("Marcar como contactado", disabled=changed or row["status"] == "contacted", width="stretch"):
        db.update_inquiry(selected, row["version"], cart, "contacted")
        st.rerun()
    with st.form(f"confirm_inquiry_{selected}_{row['version']}"):
        payment = st.selectbox("Medio de pago del pedido", ["Efectivo", "Transferencia", "Tarjeta", "Otro"])
        confirmed = st.checkbox("El cliente aceptó estos productos y precios; recibí el pago y confirmo la venta.")
        if st.form_submit_button(f"Confirmar venta del pedido · {money(total(revised))}", type="primary", disabled=invalid or changed, width="stretch"):
            if not confirmed:
                st.error("Confirma el acuerdo y el pago antes de registrar la venta.")
            else:
                sale_id = db.confirm_sale(cart, row["customer"], payment, f"Solicitud {selected[:8].upper()}",
                                          f"inquiry:{selected}", inquiry_id=selected, inquiry_version=row["version"])
                st.session_state["last_sale"] = sale_id
                st.session_state["download_sale"] = sale_id
                st.session_state["flash"] = "Venta confirmada. Existencias actualizadas y ticket disponible."
                st.session_state["next_nav"] = "Nueva venta"
                st.rerun()
    with st.expander("Cancelar solicitud"):
        with st.form(f"cancel_{selected}"):
            cancel = st.checkbox("Confirmo que deseo cancelar esta solicitud.")
            if st.form_submit_button("Cancelar pedido"):
                if cancel:
                    db.update_inquiry(selected, row["version"], cart, "cancelled")
                    st.rerun()
                else:
                    st.error("Marca la confirmación para cancelar.")
