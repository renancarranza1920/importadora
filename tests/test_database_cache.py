"""Exercise the app's resource factory across an inventory implementation update."""
import ast

import streamlit as st
from sqlalchemy import inspect

from inventory import Inventory, ROOT, product_photos


def test_inventory_update_recreates_cached_resource_without_resetting_stock(tmp_path):
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "database")
    namespace = {"st": st, "Inventory": Inventory}
    exec(compile(ast.Module(body=[factory], type_ignores=[]), str(ROOT / "app.py"), "exec"), namespace)
    database = namespace["database"]
    url = f"sqlite:///{(tmp_path / 'update.db').as_posix()}"
    try:
        old = database(url, False, "before-real-photos")
        old.adjust_stock("A06-01", 3, "Stock before deploy", "before-deploy")
        product_photos.drop(old.engine)
        assert "product_photos" not in inspect(old.engine).get_table_names()
        assert database(url, False, "before-real-photos") is old
        current = database(url, False, "with-real-photos")
        assert current is not old
        assert "product_photos" in inspect(current.engine).get_table_names()
        assert current.list_photos("A06-01") == []
        assert current.get_product("A06-01")["stock"] == 13
        assert database(url, False, "with-real-photos") is current
        current.create_inquiry = None  # Simulate a stale cached resource lacking the new API.
        repaired = database(url, False, "with-real-photos")
        assert repaired is not current
        assert callable(repaired.create_inquiry)
        assert repaired.get_product("A06-01")["stock"] == 13
    finally:
        database.clear()
