"""Catalog cards expose saved real photos without hiding the cover image."""
import ast
import base64
from html import escape
import json
import re

from inventory import Inventory, ROOT
from test_photos import photo


def gallery_markup():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"product_image", "photo_markup", "catalog_gallery_markup"}]
    scope = {"ROOT": ROOT, "base64": base64, "escape": escape, "json": json}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "app.py", "exec"), scope)
    return scope["catalog_gallery_markup"]


def test_catalog_gallery_shows_cover_real_photos_and_indicators(tmp_path):
    db = Inventory(f"sqlite:///{(tmp_path / 'gallery.db').as_posix()}")
    db.seed()
    product = db.get_product("A06-01")
    db.save_product(product, product["version"], real_photos=[photo(), photo()])
    grouped = db.list_photos_for_products(["A06-01", "A06-02", "A06-01"])
    assert list(grouped) == ["A06-01", "A06-02"]
    assert grouped["A06-01"] == [row["image_data"] for row in db.list_photos("A06-01")]
    assert grouped["A06-02"] == []
    assert db.list_photos_for_products([]) == {}

    markup = gallery_markup()(product, grouped["A06-01"])
    assert markup.count('class="catalog-gallery-slide"') == 3
    assert markup.count('class="catalog-gallery-dot') == 4  # container plus three dots
    assert markup.count('class="catalog-modal-dot') == 4
    assert "2 fotos reales" in markup
    assert "Foto del catálogo" in markup
    assert "Foto real 2" in markup
    assert 'scroll-snap' not in markup  # Layout belongs to shared CSS.
    assert re.search(r'<dialog class="catalog-photo-dialog"[^>]*>', markup)
    assert 'src="data:image/' in markup
    assert 'class="catalog-modal-image" alt=' in markup
    assert 'class="catalog-modal-image" alt="Foto de GALAXY A06" src=' not in markup


def test_catalog_gallery_with_one_photo_omits_carousel_prompts(tmp_path):
    db = Inventory(f"sqlite:///{(tmp_path / 'single.db').as_posix()}")
    db.seed()
    product = dict(db.get_product("A06-01"), name='Galaxy A06 & "más"')
    markup = gallery_markup()(product, [])
    assert markup.count('class="catalog-gallery-slide"') == 1
    assert 'class="catalog-gallery-dots"' not in markup
    assert 'class="catalog-real-badge"' not in markup
    assert 'Galaxy A06 &amp; &quot;más&quot;' in markup
