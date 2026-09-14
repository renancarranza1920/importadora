"""Generate a password hash without sending the password to any service."""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from inventory import password_hash

if __name__ == "__main__":
    first = getpass.getpass("Nueva contraseña (12 caracteres o más): ")
    second = getpass.getpass("Repite la contraseña: ")
    if first != second:
        raise SystemExit("Las contraseñas no coinciden.")
    print('\nADMIN_PASSWORD_HASH = "' + password_hash(first) + '"')
