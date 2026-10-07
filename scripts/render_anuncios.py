"""Export HTML ads with Chromium. Requires Playwright only on the export machine."""
import argparse
import csv
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'output/meta-ads')
    parser.add_argument('--chromium', help='Optional installed Chromium executable')
    args = parser.parse_args()
    with (args.output / 'REFERENCIAS.csv').open(encoding='utf-8-sig', newline='') as file:
        rows = list(csv.DictReader(file))
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.chromium, headless=True)
        page = browser.new_page(device_scale_factor=1)
        for row in rows:
            for column, height in (('publicacion', 1350), ('historia', 1920)):
                target = args.output / row[column]
                page.set_viewport_size({'width': 1080, 'height': height})
                page.set_content(target.with_suffix('.html').read_text(encoding='utf-8'), wait_until='load')
                assert page.locator('.photo img').evaluate('(img) => img.complete && img.naturalWidth > 0')
                assert page.evaluate('document.documentElement.scrollWidth') == 1080
                for selector in ('.stock', '.models', '.terms', '.cta', '.sku'):
                    box = page.locator(selector).bounding_box()
                    assert box and box['y'] >= 0 and box['y'] + box['height'] <= height, (target, selector)
                assert page.locator('.stock strong').inner_text() == f"QUEDAN {row['unidades_restantes']} UNIDADES"
                assert page.locator('.models strong').inner_text() == row['nombre_anuncio']
                if row['compatibilidad_anuncio'] != row['nombre_anuncio']:
                    assert page.locator('.compatibility b').inner_text() == row['compatibilidad_anuncio']
                assert page.locator('.minimum strong').inner_text() == 'MÍNIMO 3 UNIDADES MIXTAS'
                assert page.locator('.minimum small').inner_text() == 'Puedes combinar modelos y diseños'
                assert page.locator('.sku').inner_text() == f"REFERENCIA {row['referencia']} · Confirma disponibilidad"
                assert page.locator('.photo').bounding_box()['height'] >= 240
                page.screenshot(path=str(target), **({'quality': 95} if target.suffix == '.jpg' else {}))
            print(f"Exportada {row['referencia']}: {row['unidades_restantes']} unidades", flush=True)
        browser.close()
    print(f'{len(rows)*2} imágenes verificadas: stock, dimensiones y textos dentro del lienzo.')


if __name__ == '__main__':
    main()
