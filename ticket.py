"""Portable customer ticket rendered from the confirmed sale snapshot."""
import io

from PIL import Image, ImageDraw, ImageFont


def ticket_png(sale):
    font = ImageFont.load_default(size=26)
    small = ImageFont.load_default(size=21)
    heading = ImageFont.load_default(size=40)
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def wrap(text, width=620):
        lines, line = [], ""
        for char in str(text):
            if char == "\n" or measure.textlength(line + char, font=font) > width:
                lines.append(line)
                line = "" if char == "\n" else char
            else:
                line += char
        return lines + [line]

    rows = [(item, wrap(item["name"]), wrap(item["sku"])) for item in sale["items"]]
    height = 340 + sum(90 + 34 * (len(name) + len(sku)) for _, name, sku in rows)
    image = Image.new("RGB", (720, height), "#ffffff")
    draw = ImageDraw.Draw(image)
    ink, muted, green = "#183d2f", "#61746b", "#137b60"
    draw.rectangle((0, 0, 720, 12), fill=green)
    draw.text((48, 45), "TU COMPRA" if sale["status"] == "confirmed" else "VENTA ANULADA", font=heading, fill=ink)
    draw.text((48, 103), f"Ticket {sale['id'][:8].upper()} · USD", font=small, fill=muted)
    y = 158
    for item, names, skus in rows:
        draw.line((48, y, 672, y), fill="#dfe8e3", width=2)
        y += 20
        for line in names:
            draw.text((48, y), line, font=font, fill=ink)
            y += 34
        for line in skus:
            draw.text((48, y), line, font=small, fill=muted)
            y += 34
        price = item["unit_price_cents"]
        draw.text((48, y + 6), f"{item['quantity']} x ${price / 100:,.2f}", font=small, fill=muted)
        subtotal = f"${item['quantity'] * price / 100:,.2f}"
        draw.text((672, y + 6), subtotal, font=font, fill=ink, anchor="ra")
        y += 70
    draw.rounded_rectangle((32, y, 688, y + 98), radius=16, fill="#e8f3ed")
    draw.text((52, y + 18), "TOTAL USD", font=small, fill=green)
    total = f"${sale['total_cents'] / 100:,.2f}"
    draw.text((664, y + 48), total, font=heading, fill=ink, anchor="rm")
    draw.text((48, y + 124), "Gracias por tu compra · Comprobante no fiscal", font=small, fill=muted)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()
