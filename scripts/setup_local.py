import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inventory import Inventory, ROOT, password_hash

(ROOT / "data").mkdir(exist_ok=True)
path = ROOT / "data/admin_password.hash"
if not path.exists():
    password = secrets.token_urlsafe(15)
    path.write_text(password_hash(password), encoding="utf-8")
    (ROOT / "ACCESO_LOCAL.txt").write_text(
        "IMPORTADORA - ACCESO LOCAL\n\nDirección: http://localhost:8501\n"
        "Menú: Acceso administrador\nUsuario: Administrador\n"
        f"Contraseña: {password}\n\n"
        "No publiques este archivo ni lo subas a GitHub.\n"
        "Para cambiar la contraseña ejecuta: python scripts/cambiar_clave_local.py\n"
        "Esta clave solo corresponde a la copia local; configura una distinta en la nube.\n", encoding="utf-8")
db = Inventory(f"sqlite:///{(ROOT / 'data/inventory.db').as_posix()}")
db.seed()
print("App preparada. La contraseña está en ACCESO_LOCAL.txt. Inventario conservado.")
