"""Bundle dated ads, source photos, editable HTML and CSVs for GitHub downloads."""
import csv
import hashlib
from html import escape
import io
import json
from pathlib import Path
import re
import shutil
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]


def csv_bytes(rows, fields):
    output = io.StringIO(newline='')
    writer = csv.DictWriter(output, fieldnames=fields)
    writer.writeheader()
    writer.writerows({key: row[key] for key in fields} for row in rows)
    return output.getvalue().encode('utf-8-sig')


def bundle(name, rows, output):
    ads = ROOT / 'output/meta-ads'
    expected = {row[key] for row in rows for key in ('publicacion', 'historia')}
    stock = json.loads((ROOT / 'data/campaign_stock.json').read_text(encoding='utf-8'))
    stock['products'] = [p for p in stock['products'] if p['sku'] in {r['referencia'] for r in rows}]
    with ZipFile(output / name, 'w', ZIP_DEFLATED) as archive:
        for row in rows:
            sku = row['referencia']
            for key in ('publicacion', 'historia'):
                relative = row[key]
                archive.write(ads / relative, relative)
                markup = (ads / relative).with_suffix('.html').read_text(encoding='utf-8')
                match = re.search(r'data:image/png;base64,([A-Za-z0-9+/=]+)', markup)
                if not match:
                    raise ValueError(f'Falta fotografía incrustada: {relative}')
                import base64
                source_photo = base64.b64decode(match[1], validate=True)
                markup = markup.replace(match[0], f'../Fotos/{sku}.png')
                archive.writestr(str(Path(relative).with_suffix('.html')), markup)
            archive.writestr(f'Fotos/{sku}.png', source_photo)
        archive.writestr('REFERENCIAS.csv', csv_bytes(rows, list(rows[0])))
        with (ads / 'copys-y-enlaces.csv').open(encoding='utf-8-sig', newline='') as file:
            copys = [r for r in csv.DictReader(file) if r['referencia'] in {r['referencia'] for r in rows}]
        archive.writestr('copys-y-enlaces.csv', csv_bytes(copys, list(copys[0])))
        ordered = sorted(rows, key=lambda r: (-int(r['unidades_restantes']), r['referencia']))
        archive.writestr('PRIORIDAD-STOCK.csv', csv_bytes(ordered, ['referencia','modelos','unidades_restantes','fecha_stock']))
        archive.writestr('STOCK-ORACLE.json', json.dumps(stock, ensure_ascii=False, indent=2))
        figures = ''.join(f'<figure><a href="{r["publicacion"]}"><img src="{r["publicacion"]}" alt="{escape(r["modelos"])}"></a><figcaption>{r["referencia"]} · {escape(r["modelos"])}<br><b>Quedan {r["unidades_restantes"]} unidades</b> · {r["fecha_stock"]}<br><a href="{r["publicacion"]}">Publicación</a> · <a href="{r["historia"]}">Historia</a><br>{escape(r["estado_compatibilidad"])}</figcaption></figure>' for r in ordered)
        archive.writestr('index.html', '<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IMPORTADORA: anuncios</title><style>body{font:16px Arial;background:#f6f5ef;color:#173e31;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px}figure{margin:0}img{width:100%;border-radius:16px}figcaption{line-height:1.6}</style>' + f'<h1>{len(rows)} referencias · {len(expected)} imágenes</h1><p>Stock al {rows[0]["fecha_stock"]}. Ordenadas por unidades restantes.</p><main>{figures}</main></html>')
        archive.writestr('LEEME.txt', f'{len(rows)} referencias, {len(expected)} imágenes JPG de alta calidad (95%).\nPublicación: 1080x1350. Historia: 1080x1920.\nUnidades restantes al {rows[0]["fecha_stock"]}: {sum(int(r["unidades_restantes"]) for r in rows)}.\nStock por referencia, compartido entre sus modelos compatibles. No se actualiza automáticamente con las ventas.\nHTML editable incluido; Fotos contiene cada fotografía usada una sola vez.\nLas fotografías son mejoras digitales de fuentes pequeñas. No recuperan con certeza detalles originalmente ilegibles. Los originales están conservados en el repositorio.\nIP17PM-01/02/03: etiqueta del proveedor; ajuste físico pendiente, indicado en cada imagen.\nPrecios y compatibilidades del catálogo; confirmar antes de publicar.\nEnlaces del CSV relativos: anteponer la URL real de la tienda.\nMínimo mayorista: 3 unidades combinadas.\n')
    with ZipFile(output / name) as archive:
        assert archive.testzip() is None
        assert {p for p in archive.namelist() if p.endswith(('.jpg', '.jpeg'))} == expected
    size = (output / name).stat().st_size
    assert size < 100 * 1024 * 1024, 'El ZIP supera el límite de GitHub.'
    print(f'{name}: {len(rows)} referencias, {len(expected)} imágenes, {size:,} bytes')


def main():
    with (ROOT / 'output/meta-ads/REFERENCIAS.csv').open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    output = ROOT / 'descargas'
    output.mkdir(exist_ok=True)
    bundle('meta-ads-importadora.zip', rows, output)
    bundle('anuncios-iphone.zip', [r for r in rows if r['referencia'].startswith('IP')], output)
    bundle('primera-campana-A06-A13-A15.zip', [r for r in rows if r['referencia'] in {'A06-03','A13-01','A15-01'}], output)
    priority = sorted((r for r in rows if not r['referencia'].startswith('IP17PM-')), key=lambda r: (-int(r['unidades_restantes']),r['referencia']))[:5]
    bundle('campana-stock-prioritario.zip', priority, output)
    shutil.copy2(ROOT / 'output/importadora-publicar.zip', output / 'importadora-publicar.zip')
    checksums = ''.join(f'{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n' for path in sorted(output.glob('*.zip')))
    (output / 'SHA256SUMS').write_text(checksums, encoding='utf-8')


if __name__ == '__main__':
    main()
