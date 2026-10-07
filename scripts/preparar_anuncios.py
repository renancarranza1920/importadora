"""Generate self-contained ad documents from original, unaltered product photos.

No external service or credentials. Render the documents to PNG with a browser.
The seed is a historical catalog, not a live-stock assertion.
"""
import argparse
import base64
import csv
from html import escape
import json
from pathlib import Path
import sys
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from shop import model_names


def supplier_compatibility(product):
    return any('18 Pro Max' in model for model in model_names(product))


def ad_document(product, story=False):
    # Display the original bytes intact; do not reconstruct the actual product.
    source = (ROOT / product['image_path']).resolve()
    if not source.is_relative_to(ROOT / 'assets'):
        raise ValueError('La foto debe estar dentro de assets/.')
    photo = base64.b64encode(source.read_bytes()).decode('ascii')
    models = model_names(product)
    model_text = '<br>'.join(escape(m) for m in models)
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
.models{{text-align:center;background:#123e32;color:#fff;border-radius:26px;padding:26px 20px}}
.models small{{display:block;font-size:20px;font-weight:700;color:#e6c68a;letter-spacing:3px;margin-bottom:14px}}
.models strong{{font-size:{48 if len(models)>2 else 60}px;line-height:1.15;display:block}}
.models em{{display:block;font-size:19px;font-style:normal;line-height:1.4;color:#e6c68a;margin-top:12px}}
.terms{{display:flex;align-items:center;justify-content:space-between;gap:20px}}
.terms strong{{font-size:44px;line-height:1.1}}.terms small{{display:block;font-size:19px;font-weight:400;margin-top:7px;color:#557461}}
.minimum{{font-size:26px;font-weight:700;border-radius:18px;background:#e9dfc6;padding:16px 22px}}
.cta{{font-size:27px;font-weight:700;text-align:center;line-height:1.4}}
.cta small{{display:block;font-size:20px;font-weight:400;color:#557461;margin-top:6px}}
.sku{{font-size:16px;color:#557461;letter-spacing:1px;text-align:center}}
</style></head><body><article class="ad" aria-label="Anuncio de protector {escape(product['sku'])}">
<div class="brand">IMPORTADORA <small>TIENDA EN LÍNEA</small></div>
<div class="topline">PROTECTORES PARA TU NEGOCIO</div>
<div class="photo"><img src="data:image/png;base64,{photo}" alt="Protector original {escape(product['sku'])}"></div>
<div class="models"><small>{model_heading}</small><strong>{model_text}</strong>{fit_note}</div>
<div class="terms"><div><strong>{price}</strong><small>USD por unidad · precio mayorista</small></div><div class="minimum">MÍNIMO 3 UNIDADES</div></div>
<div class="cta">Combina modelos · Pide al 7311 3611<small>Todo el país · Envío económico a puntos específicos<br>Domicilio $5 · Tarifa económica según el total de compra</small></div>
<div class="sku">REFERENCIA {escape(product['sku'])} · Disponibilidad por confirmar</div>
</article></body></html>'''


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--catalog', type=Path, default=ROOT / 'data/catalog_seed.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'output/meta-ads')
    parser.add_argument('--web-url', default='', help='URL real del catálogo para generar enlaces; no incluir secretos.')
    args = parser.parse_args()
    products = json.loads(args.catalog.read_text(encoding='utf-8'))['products']
    args.output.mkdir(parents=True, exist_ok=True)
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
            (args.output / folder / name).write_text(ad_document(product, story), encoding='utf-8')
        query = dict(vista='pedidos', ref=product['sku'], utm_source='meta', utm_medium='paid_social',
                     utm_campaign='protectores_mayorista', utm_content=product['sku'])
        if args.web_url:
            if not args.web_url.startswith('https://') or '?' in args.web_url or '#' in args.web_url:
                parser.error('--web-url debe ser HTTPS sin parámetros ni fragmentos.')
            link = args.web_url.rstrip('/') + '/?' + urlencode(query)
        else:
            link = '/?' + urlencode(query)
        models = ' / '.join(model_names(product))
        copy = (f"Protectores SOLO para {models}. {product['sku']}: ${product['price_cents']/100:.2f} por unidad. "
                'Venta mayorista desde 3 unidades combinadas. Tienda en línea, sin local físico. '
                'Envíos a todo el país: económico a puntos específicos con costo según el total de tu compra, '
                'o personalizado a domicilio por $5. '
                f'Escríbenos: quiero {product["sku"]}, mi teléfono es ___ y necesito ___ unidades. '
                'Confirmamos disponibilidad, compatibilidad y total con envío antes de pagar.')
        if supplier:
            copy = copy.replace(f'Protectores SOLO para {models}.', f'Protectores para {models}, según la etiqueta del proveedor. Compatibilidad pendiente de comprobar físicamente.')
        rows.append(dict(referencia=product['sku'], modelos=models, precio_usd=f"{product['price_cents']/100:.2f}",
                         titulo=f'{"Según proveedor: " if supplier else "Solo "}{models} · Desde 3 unidades', texto=copy, enlace=link,
                         carpeta=folder, estado_compatibilidad='Proveedor: confirmar ajuste físico' if supplier else 'Catálogo: confirmar variante y disponibilidad'))
    with (args.output / 'copys-y-enlaces.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['referencia','modelos','precio_usd','titulo','texto','enlace','carpeta','estado_compatibilidad'])
        writer.writeheader(); writer.writerows(rows)
    with (args.output / 'REFERENCIAS.csv').open('w', encoding='utf-8-sig', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=['referencia','modelos','publicacion','historia','estado_compatibilidad'])
        writer.writeheader()
        writer.writerows(dict(referencia=r['referencia'], modelos=r['modelos'],
                              publicacion=f"{r['carpeta']}/{r['referencia']}-feed.png",
                              historia=f"{r['carpeta']}/{r['referencia']}-story.png",
                              estado_compatibilidad=r['estado_compatibilidad']) for r in rows)
    previews = ''
    for folder in sorted({r['carpeta'] for r in rows}):
        group = [r for r in rows if r['carpeta'] == folder]
        previews += f'<h2>{escape(folder)} · {len(group)} referencias · {len(group)*2} imágenes</h2><main>'
        previews += ''.join(f'<figure><a href="{folder}/{r["referencia"]}-feed.html"><img src="{folder}/{r["referencia"]}-feed.png" alt="{escape(r["modelos"])}"></a><figcaption>{escape(r["referencia"])} · {escape(r["modelos"])}<br>{escape(r["estado_compatibilidad"])}<br><a href="{folder}/{r["referencia"]}-feed.html">Feed</a> · <a href="{folder}/{r["referencia"]}-story.html">Historia</a></figcaption></figure>' for r in group)
        previews += '</main>'
    (args.output / 'index.html').write_text('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Piezas de IMPORTADORA</title><style>body{font:16px Arial;background:#f6f5ef;color:#173e31;margin:30px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:20px}figure{margin:0}img{width:100%;border-radius:12px}figcaption{padding:10px;line-height:1.6}</style><h1>Anuncios por referencia</h1>' + f'<p>{len(rows)} referencias · {len(rows)*2} imágenes en dos formatos. Cada referencia es un diseño; puede admitir varios modelos de teléfono.</p>' + '<p>Borradores basados en el catálogo inicial. Confirmar precio, existencias y compatibilidad antes de invertir. PNG: feed 1080×1350; historias 1080×1920.</p>' + previews + '</html>', encoding='utf-8')
    (args.output / 'LEEME.txt').write_text(f'{len(rows)} referencias, {len(rows)*2} imágenes: cada referencia tiene publicación e historia.\nCarpetas por marca: Samsung e iPhone.\nPiezas generadas con fotografías originales, sin alterar el producto.\nFuente: ' + str(args.catalog) + '\nNo representa el inventario actual de Oracle.\nConfirma precios, existencias y compatibilidades antes de publicar.\nIncluidos como borradores con etiqueta del proveedor, pendientes de ajuste físico (iPhone 17PM/18PM): ' + ', '.join(needs_review) + '\nEnlaces relativos: anteponer la URL real de tu tienda si no usaste --web-url.\nLos parámetros UTM etiquetan enlaces; esta app no incorpora medición de conversiones de Meta.\n', encoding='utf-8')
    print(f'{len(rows)} referencias, {len(rows)*2} documentos. Incluidos con nota del proveedor: {", ".join(needs_review)}. Salida: {args.output}')


if __name__ == '__main__':
    main()
