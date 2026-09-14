import io
import json

import pytest
from PIL import Image

from inventory import Inventory, InventoryError


def photo():
    out = io.BytesIO()
    Image.new("RGB", (80, 60), "green").save(out, "PNG")
    return out.getvalue()


def test_real_photos_persist_replace_and_restore(tmp_path):
    url = f"sqlite:///{(tmp_path / 'photos.db').as_posix()}"
    db = Inventory(url)
    db.seed()
    p = db.get_product("A06-01")
    db.save_product(p, p["version"], real_photos=[photo(), photo()])
    assert len(Inventory(url).list_photos(p["sku"])) == 2
    backup = db.backup()
    restored = Inventory(f"sqlite:///{(tmp_path / 'restored.db').as_posix()}")
    restored.restore_into_empty(backup)
    assert restored.list_photos(p["sku"]) == db.list_photos(p["sku"])
    p = db.get_product(p["sku"])
    db.save_product(p, p["version"], real_photos=[])
    assert db.list_photos(p["sku"]) == []
    old = json.loads(backup)
    old["schema_version"] = 1
    del old["tables"]["product_photos"]
    legacy = Inventory(f"sqlite:///{(tmp_path / 'legacy.db').as_posix()}")
    legacy.restore_into_empty(json.dumps(old))
    assert legacy.get_product(p["sku"])["stock"] == p["stock"]
    assert not legacy.list_photos(p["sku"])


def test_photo_errors_leave_product_unchanged(tmp_path):
    db = Inventory(f"sqlite:///{(tmp_path / 'atomic.db').as_posix()}")
    db.seed()
    p = db.get_product("A06-01")
    for images in ([photo()] * 9, [b"not an image"]):
        with pytest.raises(InventoryError):
            db.save_product(dict(p, name="Changed"), p["version"], real_photos=images)
        assert db.get_product(p["sku"])["name"] == p["name"]
    db.adjust_stock(p["sku"], 1, "Restock", "photo-race")
    with pytest.raises(InventoryError):
        db.save_product(p, p["version"], real_photos=[photo()])
    assert not db.list_photos(p["sku"])
