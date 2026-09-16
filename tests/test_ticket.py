import io

from PIL import Image, ImageDraw

from ticket import ticket_png


def test_ticket_uses_sale_snapshot_and_wraps_long_names():
    sale = {"id": "12345678-test", "status": "confirmed", "total_cents": 675,
            "items": [{"sku": "REF-01", "name": "Protector edición especial " * 10,
                       "quantity": 3, "unit_price_cents": 225}]}
    png = ticket_png(sale)
    with Image.open(io.BytesIO(png)) as image:
        assert image.format == "PNG"
        assert image.width == 720
        long_height = image.height
        image.verify()
    # Customer, business, payment and internal notes are deliberately not inputs.
    sale.update(customer="PRIVATE", notes="PRIVATE", payment="PRIVATE")
    assert ticket_png(sale) == png
    sale["status"] = "voided"
    assert ticket_png(sale) != png
    sale["items"][0]["name"] = "Protector"
    with Image.open(io.BytesIO(ticket_png(sale))) as short:
        assert short.height < long_height


def test_ticket_font_renders_spanish_letters_instead_of_missing_glyphs(monkeypatch):
    rendered_fonts = []
    draw_text = ImageDraw.ImageDraw.text

    def capture(draw, xy, text, *args, **kwargs):
        if text == "Protección edición niño":
            rendered_fonts.append(kwargs["font"])
        return draw_text(draw, xy, text, *args, **kwargs)

    monkeypatch.setattr(ImageDraw.ImageDraw, "text", capture)
    sale = dict(id="spanish-ticket", status="confirmed", total_cents=300,
                items=[dict(sku="ES-01", name="Protección edición niño", quantity=1, unit_price_cents=300)])
    ticket_png(sale)
    assert rendered_fonts
    for font in rendered_fonts:
        missing = bytes(font.getmask(chr(0x10FFFF)))
        for letter in "áéíóúüñÁÉÍÓÚÜÑ":
            assert bytes(font.getmask(letter)) != missing
