"""The exported campaign covers every supplied SKU, including supplier labels."""
import csv
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_ad_generator_covers_all_catalog_references_and_identifies_supplier_claims(tmp_path):
    subprocess.run([sys.executable, str(ROOT / 'scripts/preparar_anuncios.py'), '--output', str(tmp_path)], check=True)
    products = json.loads((ROOT / 'data/catalog_seed.json').read_text())['products']
    with (tmp_path / 'copys-y-enlaces.csv').open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    assert {r['referencia'] for r in rows} == {p['sku'] for p in products}
    assert len(rows) == 24
    for row in rows:
        for format in ('feed', 'story'):
            document = tmp_path / row['carpeta'] / f'{row["referencia"]}-{format}.html'
            assert document.is_file()
            markup = document.read_text()
            if row['referencia'].startswith('IP17PM-'):
                assert 'MODELOS INDICADOS POR EL PROVEEDOR' in markup
                assert 'pendiente de comprobar físicamente' in markup
                assert 'según la etiqueta del proveedor' in row['texto']
    assert len(list((tmp_path / 'iPhone').glob('*.html'))) == 12
    assert len(list((tmp_path / 'Samsung').glob('*.html'))) == 36
