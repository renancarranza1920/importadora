"""Extract this catalog by card position; retain the final overlaid model names."""
import argparse
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def extract(source: Path):
    doc = pymupdf.open(source)
    products = []
    for page_no, page in enumerate(doc):
        spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b
                 for line in b["lines"] for s in line["spans"]]
        refs = [s for s in spans if s["text"].startswith("REF. ")]
        for ref in refs:
            x, y = ref["bbox"][:2]
            col = 0 if x < 300 else 1
            row = round((y - 108) / 241.63)
            left, top = 36 + col * 270, 90 + row * 241.63
            card = [s for s in spans if left <= s["bbox"][0] < left + 260
                    and top <= s["bbox"][1] < top + 230]
            # PDF contains older hidden text; the final visible model is drawn last.
            names = [s["text"] for s in card if s["text"].startswith(("GALAXY ", "iPhone ", "NOTE ", "A36 "))]
            prices = [s["text"] for s in card if re.fullmatch(r"\d+\.\d{2}", s["text"])]
            quantities = [s["text"] for s in card if s["text"].startswith("CANTIDAD:")]
            assert names and len(prices) == len(quantities) == 1, (page_no, ref)
            sku = ref["text"].removeprefix("REF. ")
            pics = [i for i in page.get_image_info(xrefs=True)
                    if left <= i["bbox"][0] < left + 260 and top <= i["bbox"][1] < top + 230]
            assert len(pics) == 1, sku
            picture = doc.extract_image(pics[0]["xref"])
            path = f"assets/products/{sku}.{picture['ext']}"
            (ROOT / path).write_bytes(picture["image"])
            name = names[-1].strip()
            products.append(dict(sku=sku, name=name, compatibility=name,
                brand="Apple" if name.startswith("iPhone") else "Samsung",
                category="Protectores", price_cents=int(Decimal(prices[0]) * 100),
                stock=int(quantities[0].split(":")[1]), image_path=path,
                source_page=page_no + 1, low_stock=5,
                notes="Modelos compatibles conservados tal como aparecen en el catálogo."))
    assert len(products) == len({p["sku"] for p in products}) == 24
    payload = {"source_file": source.name,
               "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "currency": "USD", "price_type": "Precio mayorista del PDF",
               "products": products}
    (ROOT / "data/catalog_seed.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(p["stock"] for p in products)
    value = sum(p["stock"] * p["price_cents"] for p in products)
    print(f"Imported {len(products)} references; {total} units; USD {value / 100:.2f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    extract(parser.parse_args().pdf)
