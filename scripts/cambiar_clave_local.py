import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inventory import ROOT, password_hash

first = getpass.getpass("Nueva contraseña (12 caracteres o más): ")
if first != getpass.getpass("Repite la contraseña: "):
    raise SystemExit("Las contraseñas no coinciden.")
(ROOT / "data/admin_password.hash").write_text(password_hash(first), encoding="utf-8")
access = ROOT / "ACCESO_LOCAL.txt"
if access.exists():
    access.write_text("La contraseña local fue cambiada. Utiliza la que elegiste.\nURL: http://localhost:8501\n", encoding="utf-8")
print("Contraseña actualizada. Las sesiones anteriores quedan invalidadas al interactuar.")
