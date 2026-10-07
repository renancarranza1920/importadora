"""The exported campaign covers every supplied SKU, including supplier labels."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preparar_anuncios import apply_stock

ROOT = Path(__file__).resolve().parents[1]


def test_ad_generator_covers_all_catalog_references_and_identifies_supplier_claims(tmp_path):
    subprocess.run([sys.executable, str(ROOT / 'scripts/preparar_anuncios.py'), '--output', str(tmp_path)], check=True)
    products = json.loads((ROOT / 'data/catalog_seed.json').read_text())['products']
    with (tmp_path / 'copys-y-enlaces.csv').open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    assert {r['referencia'] for r in rows} == {p['sku'] for p in products}
    assert len(rows) == 24
    snapshot = json.loads((ROOT / 'data/campaign_stock.json').read_text())
    stocks = {p['sku']: p['stock'] for p in snapshot['products']}
    assert sum(int(r['unidades_restantes']) for r in rows) == sum(stocks.values())
    for row in rows:
        for format in ('feed', 'story'):
            document = tmp_path / row['carpeta'] / f'{row["referencia"]}-{format}.html'
            assert document.is_file()
            markup = document.read_text()
            assert f"QUEDAN {stocks[row['referencia']]} UNIDADES" in markup
            assert row['fecha_stock'] in markup
            assert int(row['unidades_restantes']) == stocks[row['referencia']]
            if row['referencia'].startswith('IP17PM-'):
                assert 'MODELOS INDICADOS POR EL PROVEEDOR' in markup
                assert 'pendiente de comprobar físicamente' in markup
                assert 'según la etiqueta del proveedor' in row['texto']
    assert len(list((tmp_path / 'iPhone').glob('*.html'))) == 12
    assert len(list((tmp_path / 'Samsung').glob('*.html'))) == 36


@pytest.mark.parametrize('problem', ['missing', 'duplicate', 'negative', 'boolean'])
def test_campaign_rejects_invalid_stock_instead_of_using_seed(problem):
    products = [dict(sku='A', stock=50), dict(sku='B', stock=20)]
    snapshot = dict(captured_date='2026-10-06', products=[dict(sku='A', stock=3), dict(sku='B', stock=5)])
    if problem == 'missing':
        snapshot['products'].pop()
    elif problem == 'duplicate':
        snapshot['products'].append(dict(sku='A', stock=3))
    else:
        snapshot['products'][0]['stock'] = -1 if problem == 'negative' else True
    with pytest.raises(ValueError):
        apply_stock(products, snapshot)


def test_campaign_replaces_historical_stock_without_changing_catalog():
    products = [dict(sku='A', stock=50), dict(sku='B', stock=20)]
    result = apply_stock(products, dict(captured_date='2026-10-06', products=[dict(sku='A', stock=3), dict(sku='B', stock=0)]))
    assert [p['stock'] for p in result] == [3, 0]
    assert [p['stock'] for p in products] == [50, 20]
