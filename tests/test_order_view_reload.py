import ast
import hashlib
import inspect
from pathlib import Path

import pytest
import order_views
from inventory import ROOT, InventoryError


def loader():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "load_order_views")
    namespace = dict(hashlib=hashlib, Path=Path, InventoryError=InventoryError)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "app.py", "exec"), namespace)
    return namespace["load_order_views"]


def test_stale_order_view_is_reloaded_before_keyword_call(monkeypatch):
    monkeypatch.setattr(order_views, "public_order", lambda db, summary, reel=None: None)
    monkeypatch.setattr(order_views, "IMPLEMENTATION_REVISION", "old-deployment")
    refreshed = loader()()
    assert "nav_key" in inspect.signature(refreshed.public_order).parameters
    assert "product_picker" in inspect.signature(refreshed.inquiries_page).parameters
    assert refreshed.API_VERSION == 3


def test_partial_deploy_reports_required_files(monkeypatch):
    monkeypatch.setattr(order_views, "API_VERSION", 1)
    with pytest.raises(InventoryError, match="order_views.py"):
        loader()()
