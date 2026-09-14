"""Use only a NEW empty target database. Never replaces an existing inventory."""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inventory import Inventory

parser = argparse.ArgumentParser()
parser.add_argument("backup", type=Path)
parser.add_argument("--local-output", type=Path, help="Nuevo archivo SQLite que todavía no existe")
args = parser.parse_args()
if args.local_output:
    if args.local_output.exists():
        raise SystemExit("El archivo de destino ya existe. Selecciona uno nuevo.")
    url = f"sqlite:///{args.local_output.resolve().as_posix()}"
else:
    url = os.environ.get("RESTORE_DATABASE_URL", "")
    if not url:
        raise SystemExit("Configura RESTORE_DATABASE_URL para una base NUEVA o usa --local-output nueva.db")
db = Inventory(url)
db.restore_into_empty(args.backup.read_text(encoding="utf-8"))
print("Respaldo restaurado. Verifica inventario y ventas antes de cambiar la conexión de la app.")
