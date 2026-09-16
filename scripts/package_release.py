"""Build a release from an explicit allowlist; never includes the live DB or secrets."""
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
files = [".gitignore", ".streamlit/config.toml", ".streamlit/secrets.toml.example",
         "README.md", "INICIAR_APP.bat", "app.py", "auth.py", "inventory.py", "ticket.py", "order_views.py", "styles.css",
         "requirements.txt", "requirements-dev.txt", "data/catalog_seed.json"]
for folder, pattern in (("assets/products", "*"), ("assets/fonts", "*"), ("docs", "*.md"), ("scripts", "*.py"), ("tests", "*.py")):
    files.extend(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).glob(pattern) if p.is_file())
out = ROOT / "output/importadora-publicar.zip"
out.parent.mkdir(exist_ok=True)
with ZipFile(out, "w", ZIP_DEFLATED) as archive:
    for relative in sorted(set(files)):
        archive.write(ROOT / relative, relative)
with ZipFile(out) as archive:
    assert archive.testzip() is None
    assert not any(name.endswith((".hash", ".db")) or name.endswith("secrets.toml")
                   or "ACCESO_LOCAL" in name for name in archive.namelist())
    assert len([name for name in archive.namelist() if name.startswith("assets/products/")]) == 24
    assert "assets/fonts/NotoSans-Regular.ttf" in archive.namelist()
    assert "assets/fonts/OFL.txt" in archive.namelist()
print(f"Release verified: {len(set(files))} files; {out.stat().st_size:,} bytes; no secrets or live database")
