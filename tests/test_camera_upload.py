"""Camera captures are validated and staged before saving the product."""
import ast
import io
from types import SimpleNamespace

from inventory import InventoryError, ROOT, clean_image
from test_photos import photo


def camera_helpers():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name in {"stage_camera_photo", "remove_camera_photo"}]
    state = {}
    scope = {"st": SimpleNamespace(session_state=state), "clean_image": clean_image,
             "InventoryError": InventoryError}
    exec(compile(ast.Module(body=functions, type_ignores=[]), "app.py", "exec"), scope)
    return scope["stage_camera_photo"], scope["remove_camera_photo"], state


def test_camera_photos_stage_one_at_a_time_and_respect_limit():
    stage, remove, state = camera_helpers()
    state["camera_test_0"] = io.BytesIO(photo())
    stage("test", "camera_test_0", occupied=6)
    assert len(state["camera_photos_test"]) == 1
    assert state["camera_revision_test"] == 1
    state["camera_test_1"] = io.BytesIO(photo())
    stage("test", "camera_test_1", occupied=6)
    assert len(state["camera_photos_test"]) == 2
    stage("test", "camera_test_1", occupied=6)
    assert len(state["camera_photos_test"]) == 2
    assert "8 fotos" in state["camera_error_test"]
    remove("test", 0)
    assert len(state["camera_photos_test"]) == 1
    assert "camera_error_test" not in state


def test_camera_rejects_invalid_image_without_staging():
    stage, _, state = camera_helpers()
    state["camera_test_0"] = io.BytesIO(b"not a photo")
    stage("test", "camera_test_0", occupied=0)
    assert state["camera_photos_test"] == []
    assert "imagen" in state["camera_error_test"].lower()
