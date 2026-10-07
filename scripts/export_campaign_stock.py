"""Read only: export public campaign fields from one dated system query."""
from datetime import datetime
import json
import os
import sys
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text


def main():
    url = os.environ.get('DATABASE_URL')
    if not url:
        import streamlit as st
        url = st.secrets.get('DATABASE_URL')
    if not url:
        raise SystemExit('Falta DATABASE_URL; ejecuta este script dentro del contenedor configurado.')
    url = url.replace('postgres://', 'postgresql+psycopg://', 1).replace('postgresql://', 'postgresql+psycopg://', 1)
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text('SELECT sku, name, compatibility, brand, price_cents, stock FROM products WHERE active = true ORDER BY sku'))
            products = [dict(row) for row in rows.mappings()]
        if not products:
            raise SystemExit('La consulta no devolvió referencias activas.')
        json.dump(dict(captured_date=datetime.now(ZoneInfo('America/El_Salvador')).date().isoformat(),
                       timezone='America/El_Salvador', source='Consulta de Oracle', products=products),
                  sys.stdout, ensure_ascii=False, indent=2)
        print()
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
