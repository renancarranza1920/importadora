"""The exported campaign covers every supplied SKU, including supplier labels."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.preparar_anuncios import apply_campaign_data, apply_stock, display_label

ROOT = Path(__file__).resolve().parents[1]


def test_ad_generator_covers_all_catalog_references_and_identifies_supplier_claims(tmp_path):
    products = json.loads((ROOT / 'data/catalog_seed.json').read_text())['products']
    snapshot = json.loads((ROOT / 'data/campaign_stock.json').read_text())
    seed = {p['sku']: p for p in products}
    snapshot['products'] = [dict(seed[p['sku']], **p) for p in snapshot['products']]
    # Reproduce a system edit that differs from the old seed, including 5G/A04S.
    for row in snapshot['products']:
        if row['sku'] == 'A13-01':
            row.update(name='GALAXY A13 5G/ A04S', compatibility='GALAXY A13(5G)/ A04S', price_cents=215)
    snapshot_path = tmp_path / 'oracle.json'
    snapshot_path.write_text(json.dumps(snapshot))
    subprocess.run([sys.executable, str(ROOT / 'scripts/preparar_anuncios.py'), '--stock-file', str(snapshot_path), '--output', str(tmp_path)], check=True)
    with (tmp_path / 'copys-y-enlaces.csv').open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    assert {r['referencia'] for r in rows} == {p['sku'] for p in products}
    assert len(rows) == 24
    stocks = {p['sku']: p['stock'] for p in snapshot['products']}
    current = {p['sku']: p for p in snapshot['products']}
    saved = json.loads((tmp_path / 'DATOS-SISTEMA.json').read_text())
    assert [p['sku'] for p in saved['products']] == [p['sku'] for p in snapshot['products']]
    assert {p['sku']: p for p in saved['products']} == {
        sku: {k: p[k] for k in ('sku','name','compatibility','brand','price_cents','stock')}
        for sku, p in current.items()}
    assert sum(int(r['unidades_restantes']) for r in rows) == sum(stocks.values())
    for row in rows:
        assert row['nombre_sistema'] == current[row['referencia']]['name']
        assert row['compatibilidad_sistema'] == current[row['referencia']]['compatibility']
        assert row['modelos'] == current[row['referencia']]['compatibility']
        assert row['precio_usd'] == f"{current[row['referencia']]['price_cents']/100:.2f}"
        assert '3 unidades mixtas' in row['texto']
        assert 'Puedes combinar modelos y diseños' in row['texto']
        assert 'antes de pagar' not in row['texto']
        for format in ('feed', 'story'):
            document = tmp_path / row['carpeta'] / f'{row["referencia"]}-{format}.html'
            assert document.is_file()
            markup = document.read_text()
            assert f"QUEDAN {stocks[row['referencia']]} UNIDADES" in markup
            assert row['fecha_stock'] in markup
            assert int(row['unidades_restantes']) == stocks[row['referencia']]
            assert 'MÍNIMO 3 UNIDADES MIXTAS' in markup
            assert 'Puedes combinar modelos y diseños' in markup
            assert 'antes de pagar' not in markup
            if row['referencia'] == 'A13-01':
                assert 'GALAXY A13 5G/ A04S' in markup.replace('<wbr>', '')
                assert 'GALAXY A13(5G)/ A04S' in markup.replace('<wbr>', '')
            if row['referencia'].startswith('IP17PM-'):
                assert 'MODELOS INDICADOS POR EL PROVEEDOR' in markup
                assert 'pendiente de comprobar físicamente' in markup
                assert 'según la etiqueta del proveedor' in row['texto']
                assert 'Pro Max' in row['nombre_anuncio']
                assert 'normal' not in row['nombre_anuncio']
            elif row['referencia'].startswith('IP14-'):
                assert row['nombre_anuncio'] == 'iPhone 13 normal / iPhone 14 normal'
                assert 'iPhone 13 normal' in markup and 'iPhone 14 normal' in markup
            elif row['referencia'] == 'IPX-01':
                assert row['nombre_anuncio'] == 'iPhone X normal'
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


def test_campaign_preserves_exact_system_fields_and_uses_current_price():
    seed = [dict(sku='A13-01', name='GALAXY A13', compatibility='GALAXY A13', brand='Samsung', stock=30, price_cents=200)]
    current = dict(sku='A13-01', name='GALAXY A13 5G/ A04S', compatibility='GALAXY A13(5G)/ A04S', brand='Samsung', stock=26, price_cents=215)
    merged = apply_campaign_data(seed, dict(captured_date='2026-10-07', products=[current]))
    assert {k: merged[0][k] for k in current} == current
    assert seed[0]['name'] == 'GALAXY A13'
    assert seed[0]['price_cents'] == 200


@pytest.mark.parametrize('missing', ['name', 'compatibility', 'brand', 'price_cents'])
def test_campaign_requires_current_system_fields_instead_of_falling_back_to_seed(missing):
    current = dict(sku='A13-01', name='GALAXY A13 5G/ A04S', compatibility='GALAXY A13(5G)/ A04S', brand='Samsung', stock=26, price_cents=200)
    current.pop(missing)
    with pytest.raises(ValueError):
        apply_campaign_data([dict(sku='A13-01', stock=30)], dict(captured_date='2026-10-07', products=[current]))


@pytest.mark.parametrize(('name', 'expected'), [('iPhone 13/14', 'iPhone 13 normal / iPhone 14 normal'),
                                             ('iPhone X', 'iPhone X normal'),
                                             ('iPhone 17PM/ 18PM', 'iPhone 17 Pro Max / iPhone 18 Pro Max'),
                                             ('iPhone 14 Pro', 'iPhone 14 Pro')])
def test_iphone_label_distinguishes_normal_and_pro_without_changing_system_data(name, expected):
    product = dict(name=name, compatibility=name, brand='Apple')
    assert display_label(product) == expected
    assert product['name'] == name and product['compatibility'] == name
