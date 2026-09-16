from __future__ import annotations

import base64
import csv
import html
import hashlib
import io
import logging
import os
import unicodedata
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import streamlit as st
import streamlit.components.v1 as components
from sqlalchemy.exc import SQLAlchemyError

import auth
from ticket import ticket_png
from inventory import Inventory, InventoryError, ROOT, cents, clean_image

st.set_page_config(page_title="IMPORTADORA · Catálogo e inventario", page_icon="📦", layout="wide",
                   initial_sidebar_state="auto")


def config(name, default=""):
    if name in os.environ:
        return os.environ[name]
    try:
        return st.secrets.get(name, default)
    except (FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
        return default


def is_true(value):
    return str(value).lower() in ("true", "1", "yes")


BUSINESS = str(config("BUSINESS_NAME", "IMPORTADORA"))
TZ = ZoneInfo(str(config("TIMEZONE", "America/El_Salvador")))
PRODUCTION = str(config("APP_ENV", "production")) == "production"
PUBLIC = is_true(config("PUBLIC_CATALOG", True))
ENCODED = auth.configured_hash(config, PRODUCTION)


@st.cache_resource
def database(url, production, implementation_revision):
    # Streamlit does not invalidate this resource when only inventory.py changes.
    # Include that file's revision in the cache key so new methods/tables are loaded.
    db = Inventory(url, production)
    db.seed()
    return db


def money(amount):
    return f"${amount / 100:,.2f}"


def local_time(value):
    return datetime.fromisoformat(value).astimezone(TZ)


def escape(value):
    return html.escape(str(value))


def flash(message):
    st.session_state["flash"] = message
    st.rerun()


def reset_catalog_filters():
    for key in ("search", "catalog_brand", "catalog_category", "catalog_order", "catalog_stock", "catalog_page", "catalog_filters"):
        st.session_state.pop(key, None)


def search_text(value):
    return "".join(c for c in unicodedata.normalize("NFKD", str(value).casefold()) if not unicodedata.combining(c))


def new_cart_key():
    st.session_state["sale_request"] = str(uuid4())


def csv_export(rows):
    if not rows:
        return "".encode("utf-8-sig")
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: ("'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v)
                         for k, v in row.items()})
    return out.getvalue().encode("utf-8-sig")


def inventory_rows(items):
    return [{"Referencia": p["sku"], "Artículo": p["name"], "Compatibilidad": p["compatibility"],
             "Marca": p["brand"], "Categoría": p["category"], "Precio USD": f"{p['price_cents']/100:.2f}",
             "Disponibles": p["stock"], "Alerta mínima": p["low_stock"],
             "Estado": "Activo" if p["active"] else "Archivado"} for p in items]


def product_image(product):
    if product.get("image_data"):
        return product["image_data"]
    path = ROOT / product["image_path"] if product.get("image_path") else None
    if path and path.is_file() and path.resolve().is_relative_to((ROOT / "assets").resolve()):
        return path.read_bytes()
    return None


def photo_markup(product):
    raw = product_image(product)
    if raw:
        mime = "image/png" if raw[:8] == b"\x89PNG\r\n\x1a\n" else "image/jpeg"
        zoom = max(100, min(200, int(product.get("image_zoom", 115)))) / 100
        x = max(0, min(100, int(product.get("image_x", 50))))
        y = max(0, min(100, int(product.get("image_y", 50))))
        return (f'<div class="product-photo" tabindex="0" aria-label="Ampliar foto de {escape(product["name"])}" '
                f'style="--photo-zoom:{zoom};--photo-hover:{zoom * 1.65};--photo-x:{x}%;--photo-y:{y}%">'
                f'<img alt="{escape(product["name"])}" src="data:{mime};base64,{base64.b64encode(raw).decode()}"></div>')
    return '<div class="product-photo"><span style="font-size:52px">◇</span></div>'


def title(kicker, heading, description=""):
    st.html(f'<div class="eyebrow">{escape(kicker)}</div><h1>{escape(heading)}</h1>')
    if description:
        st.caption(description)


def product_summary(p):
    st.html('<div class="cart-product">' + photo_markup(p) +
            f'<div><div class="product-ref">{escape(p["sku"])}</div>'
            f'<div class="product-title">{escape(p["name"])}</div>'
            f'<div class="cart-unit">{money(p["price_cents"])}</div>'
            f'<span class="stock">{p["stock"]} disponibles</span>'
            f'<p class="muted">{"Activo" if p["active"] else "Archivado"}</p></div></div>')


def photo_reel(photos):
    st.html('<div class="photo-reel" tabindex="0" aria-label="Fotos reales; desliza para ver más">' +
            ''.join(f'<figure tabindex="0"><img alt="Foto real {index + 1}" src="data:image/jpeg;base64,{base64.b64encode(raw).decode()}">'
                    f'<figcaption>Foto {index + 1} de {len(photos)}</figcaption></figure>'
                    for index, raw in enumerate(photos)) + '</div>')


def open_inventory(sku, action):
    st.session_state["inventory_action"] = action
    st.session_state["inventory_sku"] = sku


def login_page():
    title("Tu negocio, en orden", "Acceso a tu importadora", "Entra para registrar ventas, reponer artículos y consultar tu actividad.")
    if not ENCODED:
        st.info("Falta configurar el acceso. En tu computadora ejecuta INICIAR_APP.bat. En la nube agrega ADMIN_PASSWORD_HASH en Secrets siguiendo la guía.")
        return
    with st.form("login"):
        st.text_input("Usuario", value="Administrador", disabled=True)
        password = st.text_input("Contraseña", type="password", max_chars=200)
        if st.form_submit_button("Entrar", type="primary", width="stretch"):
            error = auth.login(db, password, ENCODED)
            if error:
                st.error(error)
            else:
                st.rerun()


@st.fragment(run_every="30s")
def catalogue(seller):
    all_items = db.list_products()
    st.html('<div class="hero"><div class="eyebrow">COLECCIÓN MAYORISTA · USD</div>'
            '<h1>El próximo favorito<br>de tus clientes.</h1>'
            '<p>Explora los modelos, encuentra el protector ideal y consulta las unidades disponibles.</p>'
            '<span class="hero-badge">● &nbsp; Existencias actualizadas cada 30 segundos</span></div>')
    st.html(f'<div class="section-line"><h2>Encuentra tu modelo</h2><span class="muted">{len(all_items)} referencias · {sum(p["stock"] for p in all_items):,} unidades disponibles</span></div>')
    search = st.text_input("Buscar por modelo o referencia", placeholder="Ej. A26, iPhone 14, A06-01…", key="search", icon=":material/search:")
    cols = st.columns([1, 1, 1])
    brand = cols[0].selectbox("Marca", ["Todas las marcas"] + sorted({p["brand"] for p in all_items}), key="catalog_brand")
    category = cols[1].selectbox("Categoría", ["Todas las categorías"] + sorted({p["category"] for p in all_items}), key="catalog_category")
    order = cols[2].selectbox("Ordenar", ["Referencia", "Menor precio", "Mayor precio", "Más disponibles"], key="catalog_order")
    only_stock = st.toggle("Solo artículos disponibles", value=True, key="catalog_stock")
    st.button("Limpiar filtros", on_click=reset_catalog_filters)
    # Repeating the family prefix makes searching "iphone 14" also find "iPhone 13/14".
    def searchable(p):
        value = search_text(" ".join(str(p[k]) for k in ("sku", "name", "compatibility", "brand", "category")))
        compact = value.casefold().replace(" ", "")
        terms = search_text(search).split()
        for term in terms:
            if term not in value.casefold() and term.replace(" ", "") not in compact:
                return False
        return True
    items = [p for p in all_items if searchable(p) and (brand == "Todas las marcas" or p["brand"] == brand)
             and (category == "Todas las categorías" or p["category"] == category) and (not only_stock or p["stock"] > 0)]
    if order != "Referencia":
        items.sort(key=lambda p: p["stock"] if order == "Más disponibles" else p["price_cents"],
                   reverse=order in ("Mayor precio", "Más disponibles"))
    st.caption(f"{len(items)} resultados · Precios mayoristas en dólares estadounidenses")
    if not items:
        st.html('<div class="empty-state"><strong>No encontramos ese modelo</strong>Prueba otra referencia o cambia los filtros.</div>')
        return
    pages = max(1, (len(items) + 11) // 12)
    filters = (search, brand, category, order, only_stock)
    if st.session_state.get("catalog_filters") != filters or st.session_state.get("catalog_page", 1) > pages:
        st.session_state["catalog_page"] = 1
    st.session_state["catalog_filters"] = filters
    page = st.selectbox("Página de resultados", list(range(1, pages + 1)), key="catalog_page", format_func=lambda n: f"Página {n} de {pages}") if pages > 1 else 1
    with st.container(horizontal=True, gap="small", key="catalog_grid"):
        for p in items[(page - 1) * 12:page * 12]:
            with st.container(width=255, border=True, key=f"card_{p['sku']}"):
                stock_class = "empty" if not p["stock"] else "low" if p["stock"] <= p["low_stock"] else ""
                stock_text = f"{p['stock']} disponibles" if p["stock"] else "Agotado"
                st.html(photo_markup(p) + f'<div class="product-ref">{escape(p["brand"])} / {escape(p["sku"])}</div>'
                        f'<div class="product-title">{escape(p["name"])}</div>'
                        f'<div class="product-foot"><span class="product-price">{money(p["price_cents"])} <span class="price-currency">USD</span></span>'
                        f'<span class="stock {stock_class}">{stock_text}</span></div>')
                with st.expander("Ver detalles"):
                    raw = product_image(p)
                    if raw:
                        st.image(raw, width="stretch")
                    st.write(f"**Compatibilidad:** {p['compatibility'] or 'No especificada'}")
                    st.caption("Una sola referencia comparte las existencias entre todos los modelos indicados.")
                    if p["notes"]:
                        st.caption(p["notes"])
                if seller:
                    cart = st.session_state["cart"]
                    in_cart = cart.get(p["sku"], {}).get("quantity", 0)
                    if st.button("Agregar a la venta" if not in_cart else f"Agregar otra · {in_cart} en carrito",
                                 key=f"add_{p['sku']}", width="stretch", disabled=p["stock"] <= in_cart,
                                 icon=":material/add_shopping_cart:"):
                        if not auth.authenticated(ENCODED):
                            st.rerun()
                        cart[p["sku"]] = {"quantity": in_cart + 1, "price_cents": p["price_cents"]}
                        st.session_state.pop(f"qty_{p['sku']}", None)
                        new_cart_key()
                        st.toast(f"{p['sku']} agregado")
                        st.rerun()
    st.caption("Disponibilidad informativa hasta confirmar la venta. Las compatibilidades proceden del catálogo suministrado.")


def receipt(sale):
    rows = "".join(f'<tr><td>{escape(i["sku"])}</td><td>{escape(i["name"])}</td><td>{i["quantity"]}</td>'
                   f'<td>{money(i["unit_price_cents"])}</td><td>{money(i["quantity"]*i["unit_price_cents"])}</td></tr>' for i in sale["items"])
    return f'''<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>Comprobante {sale['id'][:8]}</title><style>body{{font:15px Arial;max-width:800px;margin:40px auto;padding:20px;color:#183d2f}}
    table{{width:100%;border-collapse:collapse}}td,th{{padding:12px 4px;text-align:left;border-bottom:1px solid #ddd}}h1{{letter-spacing:2px}}</style>
    <h1>{escape(BUSINESS)}</h1><h2>Comprobante de venta · {sale['id'][:8].upper()}</h2>
    <p>{local_time(sale['created_at']).strftime('%d/%m/%Y %H:%M')} · {escape(sale['customer'])}</p>
    <p>Pago: {escape(sale['payment'])} · Estado: {'Anulada' if sale['status']=='voided' else 'Confirmada'}</p>
    <table><tr><th>Referencia</th><th>Artículo</th><th>Unidades</th><th>Precio</th><th>Subtotal</th></tr>{rows}</table>
    <h2>Total: {money(sale['total_cents'])} USD</h2><p>{escape(sale['notes'])}</p>
    <small>Comprobante interno de venta. No es una factura fiscal.</small></html>'''


def sale_view(sale):
    png = ticket_png(sale)
    st.download_button("Descargar ticket en imagen", png, file_name=f"ticket-{sale['id'][:8]}.png",
                       mime="image/png", key=f"ticket_{sale['id']}", type="primary", on_click="ignore")
    with st.expander("Vista previa del ticket para el cliente"):
        st.image(png, width=360)
    if st.session_state.get("download_sale") == sale["id"]:
        st.session_state.pop("download_sale", None)
        encoded = base64.b64encode(png).decode("ascii")
        components.html(f'''<script>
        const doc = window.parent.document;
        const a = doc.createElement('a');
        a.href = "data:image/png;base64,{encoded}";
        a.download = "ticket-{sale['id'][:8]}.png";
        doc.body.appendChild(a); a.click(); a.remove();
        </script>''', height=0)
        st.caption("Ticket listo. Si tu navegador no inició la descarga, toca «Descargar ticket en imagen».")
    st.write(f"**Venta {sale['id'][:8].upper()} · {sale['customer']}**")
    st.caption(f"{local_time(sale['created_at']).strftime('%d/%m/%Y %H:%M')} · {sale['payment']} · {'Anulada' if sale['status']=='voided' else 'Confirmada'}")
    st.dataframe([{"Referencia": i["sku"], "Artículo": i["name"], "Unidades": i["quantity"],
                   "Precio": money(i["unit_price_cents"]), "Subtotal": money(i["quantity"] * i["unit_price_cents"])}
                  for i in sale["items"]], hide_index=True, width="stretch")
    st.write(f"**Total: {money(sale['total_cents'])} USD**")
    st.download_button("Descargar comprobante", receipt(sale).encode(), file_name=f"venta-{sale['id'][:8]}.html",
                       mime="text/html", key=f"receipt_{sale['id']}")


def cart_page():
    title("Punto de venta", "Tu próxima venta", "Revisa las unidades y confirma cuando hayas recibido el pago.")
    if st.session_state.get("last_sale"):
        with st.expander("Última venta registrada", expanded=not st.session_state["cart"]):
            sale_view(db.get_sale(st.session_state["last_sale"]))
    cart = st.session_state["cart"]
    if not cart:
        st.html('<div class="empty-state"><strong>Tu carrito está listo para comenzar</strong>Entra al catálogo y agrega los artículos que tu cliente eligió.</div>')
        return
    total = 0
    invalid = False
    for sku, entry in list(cart.items()):
        p = db.get_product(sku)
        with st.container(border=True, key=f"cart_item_{sku}"):
            st.html('<div class="cart-product">' + photo_markup(p) +
                    f'<div><div class="product-ref">{escape(p["brand"])} / {escape(sku)}</div>'
                    f'<div class="product-title">{escape(p["name"])}</div>'
                    f'<div class="cart-unit">{money(entry["price_cents"])} <span>por unidad</span></div>'
                    f'<div class="muted">{p["stock"]} disponibles</div></div></div>')
            real = db.list_photos(sku)
            if real:
                with st.expander(f"Foto real · {len(real)} fotos", expanded=True):
                    st.caption("Desliza para ver las fotos. En computadora, pasa el mouse para ampliar.")
                    photo_reel([r["image_data"] for r in real])
            qty = st.number_input(f"Cantidad · {sku}", min_value=1, max_value=10000000,
                                   value=entry["quantity"], step=1, key=f"qty_{sku}")
            if qty != entry["quantity"]:
                cart[sku]["quantity"] = qty
                new_cart_key()
            if not p["active"] or qty > p["stock"]:
                st.error("Este artículo no está disponible en esa cantidad. Modifica las unidades o retíralo.")
                invalid = True
            if entry["price_cents"] != p["price_cents"]:
                invalid = True
                st.warning(f"El precio cambió de {money(entry['price_cents'])} a {money(p['price_cents'])}.")
                if st.button("Aceptar precio actualizado", key=f"price_{sku}"):
                    entry["price_cents"] = p["price_cents"]
                    new_cart_key()
                    st.rerun()
            st.html(f'<div class="cart-subtotal"><span>{qty} × {money(entry["price_cents"])}</span>'
                    f'<strong>Subtotal: {money(qty * entry["price_cents"])}</strong></div>')
            if st.button("Quitar artículo", key=f"remove_{sku}", icon=":material/delete:"):
                del cart[sku]
                st.session_state.pop(f"qty_{sku}", None)
                new_cart_key()
                st.rerun()
            total += qty * entry["price_cents"]
    st.html(f'<div class="cart-total"><div><div class="eyebrow">Total para el cliente · USD</div>'
            f'<div class="muted">{sum(e["quantity"] for e in cart.values())} unidades · {len(cart)} productos</div></div>'
            f'<div class="receipt-total">{money(total)}</div></div>')
    with st.form("checkout"):
        customer = st.text_input("Cliente (opcional)", max_chars=200, placeholder="Cliente general")
        payment = st.selectbox("Medio de pago", ["Efectivo", "Transferencia", "Tarjeta", "Otro"])
        notes = st.text_area("Notas (opcional)", max_chars=3000, placeholder="Entrega, referencia de transferencia…")
        acknowledged = st.checkbox("Confirmo que recibí el pago y quiero descontar estas unidades del inventario.")
        if st.form_submit_button(f"Confirmar venta · {money(total)}", disabled=invalid, type="primary", width="stretch"):
            if not acknowledged:
                st.error("Marca la confirmación de pago para registrar la venta.")
            else:
                sale_id = db.confirm_sale(cart, customer, payment, notes, st.session_state["sale_request"])
                st.session_state["last_sale"] = sale_id
                st.session_state["download_sale"] = sale_id
                for sku in list(cart):
                    st.session_state.pop(f"qty_{sku}", None)
                st.session_state["cart"] = {}
                new_cart_key()
                flash(f"Venta {sale_id[:8].upper()} confirmada. Las existencias ya se actualizaron.")


def product_form(product=None):
    p = product or {"sku": "", "name": "", "compatibility": "", "brand": "", "category": "Protectores",
                    "price_cents": 0, "low_stock": 5, "notes": "", "active": True, "stock": 0}
    identity = f"{p['sku']}_{p['version']}" if product else f"new_{st.session_state.get('new_product_revision', 0)}"
    st.subheader("Fotografías del artículo")
    photo = st.file_uploader("Foto del artículo (máximo 5 MB)", type=["jpg", "jpeg", "png", "webp"], key=f"cover_{identity}")
    with st.container(border=True, key="image_editor"):
        st.markdown("**Encuadre de la foto en las tarjetas**")
        zoom = st.slider("Zoom de la imagen (%)", 100, 200, int(p.get("image_zoom", 115)), step=5, key=f"zoom_{identity}")
        x = st.slider("Centro horizontal (%)", 0, 100, int(p.get("image_x", 50)), key=f"image_x_{identity}")
        y = st.slider("Centro vertical (%)", 0, 100, int(p.get("image_y", 50)), key=f"image_y_{identity}")
        preview = dict(p, image_zoom=zoom, image_x=x, image_y=y)
        if photo:
            preview["image_data"] = clean_image(photo.getvalue())
        st.html('<div class="image-preview">' + photo_markup(preview) + '</div>')
        st.caption("100 % muestra la imagen completa. Ajusta el centro para ampliar la zona deseada. Se aplica al catálogo, inventario y carrito al guardar.")
    existing = db.list_photos(p["sku"]) if product else []
    if existing:
        photo_reel([r["image_data"] for r in existing])
    removed = st.multiselect("Fotos reales que deseas quitar", [r["id"] for r in existing],
                            format_func=lambda value: f"Foto {next(i + 1 for i, r in enumerate(existing) if r['id'] == value)}",
                            key=f"remove_photos_{identity}") if existing else []
    uploads = st.file_uploader("Añadir fotos reales (hasta 8 en total, máximo 5 MB cada una)",
                               type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key=f"real_{identity}")
    prepared = [clean_image(f.getvalue()) for f in uploads]
    if prepared:
        photo_reel(prepared)
    st.caption("Las fotos se guardan al crear el artículo o guardar los cambios. Las fotos reales aparecen en el carrito.")
    with st.form(f"product_{identity}", clear_on_submit=not bool(product)):
        sku = st.text_input("Referencia única", value=p["sku"], disabled=bool(product), max_chars=60)
        name = st.text_input("Nombre del artículo", value=p["name"], max_chars=200)
        compatibility = st.text_input("Modelos compatibles", value=p["compatibility"], max_chars=1500,
                                      help="Escribe todos los modelos para los que sirve la misma unidad.")
        c1, c2 = st.columns(2)
        brand = c1.text_input("Marca", value=p["brand"], max_chars=80)
        category = c2.text_input("Categoría", value=p["category"], max_chars=80)
        price = c1.number_input("Precio de venta (USD)", min_value=0.0, max_value=9999999.99,
                                 value=p["price_cents"] / 100, step=0.25, format="%.2f")
        low = c2.number_input("Avisar cuando queden", min_value=0, max_value=10000000, value=p["low_stock"], step=1)
        stock = st.number_input("Unidades iniciales", min_value=0, max_value=10000000, value=0, step=1) if not product else p["stock"]
        notes = st.text_area("Notas del artículo (visibles en el catálogo)", value=p["notes"], max_chars=3000)
        active = st.checkbox("Artículo activo en el catálogo", value=p["active"])
        if st.form_submit_button("Guardar cambios" if product else "Crear artículo", type="primary"):
            db.save_product(dict(sku=sku, name=name, compatibility=compatibility, brand=brand, category=category,
                price_cents=cents(f"{price:.2f}"), low_stock=int(low), stock=int(stock), notes=notes, active=active,
                image_zoom=zoom, image_x=x, image_y=y),
                expected_version=p["version"] if product else None, image=photo.getvalue() if photo else None,
                real_photos=([r["image_data"] for r in existing if r["id"] not in removed] + prepared) if uploads or removed else None)
            st.session_state.pop("editing_product", None)
            if not product:
                st.session_state["new_product_revision"] = st.session_state.get("new_product_revision", 0) + 1
            flash("Artículo guardado.")


def inventory_page():
    title("Control de existencias", "Inventario", "Consulta, repón y administra todos tus artículos desde un solo lugar.")
    items = db.list_products(include_archived=True)
    active = [p for p in items if p["active"]]
    c1, c2, c3 = st.columns(3)
    c1.metric("Unidades en inventario", f"{sum(p['stock'] for p in items):,}")
    c2.metric("Valor a precio de venta", money(sum(p["stock"] * p["price_cents"] for p in items)))
    c3.metric("Referencias por reponer", sum(p["stock"] <= p["low_stock"] for p in active))
    st.caption("El valor del inventario utiliza precios de venta; no representa costo ni ganancia.")
    action = st.radio("Gestión", ["Existencias", "Reponer / ajustar", "Editar artículo", "Nuevo artículo"], horizontal=True, key="inventory_action")
    if action == "Nuevo artículo":
        product_form()
        return
    if action == "Existencias":
        search = st.text_input("Buscar en inventario")
        low_only = st.checkbox("Mostrar solo existencias bajas o agotadas")
        filtered = [p for p in items if search.casefold() in (p["sku"] + " " + p["name"] + " " + p["compatibility"]).casefold()
                    and (not low_only or p["stock"] <= p["low_stock"])]
        rows = inventory_rows(filtered)
        view = st.radio("Vista de inventario", ["Con fotos", "Tabla"], horizontal=True)
        if view == "Tabla":
            st.dataframe(rows, hide_index=True, width="stretch")
        else:
            pages = max(1, (len(filtered) + 11) // 12)
            page = st.selectbox("Página de inventario", range(1, pages + 1)) if pages > 1 else 1
            with st.container(horizontal=True, key="inventory_grid"):
                for p in filtered[(page-1)*12:page*12]:
                    with st.container(border=True, width=280, key=f"inventory_card_{p['sku']}"):
                        product_summary(p)
                        st.button("Editar artículo", key=f"edit_{p['sku']}", on_click=open_inventory, args=(p["sku"], "Editar artículo"), width="stretch")
                        st.button("Reponer / ajustar", key=f"stock_{p['sku']}", on_click=open_inventory, args=(p["sku"], "Reponer / ajustar"), width="stretch")
            if not filtered:
                st.info("No hay artículos para estos filtros.")
        st.caption(f"{len(filtered)} de {len(items)} referencias")
        st.download_button("Exportar inventario CSV", csv_export(rows), "inventario.csv", "text/csv")
        return
    sku = st.selectbox("Selecciona el artículo", [p["sku"] for p in items], key="inventory_sku",
                       format_func=lambda x: next(f"{p['sku']} · {p['name']}" for p in items if p["sku"] == x))
    if not sku:
        return
    p = db.get_product(sku)
    product_summary(p)
    if action == "Editar artículo":
        st.caption(f"Existencias actuales: {p['stock']}. Para cambiarlas utiliza «Reponer / ajustar».")
        snapshot = st.session_state.get("editing_product")
        if not snapshot or snapshot["sku"] != sku:
            st.session_state["editing_product"] = p
        if st.button("Recargar datos del artículo"):
            st.session_state["editing_product"] = p
            st.rerun()
        product_form(st.session_state["editing_product"])
    else:
        st.info(f"{p['sku']} · {p['stock']} unidades disponibles")
        with st.form("adjustment", clear_on_submit=True):
            kind = st.selectbox("Tipo de movimiento", ["Entrada de mercancía", "Salida por ajuste"])
            qty = st.number_input("Unidades del movimiento", min_value=1, max_value=10000000, value=1, step=1)
            reason = st.text_input("Motivo obligatorio", placeholder="Compra al proveedor, daño, conteo físico…", max_chars=1000)
            confirmed = st.checkbox("Revisé la referencia, el tipo de movimiento y la cantidad.")
            if st.form_submit_button("Registrar movimiento", type="primary"):
                if not confirmed:
                    st.error("Confirma los datos del movimiento.")
                else:
                    db.adjust_stock(sku, qty if kind == "Entrada de mercancía" else -qty,
                                    reason, st.session_state["adjust_request"])
                    st.session_state["adjust_request"] = str(uuid4())
                    flash("Movimiento registrado. Inventario actualizado.")


def sales_page():
    title("Actividad comercial", "Ventas", "Cada venta conserva sus precios y cantidades originales.")
    rows = db.list_sales()
    today = datetime.now(TZ).date()
    cols = st.columns(2)
    start = cols[0].date_input("Desde", today - timedelta(days=30))
    end = cols[1].date_input("Hasta", today)
    if start > end:
        st.error("La fecha inicial debe ser anterior o igual a la final.")
        return
    search = st.text_input("Buscar por cliente o número de venta")
    filtered = [r for r in rows if start <= local_time(r["created_at"]).date() <= end
                and search.casefold() in (r["customer"] + " " + r["id"]).casefold()]
    confirmed = [r for r in filtered if r["status"] == "confirmed"]
    c1, c2 = st.columns(2)
    c1.metric("Ventas confirmadas", len(confirmed))
    c2.metric("Total vendido en el período", money(sum(r["total_cents"] for r in confirmed)))
    exported = [{"Venta": r["id"][:8].upper(), "Fecha": local_time(r["created_at"]).strftime("%d/%m/%Y %H:%M"),
                 "Cliente": r["customer"], "Pago": r["payment"], "Total USD": f"{r['total_cents']/100:.2f}",
                 "Estado": "Confirmada" if r["status"] == "confirmed" else "Anulada"} for r in filtered]
    st.dataframe(exported, hide_index=True, width="stretch")
    st.download_button("Exportar ventas CSV", csv_export(exported), "ventas.csv", "text/csv")
    if not filtered:
        st.info("Todavía no hay ventas para estos filtros.")
        return
    selected = st.selectbox("Ver detalle de una venta", [r["id"] for r in filtered],
        format_func=lambda x: next(f"{r['id'][:8].upper()} · {r['customer']} · {money(r['total_cents'])}" for r in filtered if r["id"] == x))
    sale = db.get_sale(selected)
    sale_view(sale)
    if sale["status"] == "confirmed":
        with st.expander("Anular venta y devolver unidades al inventario"):
            with st.form(f"void_{selected}"):
                reason = st.text_input("Motivo de anulación", max_chars=1000)
                confirmed_void = st.checkbox("Confirmo que todas las unidades de esta venta regresan al inventario.")
                st.caption("Esta opción anula la venta completa. Registra por separado cualquier reembolso al cliente.")
                if st.form_submit_button("Anular y reingresar unidades"):
                    if not confirmed_void:
                        st.error("Confirma la devolución de todas las unidades.")
                    else:
                        db.void_sale(selected, reason)
                        flash("Venta anulada. Las unidades regresaron al inventario.")
    else:
        st.info(f"Anulada: {sale['void_reason']}")


def movements_page():
    title("Historial de inventario", "Movimientos", "Trazabilidad de las entradas, ventas, ajustes y anulaciones.")
    items = db.list_products(True)
    sku = st.selectbox("Filtrar por referencia", ["Todas"] + [p["sku"] for p in items])
    rows = db.list_movements(None if sku == "Todas" else sku)
    names = {"initial": "Inventario inicial", "sale": "Venta", "adjustment": "Ajuste", "void": "Anulación"}
    exported = [{"Fecha": local_time(r["created_at"]).strftime("%d/%m/%Y %H:%M:%S"), "Referencia": r["sku"],
                 "Movimiento": names.get(r["kind"], r["kind"]), "Unidades +/-": r["delta"],
                 "Saldo": r["balance"], "Motivo": r["reason"], "Venta": (r["sale_id"] or "")[:8].upper()} for r in rows]
    st.dataframe(exported, hide_index=True, width="stretch")
    st.download_button("Exportar movimientos CSV", csv_export(exported), "movimientos.csv", "text/csv")


def help_page():
    title("Tu operación, respaldada", "Ayuda y respaldo")
    st.markdown("""**Para vender desde el celular:**

1. Abre la dirección de tu app e inicia sesión.
2. En **Catálogo**, busca el modelo y toca **Agregar a la venta**.
3. En **Nueva venta**, revisa cantidades, cliente y pago.
4. Confirma la venta. La app descuenta las unidades y genera un comprobante.

El carrito no reserva mercancía. La disponibilidad se vuelve a comprobar al confirmar.
Necesitas conexión a internet para registrar una venta en la app publicada.
""")
    st.subheader("Respaldo completo")
    st.caption("Incluye inventario, ventas, movimientos y fotos nuevas. Descárgalo al terminar tu jornada y guárdalo en un lugar privado.")
    st.download_button("Descargar respaldo JSON", db.backup(), f"respaldo-importadora-{datetime.now(TZ).strftime('%Y%m%d-%H%M')}.json",
                       "application/json", type="primary")
    st.caption("La guía explica cómo restaurarlo en una base nueva sin sobrescribir ventas existentes.")
    st.subheader("Datos del catálogo inicial")
    st.write("24 referencias · 360 unidades · $902.50 a precio mayorista. Estos son los valores iniciales del PDF, no el inventario actual.")
    st.caption("Se conservaron los nombres de compatibilidad, incluidos «iPhone 17PM/ 18PM», tal como fueron proporcionados. Puedes corregirlos en Inventario → Editar artículo.")
    guide = ROOT / "docs/PUBLICAR_EN_INTERNET.md"
    if guide.exists():
        with st.expander("Leer la guía para publicar paso a paso"):
            st.markdown(guide.read_text(encoding="utf-8"))
        st.download_button("Descargar guía para publicar", guide.read_bytes(), "PUBLICAR_EN_INTERNET.md", "text/markdown")
    st.caption("Base de datos: PostgreSQL en la nube" if PRODUCTION else "Base de datos local en esta computadora. La app aún no está publicada en internet.")


st.html(f"<style>{(ROOT / 'styles.css').read_text(encoding='utf-8')}</style>")
url = str(config("DATABASE_URL", ""))
if not url and not PRODUCTION:
    (ROOT / "data").mkdir(exist_ok=True)
    url = f"sqlite:///{(ROOT / 'data/inventory.db').as_posix()}"
try:
    if PRODUCTION and not ENCODED.startswith("pbkdf2_sha256$"):
        raise InventoryError("Configura ADMIN_PASSWORD_HASH en Secrets. Consulta docs/PUBLICAR_EN_INTERNET.md.")
    db = database(url, PRODUCTION, hashlib.sha256((ROOT / "inventory.py").read_bytes()).hexdigest())
except (InventoryError, SQLAlchemyError, ValueError):
    st.error("No se pudo iniciar la base de datos o falta configurar el acceso.")
    st.info("En tu computadora abre INICIAR_APP.bat. Para publicar, completa DATABASE_URL, APP_ENV y ADMIN_PASSWORD_HASH en Secrets según la guía.")
    st.stop()

seller = auth.authenticated(ENCODED)
if not seller:
    st.session_state.pop("cart", None)
st.session_state.setdefault("cart", {})
st.session_state.setdefault("sale_request", str(uuid4()))
st.session_state.setdefault("adjust_request", str(uuid4()))

with st.sidebar:
    st.html(f'<div class="brand"><span class="brand-icon">▧</span>{escape(BUSINESS)}</div><div class="brand-sub">CATÁLOGO & INVENTARIO</div>')
    st.caption("TU ESPACIO DE TRABAJO" if seller else "EXPLORA LA COLECCIÓN")
    options = ["Catálogo", "Nueva venta", "Inventario", "Ventas", "Movimientos", "Ayuda y respaldo"] if seller else (["Catálogo", "Acceso administrador"] if PUBLIC else ["Acceso administrador"])
    if st.session_state.get("nav") not in options:
        st.session_state["nav"] = options[0]
    icons = {"Catálogo": "▦", "Nueva venta": "+", "Inventario": "▤", "Ventas": "↗", "Movimientos": "⇄", "Ayuda y respaldo": "ⓘ", "Acceso administrador": "↪"}
    current = st.radio("Navegación", options, key="nav", label_visibility="collapsed",
                       format_func=lambda x: f"{icons[x]}  {x}")
    if seller:
        count = sum(r["quantity"] for r in st.session_state["cart"].values())
        st.divider()
        st.write(f"**{count} unidades en tu carrito**")
        st.caption("Sesión: Administrador")
        if st.button("Cerrar sesión", width="stretch"):
            auth.logout()
            st.rerun()
    st.html('<div class="side-note"><strong>Todo listo para vender.</strong><br>Precios en USD y existencias por referencia. Encuentra cada modelo en segundos.</div>')
    if not PRODUCTION:
        st.caption("Vista local · Publicación pendiente")

if st.session_state.get("flash"):
    st.success(st.session_state.pop("flash"))
try:
    if current == "Acceso administrador":
        login_page()
    elif current == "Catálogo" and (PUBLIC or seller):
        catalogue(seller)
    elif seller:
        {"Nueva venta": cart_page, "Inventario": inventory_page, "Ventas": sales_page,
         "Movimientos": movements_page, "Ayuda y respaldo": help_page}[current]()
except InventoryError as error:
    st.error(str(error))
    if st.button("Actualizar y revisar"):
        st.rerun()
except SQLAlchemyError:
    # Do not expose connection URLs or SQL parameters to a public visitor.
    st.error("No se pudo completar la operación. Comprueba tu conexión y revisa el historial antes de volver a intentar.")
    if st.button("Reintentar conexión"):
        st.rerun()
