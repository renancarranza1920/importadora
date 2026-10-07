"""Store information and a deterministic, accessible FAQ assistant."""
from html import escape
import re
from urllib.parse import urlencode

MINIMUM_UNITS = 3
SHIPPING_COPY = "Envíos a todo el país: económico a puntos específicos, con costo según el total de tu compra; personalizado a domicilio por $5.00."


def model_names(product):
    """Expand only explicitly supplied compatibility; never guess other models."""
    raw = str(product.get("compatibility") or product.get("name") or "").strip()
    parts = [part.strip() for part in raw.split("/") if part.strip()]
    if not parts:
        return []
    prefix = re.match(r"^(iphone|galaxy(?:\s+note)?|note)\s+", parts[0], re.I)
    family = prefix.group(0) if prefix else ""
    names = []
    for i, part in enumerate(parts):
        if i and family and not re.match(r"^(iphone|galaxy|note)\b", part, re.I):
            part = family + part
        part = re.sub(r"(\d+)\s*PM\b", r"\1 Pro Max", part, flags=re.I)
        part = re.sub(r"^GALAXY", "Galaxy", part, flags=re.I)
        part = re.sub(r"^NOTE", "Note", part, flags=re.I)
        part = re.sub(r"\bNOTE\b", "Note", part, flags=re.I)
        part = re.sub(r"^IPHONE", "iPhone", part, flags=re.I)
        if part not in names:
            names.append(part)
    return names


def available_models(products):
    return sorted({name for p in products if p.get("active", True) and p["stock"] > 0
                   for name in model_names(p)}, key=str.casefold)


def contact_link(recipient, message):
    return f"https://wa.me/{recipient}?{urlencode({'text': message})}"


def assistant_markup(products, recipient):
    models = ", ".join(available_models(products)) or "Consulta el catálogo para ver la próxima disponibilidad."
    answers = [
        ("¿Qué modelos tienen disponibles?", f"Los modelos con existencias son: {models}. Elige tu teléfono en el catálogo para ver sus fotos y precios. Si no aparece, no está disponible en este catálogo."),
        ("¿Cuál es el pedido mínimo?", "Este catálogo es mayorista: el pedido mínimo es de 3 unidades. Puedes combinar modelos y diseños disponibles."),
        ("¿Tienen tienda física?", "Somos una tienda en línea, sin local físico. Elige tus productos aquí y coordinamos tu entrega por WhatsApp."),
        ("¿Cómo funcionan los envíos?", SHIPPING_COPY + " Por WhatsApp confirmamos el punto disponible para el envío económico o tu dirección para el personalizado, y el total antes de pagar."),
        ("¿Cómo hago mi pedido?", "Selecciona tu modelo, añade los protectores y revisa Mi pedido. Al tocar Pedir por WhatsApp se prepara el mensaje; debes pulsar Enviar en el chat. Luego confirmamos disponibilidad, pago y envío contigo."),
        ("¿Puedo comprar una sola unidad?", "Este catálogo muestra precios mayoristas desde 3 unidades. Para una compra individual, consulta por WhatsApp la disponibilidad y el precio minorista."),
    ]
    faqs = "".join(f'<details class="shop-faq"><summary>{escape(question)}</summary><p>{escape(answer)}</p></details>'
                   for question, answer in answers)
    link = escape(contact_link(recipient, "Hola, tengo una consulta sobre el catálogo mayorista."), quote=True)
    return ('<details class="shop-assistant"><summary class="shop-assistant-toggle">'
            '<span aria-hidden="true">?</span> ¿Te ayudamos?</summary>'
            '<section class="shop-assistant-panel" aria-label="Asistente de la tienda">'
            '<div class="shop-assistant-heading">Hola, estamos para ayudarte.</div>'
            '<p class="shop-assistant-intro">Elige una pregunta y consulta su respuesta.</p>'
            + faqs + f'<a class="shop-contact" href="{link}" target="_blank" rel="noopener noreferrer">Hablar por WhatsApp ↗</a>'
            '</section></details>')
