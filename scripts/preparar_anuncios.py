"""Generate dated campaign documents using an explicit Oracle stock snapshot."""
import argparse
import base64
import csv
from datetime import date
from html import escape
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shop import model_names


def display_label(product, field='name'):
    """Clarify base iPhones without overwriting the original system strings."""
    if product['brand'] != 'Apple':
        return product[field]
    names = model_names(dict(compatibility=product[field]))
    return ' / '.join(name if re.search(r'\bPro\b', name, re.I) else f'{name} normal' for name in names)


def supplier_compatibility(product):
    return any('18 Pro Max' in model for model in model_names(product))


def apply_stock(products, snapshot):
    """Never silently substitute historical seed quantities for current stock."""
    captured = date.fromisoformat(snapshot['captured_date'])
    stocks = {}
    for row in snapshot['products']:
        sku, stock = row['sku'], row['stock']
        if sku in stocks or type(stock) is not int or stock < 0:
            raise ValueError(f'Existencias inválidas o referencia duplicada: {sku}')
        stocks[sku] = stock
    active = [p for p in products if p.get('active', True)]
    if set(stocks) != {p['sku'] for p in active}:
        raise ValueError('La consulta de existencias debe cubrir exactamente las referencias activas del catálogo.')
    return [dict(p, stock=stocks[p['sku']], stock_date=captured.strftime('%d/%m/%Y')) for p in active]


def apply_campaign_data(products, snapshot):
    """Use names, compatibility and prices from the same system query as stock."""
    merged = apply_stock(products, snapshot)
    current = {p['sku']: p for p in snapshot['products']}
    for product in merged:
        row = current[product['sku']]
        for field in ('name', 'compatibility', 'brand'):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"Falta {field} del sistema para {product['sku']}; exporta el catálogo completo de Oracle.")
            product[field] = row[field]
        if type(row.get('price_cents')) is not int or row['price_cents'] < 0:
            raise ValueError(f"Precio del sistema inválido para {product['sku']}.")
        product['price_cents'] = row['price_cents']
    return merged


def photo_source(product, original=False):
    source = (ROOT / product['image_path']).resolve()
    if not source.is_relative_to(ROOT / 'assets'):
        raise ValueError('La foto debe estar dentro de assets/.')
    enhanced = ROOT / 'assets/products_hd' / f"{product['sku']}.png"
    return source if original or not enhanced.exists() else enhanced


def ad_document(product, story=False, original=False):
    source = photo_source(product, original)
    photo = base64.b64encode(source.read_bytes()).decode('ascii')
    # Keep the actual system strings, including variants, case and slash groups.
    label = display_label(product)
    compatibility_label = display_label(product, 'compatibility')
    model_text = escape(label).replace('/', '/<wbr>')
    compatibility_text = escape(compatibility_label).replace('/', '/<wbr>')
    compatibility_note = (f'<div class="compatibility"><span>Compatible con: </span><b>{compatibility_text}</b></div>'
                          if compatibility_label != label else '')
    supplier = supplier_compatibility(product)
    model_heading = 'MODELOS INDICADOS POR EL PROVEEDOR' if supplier else 'SOLO PARA ESTOS MODELOS'
    fit_note = '<em>Compatibilidad pendiente de comprobar físicamente</em>' if supplier else ''
    price = f"${product['price_cents'] / 100:.2f}"
    height = 1920 if story else 1350
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=1080,initial-scale=1"><title>{escape(product['sku'])}</title>
<style>
*{{box-sizing:border-box}}html,body{{margin:0;width:1080px;height:{height}px;font-family:Arial,sans-serif;color:#173e31;background:#f6f5ef}}
.ad{{width:1080px;height:{height}px;padding:{210 if story else 54}px 64px {240 if story else 54}px;display:flex;flex-direction:column;gap:24px;overflow:hidden}}
.brand{{font-weight:800;font-size:29px;letter-spacing:5px;display:flex;justify-content:space-between;align-items:center}}
.brand small{{font-size:19px;letter-spacing:2px;color:#557461}}
.topline{{font-size:20px;color:#557461;font-weight:700;letter-spacing:3px;margin-top:4px}}
.photo{{min-height:0;flex:1;display:flex;align-items:center;justify-content:center;background:#fff;border:1px solid #d9e1d7;border-radius:32px;overflow:hidden}}
.photo img{{height:100%;width:100%;object-fit:contain;display:block}}
.stock{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:15px 22px;background:#e9dfc6;border-radius:18px}}
.stock strong{{font-size:32px;line-height:1.15}}.stock small{{font-size:18px;line-height:1.3;color:#557461;text-align:right}}
.models{{text-align:center;background:#123e32;color:#fff;border-radius:26px;padding:26px 20px}}
.models small{{display:block;font-size:20px;font-weight:700;color:#e6c68a;letter-spacing:3px;margin-bottom:14px}}
.models strong{{font-size:{48 if len(label)>30 else 56 if len(label)>22 else 60}px;line-height:1.15;display:block}}
.compatibility{{font-size:24px;line-height:1.35;margin-top:12px;color:#fff}}
.models em{{display:block;font-size:19px;font-style:normal;line-height:1.4;color:#e6c68a;margin-top:12px}}
.terms{{display:flex;align-items:center;justify-content:space-between;gap:20px}}
.terms strong{{font-size:44px;line-height:1.1}}.terms small{{display:block;font-size:19px;font-weight:400;margin-top:7px;color:#557461}}
.minimum{{font-size:26px;font-weight:700;border-radius:18px;background:#e9dfc6;padding:16px 22px}}
.minimum strong{{display:block;font-size:26px;line-height:1.2}}.minimum small{{font-size:20px;font-weight:600;color:#173e31}}
.cta{{font-size:27px;font-weight:700;text-align:center;line-height:1.4}}
.cta small{{display:block;font-size:20px;font-weight:400;color:#557461;margin-top:6px}}
.sku{{font-size:16px;color:#557461;letter-spacing:1px;text-align:center}}
</style></head><body><article class="ad" aria-label="Anuncio de protector {escape(product['sku'])}">
<div class="brand">IMPORTADORA <small>TIENDA EN LÍNEA</small></div>
<div class="topline">PROTECTORES PARA TU NEGOCIO</div>
<div class="photo"><img src="data:image/png;base64,{photo}" alt="Protector referencia {escape(product['sku'])}"></div>
<div class="stock"><strong>QUEDAN {product['stock']} UNIDADES</strong><small>Stock al {escape(product['stock_date'])}<br>Existencias por referencia</small></div>
<div class="models"><small>{model_heading}</small><strong>{model_text}</strong>{compatibility_note}{fit_note}</div>
<div class="terms"><div><strong>{price}</strong><small>USD por unidad · precio mayorista</small></div><div class="minimum"><strong>MÍNIMO 3 UNIDADES MIXTAS</strong><small>Puedes combinar modelos y diseños</small></div></div>
<div class="cta">Pide al 7311 3611<small>Todo el país · Envío económico a puntos específicos<br>Domicilio $5 · Tarifa económica según el total de compra</small></div>
<div class="sku">REFERENCIA {escape(product['sku'])} · Confirma disponibilidad</div>
</article></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', type=Path, default=ROOT / 'data/catalog_seed.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/meta-ads')
    parser.add_argument('--stock-file', type=Path, default=ROOT / 'data/campaign_stock.json')
    parser.add_argument('--original-photos', action='store_true', help='Usar las fotografías del proveedor sin mejora digital.')
    parser.add_argument('--image-format', choices=('jpg', 'png'), default='jpg')
    parser.add_argument('--web-url', default='', help='URL real del catálogo para generar enlaces; no incluir secretos.')
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.stock_file.read_text(encoding='utf-8'))
        products = apply_campaign_data(json.loads(args.catalog.read_text(encoding='utf-8'))['products'], snapshot)
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(f'No se pueden generar anuncios con stock real: {error}')
    args.output.mkdir(parents=True, exist_ok=True)
    campaign_snapshot = dict(captured_date=snapshot['captured_date'],
                             timezone=snapshot.get('timezone', 'America/El_Salvador'),
                             source=snapshot.get('source', 'Consulta de Oracle'),
                             products=[{k: p[k] for k in ('sku', 'name', 'compatibility', 'brand', 'price_cents', 'stock')}
                                       for p in snapshot['products']])
    (args.output / 'DATOS-SISTEMA.json').write_text(json.dumps(campaign_snapshot, ensure_ascii=False, indent=2), encoding='utf-8')
    rows, needs_review = [], []
    for product in products:
        if not product.get('active', True) or product['stock'] <= 0:
            continue
        supplier = supplier_compatibility(product)
        if supplier:
            needs_review.append(product['sku'])
        folder = 'iPhone' if product['brand'] == 'Apple' else 'Samsung' if product['brand'] == 'Samsung' else 'Otros'
        (args.output / folder).mkdir(exist_ok=True)
        for story in (False, True):
            name = f"{product['sku']}-{'story' if story else 'feed'}.html"
            (args.output / folder / name).write_text(ad_document(product, story, args.original_photos), encoding='utf-8')
        query = dict(vista='pedidos', ref=product['sku'], utm_source='meta', utm_medium='paid_social',
                     utm_campaign='protectores_mayorista', utm_content=product['sku'])
        if args.web_url:
            if not args.web_url.startswith('https://') or '?' in args.web_url or '#' in args.web_url:
                parser.error('--web-url debe ser HTTPS sin parámetros ni fragmentos.')
            link = args.web_url.rstrip('/') + '/?' + urlencode(query)
        else:
            link = '/?' + urlencode(query)
        models = display_label(product, 'compatibility')
        copy = (f"Protectores SOLO para {models}. {product['sku']}: ${product['price_cents']/100:.2f} por unidad. "
                f"Quedan {product['stock']} unidades de esta referencia (stock al {product['stock_date']}; compartido entre sus modelos compatibles). "
                'Pedido mayorista mínimo: 3 unidades mixtas. Puedes combinar modelos y diseños disponibles en un mismo pedido. Tienda en línea, sin local físico. '
                'Envíos a todo el país: económico a puntos específicos con costo según el total de tu compra, '
                'o personalizado a domicilio por $5. '
                f'Escríbenos: quiero {product["sku"]}, mi teléfono es ___ y necesito ___ unidades. '
                'Confirmamos disponibilidad.')
        if supplier:
            copy = copy.replace(f'Protectores SOLO para {models}.', f'Protectores para {models}, según la etiqueta del proveedor. Compatibilidad pendiente de comprobar físicamente.')
        rows.append(dict(referencia=product['sku'], modelos=product['compatibility'], precio_usd=f"{product['price_cents']/100:.2f}",
                         nombre_sistema=product['name'], compatibilidad_sistema=product['compatibility'],
                         nombre_anuncio=display_label(product), compatibilidad_anuncio=models,
                         unidades_restantes=product['stock'], fecha_stock=product['stock_date'],
                         fotografia='Mejora digital' if photo_source(product, args.original_photos).parent.name == 'products_hd' else 'Original del proveedor',
                         titulo=f'{"Según proveedor: " if supplier else "Solo "}{display_label(product)} · Desde 3 unidades mixtas', texto=copy, enlace=link,
                         carpeta=folder, estado_compatibilidad='Proveedor: confirmar ajuste físico' if supplier else 'Catálogo: confirmar variante y disponibilidad'))
    with (args.output / 'copys-y-enlaces.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['referencia','nombre_sistema','compatibilidad_sistema','nombre_anuncio','compatibilidad_anuncio','modelos','precio_usd','unidades_restantes','fecha_stock','fotografia','titulo','texto','enlace','carpeta','estado_compatibilidad'])
        writer.writeheader(); writer.writerows(rows)
    with (args.output / 'REFERENCIAS.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['referencia','nombre_sistema','compatibilidad_sistema','nombre_anuncio','compatibilidad_anuncio','modelos','unidades_restantes','fecha_stock','fotografia','publicacion','historia','estado_compatibilidad'])
        writer.writeheader()
        writer.writerows(dict(referencia=r['referencia'], modelos=r['modelos'],
                              nombre_sistema=r['nombre_sistema'], compatibilidad_sistema=r['compatibilidad_sistema'],
                              nombre_anuncio=r['nombre_anuncio'], compatibilidad_anuncio=r['compatibilidad_anuncio'],
                              unidades_restantes=r['unidades_restantes'], fecha_stock=r['fecha_stock'], fotografia=r['fotografia'],
                              publicacion=f"{r['carpeta']}/{r['referencia']}-feed.{args.image_format}",
                              historia=f"{r['carpeta']}/{r['referencia']}-story.{args.image_format}",
                              estado_compatibilidad=r['estado_compatibilidad']) for r in rows)
    with (args.output / 'PRIORIDAD-STOCK.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['referencia','nombre_sistema','compatibilidad_sistema','modelos','unidades_restantes','fecha_stock'])
        writer.writeheader()
        writer.writerows({k:r[k] for k in writer.fieldnames} for r in sorted(rows, key=lambda r:(-r['unidades_restantes'],r['referencia'])))
    previews = ''
    for folder in sorted({r['carpeta'] for r in rows}):
        group = sorted([r for r in rows if r['carpeta'] == folder], key=lambda r:(-r['unidades_restantes'],r['referencia']))
        previews += f'<h2>{escape(folder)} · {len(group)} referencias · {len(group)*2} imágenes</h2><main>'
        previews += ''.join(f'<figure><a href="{folder}/{r["referencia"]}-feed.{args.image_format}"><img src="{folder}/{r["referencia"]}-feed.{args.image_format}" alt="{escape(r["modelos"])}"></a><figcaption>{escape(r["referencia"])} · {escape(r["nombre_anuncio"])}<br>Compatible con: {escape(r["compatibilidad_anuncio"])}<br><strong>Quedan {r["unidades_restantes"]} unidades</strong> · {r["fecha_stock"]}<br>{escape(r["estado_compatibilidad"])}<br><a href="{folder}/{r["referencia"]}-feed.{args.image_format}">Feed</a> · <a href="{folder}/{r["referencia"]}-story.{args.image_format}">Historia</a></figcaption></figure>' for r in group)
        previews += '</main>'
    (args.output / 'index.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Piezas de IMPORTADORA</title><style>body{font:16px Arial;background:#f6f5ef;color:#173e31;margin:30px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px}figure{margin:0}img{width:100%;border-radius:12px}figcaption{padding:10px;line-height:1.6}</style><h1>Anuncios por referencia</h1>' + f'<p>{len(rows)} referencias · {len(rows)*2} imágenes · {sum(r["unidades_restantes"] for r in rows)} unidades al {products[0]["stock_date"]}. Cada referencia es un diseño; sus modelos compatibles comparten stock.</p><p>{args.image_format.upper()}: feed 1080×1350; historias 1080×1920. Fotos optimizadas digitalmente; originales conservados en el repositorio. Las cantidades impresas no se actualizan con las ventas.</p>' + previews + '</html>', encoding='utf-8')
    (args.output / 'LEEME.txt').write_text(f'{len(rows)} referencias, {len(rows)*2} imágenes: cada referencia tiene publicación e historia.\nStock: {sum(r["unidades_restantes"] for r in rows)} unidades al {products[0]["stock_date"]}, consulta de Oracle compartida por el propietario.\nCantidad por referencia, compartida entre sus modelos compatibles. No se actualiza automáticamente con las ventas.\nCarpetas por marca: Samsung e iPhone.\nFotos optimizadas digitalmente: no recuperan con certeza detalles ilegibles; originales conservados en assets/products.\nNombres, compatibilidades, precios y existencias proceden de una misma consulta de Oracle. Los campos originales se conservan en los CSV. Confirma disponibilidad. Mínimo: 3 unidades mixtas; puedes combinar modelos y diseños.\nIncluidos como borradores con etiqueta del proveedor, pendientes de ajuste físico (iPhone 17PM/18PM): ' + ', '.join(needs_review) + '\nEnlaces relativos: anteponer la URL real de tu tienda si no usaste --web-url.\nLos parámetros UTM etiquetan enlaces; esta app no incorpora medición de conversiones de Meta.\n', encoding='utf-8')
    print(f'{len(rows)} referencias, {len(rows)*2} documentos. Incluidos con nota del proveedor: {", ".join(needs_review)}. Salida: {args.output}')


if __name__ == '__main__':
    main()
