"""Persistent inventory and transactional sales. Money is stored as integer cents."""
from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import secrets
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps
from sqlalchemy import (Boolean, CheckConstraint, Column, Integer, LargeBinary,
                        MetaData, String, Table, Text, create_engine, event,
                        insert, select, update)
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parent
metadata = MetaData()
products = Table("products", metadata,
    Column("sku", String(60), primary_key=True), Column("name", String(200), nullable=False),
    Column("compatibility", Text, nullable=False), Column("brand", String(80), nullable=False),
    Column("category", String(80), nullable=False), Column("price_cents", Integer, nullable=False),
    Column("stock", Integer, nullable=False), Column("low_stock", Integer, nullable=False, default=5),
    Column("image_path", String(250), nullable=False, default=""), Column("image_data", LargeBinary),
    Column("source_page", Integer), Column("notes", Text, nullable=False, default=""),
    Column("active", Boolean, nullable=False, default=True), Column("version", Integer, nullable=False, default=1),
    CheckConstraint("stock >= 0"), CheckConstraint("price_cents >= 0"), CheckConstraint("low_stock >= 0"))
sales = Table("sales", metadata,
    Column("id", String(36), primary_key=True), Column("request_key", String(80), nullable=False, unique=True),
    Column("created_at", String(40), nullable=False), Column("customer", String(200), nullable=False),
    Column("payment", String(40), nullable=False), Column("notes", Text, nullable=False),
    Column("total_cents", Integer, nullable=False), Column("status", String(20), nullable=False),
    Column("void_reason", Text), Column("voided_at", String(40)))
sale_items = Table("sale_items", metadata,
    Column("id", String(36), primary_key=True), Column("sale_id", String(36), nullable=False, index=True),
    Column("sku", String(60), nullable=False), Column("name", String(200), nullable=False),
    Column("quantity", Integer, nullable=False), Column("unit_price_cents", Integer, nullable=False),
    CheckConstraint("quantity > 0"), CheckConstraint("unit_price_cents >= 0"))
movements = Table("movements", metadata,
    Column("id", String(36), primary_key=True), Column("created_at", String(40), nullable=False),
    Column("sku", String(60), nullable=False, index=True), Column("delta", Integer, nullable=False),
    Column("balance", Integer, nullable=False), Column("kind", String(30), nullable=False),
    Column("reason", Text, nullable=False), Column("sale_id", String(36)),
    Column("request_key", String(80), unique=True))
settings = Table("settings", metadata,
    Column("key", String(80), primary_key=True), Column("value", Text, nullable=False))
auth_attempts = Table("auth_attempts", metadata,
    Column("id", String(36), primary_key=True), Column("at", Integer, nullable=False, index=True))


class InventoryError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def cents(value):
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal("9999999.99"):
            raise InventoryError("El precio debe estar entre 0 y 9,999,999.99.")
        if amount != amount.quantize(Decimal("0.01")):
            raise InventoryError("El precio admite hasta dos decimales.")
        return int(amount * 100)
    except (InvalidOperation, TypeError):
        raise InventoryError("Escribe un precio válido.") from None


def integer(value, label, minimum=0, maximum=10000000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise InventoryError(f"{label}: usa un número entero entre {minimum} y {maximum}.")
    return value


def password_hash(password):
    if len(password) < 12:
        raise InventoryError("Usa una contraseña de al menos 12 caracteres.")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 600000)
    return f"pbkdf2_sha256$600000${salt}${digest.hex()}"


def verify_password(password, encoded):
    try:
        kind, rounds, salt, digest = encoded.split("$")
        if kind != "pbkdf2_sha256" or not 100000 <= int(rounds) <= 2000000:
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(rounds)).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError, AttributeError):
        return False


def clean_image(raw):
    if len(raw) > 5 * 1024 * 1024:
        raise InventoryError("La imagen debe pesar como máximo 5 MB.")
    try:
        with Image.open(io.BytesIO(raw)) as img:
            if img.width * img.height > 20000000:
                raise InventoryError("La imagen es demasiado grande; máximo 20 megapíxeles.")
            img = ImageOps.exif_transpose(img).convert("RGB")
            img.thumbnail((1000, 1000))
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=85)
            return out.getvalue()
    except (OSError, Image.DecompressionBombError):
        raise InventoryError("Selecciona una imagen JPG, PNG o WebP válida.") from None


class Inventory:
    def __init__(self, url, production=False):
        if production and not url.startswith(("postgresql://", "postgres://", "postgresql+psycopg://")):
            raise InventoryError("Configura una base PostgreSQL persistente en DATABASE_URL para publicar.")
        if url.startswith("postgres://"):
            url = "postgresql+psycopg://" + url.removeprefix("postgres://")
        elif url.startswith("postgresql://"):
            url = "postgresql+psycopg://" + url.removeprefix("postgresql://")
        self.engine = create_engine(url, pool_pre_ping=True,
            connect_args={"check_same_thread": False, "timeout": 30} if url.startswith("sqlite") else {})
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def setup_sqlite(connection, _):
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("PRAGMA journal_mode=WAL")
                connection.execute("PRAGMA busy_timeout=30000")
        metadata.create_all(self.engine)

    def seed(self, path=ROOT / "data/catalog_seed.json"):
        """One transaction; a unique marker prevents resetting stock on a restart."""
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        try:
            with self.engine.begin() as conn:
                if conn.execute(select(settings.c.value).where(settings.c.key == "catalog_v1")).first():
                    return False
                conn.execute(insert(settings).values(key="catalog_v1", value=payload["source_sha256"]))
                for item in payload["products"]:
                    conn.execute(insert(products).values(**item, active=True, version=1))
                    self._movement(conn, item["sku"], item["stock"], item["stock"], "initial",
                                   f"Inventario inicial · PDF página {item['source_page']}")
            return True
        except IntegrityError:
            with self.engine.connect() as conn:
                if conn.execute(select(settings.c.key).where(settings.c.key == "catalog_v1")).first():
                    return False
            raise

    @staticmethod
    def _movement(conn, sku, delta, balance, kind, reason, sale_id=None, request_key=None):
        conn.execute(insert(movements).values(id=str(uuid4()), created_at=now(), sku=sku,
            delta=delta, balance=balance, kind=kind, reason=reason, sale_id=sale_id, request_key=request_key))

    def list_products(self, include_archived=False):
        query = select(products).order_by(products.c.sku)
        if not include_archived:
            query = query.where(products.c.active.is_(True))
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(query).mappings()]

    def get_product(self, sku):
        with self.engine.connect() as conn:
            row = conn.execute(select(products).where(products.c.sku == sku)).mappings().first()
            if not row:
                raise InventoryError("El artículo ya no existe.")
            return dict(row)

    def save_product(self, item, expected_version=None, image=None):
        values = {k: str(item.get(k, "")).strip() for k in ("sku", "name", "compatibility", "brand", "category", "notes")}
        values["sku"] = values["sku"].upper()
        if not values["sku"] or len(values["sku"]) > 60 or not all(c.isalnum() or c in "-_" for c in values["sku"]):
            raise InventoryError("La referencia admite hasta 60 letras, números, guiones o guiones bajos.")
        for field, limit in (("name", 200), ("brand", 80), ("category", 80)):
            if not values[field] or len(values[field]) > limit:
                raise InventoryError(f"Completa {field} (máximo {limit} caracteres).")
        if len(values["notes"]) > 3000 or len(values["compatibility"]) > 1500:
            raise InventoryError("Acorta las notas o la lista de compatibilidad.")
        values.update(price_cents=integer(item["price_cents"], "Precio", maximum=999999999),
            low_stock=integer(item.get("low_stock", 5), "Alerta de existencias"), active=bool(item.get("active", True)))
        if image is not None:
            values["image_data"] = clean_image(image)
        try:
            with self.engine.begin() as conn:
                if expected_version is None:
                    stock = integer(item.get("stock", 0), "Existencias")
                    conn.execute(insert(products).values(**values, stock=stock, image_path="", version=1))
                    self._movement(conn, values["sku"], stock, stock, "initial", "Alta de artículo")
                else:
                    changed = conn.execute(update(products).where(products.c.sku == values["sku"],
                        products.c.version == expected_version).values(**values, version=products.c.version + 1))
                    if changed.rowcount != 1:
                        raise InventoryError("Este artículo cambió. Actualiza la página y vuelve a guardar.")
        except IntegrityError:
            raise InventoryError("Esa referencia ya existe. Usa una referencia diferente.") from None

    def adjust_stock(self, sku, delta, reason, request_key):
        integer(delta, "Cantidad", minimum=-10000000)
        reason = reason.strip()
        if delta == 0 or not reason or len(reason) > 1000 or not request_key:
            raise InventoryError("Indica una cantidad distinta de cero y un motivo (máximo 1000 caracteres).")
        try:
            with self.engine.begin() as conn:
                if conn.execute(select(movements.c.id).where(movements.c.request_key == request_key)).first():
                    return
                result = conn.execute(update(products).where(products.c.sku == sku,
                    products.c.stock + delta >= 0, products.c.stock + delta <= 10000000)
                    .values(stock=products.c.stock + delta, version=products.c.version + 1))
                if result.rowcount != 1:
                    raise InventoryError("El ajuste dejaría existencias negativas o excedería el máximo permitido.")
                stock = conn.execute(select(products.c.stock).where(products.c.sku == sku)).scalar_one()
                self._movement(conn, sku, delta, stock, "adjustment", reason, request_key=request_key)
        except IntegrityError:
            with self.engine.connect() as conn:
                if conn.execute(select(movements.c.id).where(movements.c.request_key == request_key)).first():
                    return
            raise

    def confirm_sale(self, cart, customer, payment, notes, request_key):
        """Conditional UPDATE serializes competing buyers; the whole cart commits or rolls back."""
        if not cart or not request_key or len(request_key) > 80:
            raise InventoryError("Agrega al menos un artículo a la venta.")
        if payment not in ("Efectivo", "Transferencia", "Tarjeta", "Otro"):
            raise InventoryError("Selecciona un medio de pago válido.")
        customer = customer.strip() or "Cliente general"
        if len(customer) > 200 or len(notes) > 3000:
            raise InventoryError("Acorta el nombre del cliente o las notas.")
        sale_id = str(uuid4())
        try:
            with self.engine.begin() as conn:
                old = conn.execute(select(sales.c.id).where(sales.c.request_key == request_key)).scalar_one_or_none()
                if old:
                    return old
                conn.execute(insert(sales).values(id=sale_id, request_key=request_key, created_at=now(),
                    customer=customer, payment=payment, notes=notes.strip(), total_cents=0, status="confirmed"))
                total = 0
                for sku in sorted(cart):  # stable lock order avoids deadlocks across carts
                    entry = cart[sku]
                    qty = integer(entry["quantity"], "Cantidad", minimum=1)
                    price = integer(entry["price_cents"], "Precio", maximum=999999999)
                    result = conn.execute(update(products).where(products.c.sku == sku,
                        products.c.active.is_(True), products.c.stock >= qty, products.c.price_cents == price)
                        .values(stock=products.c.stock - qty, version=products.c.version + 1))
                    if result.rowcount != 1:
                        raise InventoryError(f"{sku}: cambió el precio, se archivó o no tiene suficientes unidades. Revisa el carrito.")
                    product = conn.execute(select(products).where(products.c.sku == sku)).mappings().one()
                    total += qty * price
                    if total > 2000000000:
                        raise InventoryError("El total excede el máximo permitido por venta.")
                    conn.execute(insert(sale_items).values(id=str(uuid4()), sale_id=sale_id, sku=sku,
                        name=product["name"], quantity=qty, unit_price_cents=price))
                    self._movement(conn, sku, -qty, product["stock"], "sale", "Venta confirmada", sale_id)
                conn.execute(update(sales).where(sales.c.id == sale_id).values(total_cents=total))
            return sale_id
        except IntegrityError:
            with self.engine.connect() as conn:
                old = conn.execute(select(sales.c.id).where(sales.c.request_key == request_key)).scalar_one_or_none()
                if old:
                    return old
            raise

    def void_sale(self, sale_id, reason):
        if not reason.strip() or len(reason) > 1000:
            raise InventoryError("Escribe un motivo para anular (máximo 1000 caracteres).")
        with self.engine.begin() as conn:
            result = conn.execute(update(sales).where(sales.c.id == sale_id, sales.c.status == "confirmed")
                .values(status="voided", void_reason=reason.strip(), voided_at=now()))
            if result.rowcount != 1:
                existing = conn.execute(select(sales.c.status).where(sales.c.id == sale_id)).scalar_one_or_none()
                if existing == "voided":
                    return False
                raise InventoryError("No se encontró esa venta.")
            items = conn.execute(select(sale_items).where(sale_items.c.sale_id == sale_id)
                                 .order_by(sale_items.c.sku)).mappings().all()
            for item in items:
                conn.execute(update(products).where(products.c.sku == item["sku"])
                    .values(stock=products.c.stock + item["quantity"], version=products.c.version + 1))
                balance = conn.execute(select(products.c.stock).where(products.c.sku == item["sku"])).scalar_one()
                self._movement(conn, item["sku"], item["quantity"], balance, "void", reason.strip(), sale_id)
        return True

    def list_sales(self):
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(select(sales).order_by(sales.c.created_at.desc())).mappings()]

    def get_sale(self, sale_id):
        with self.engine.connect() as conn:
            row = conn.execute(select(sales).where(sales.c.id == sale_id)).mappings().one()
            result = dict(row)
            result["items"] = [dict(r) for r in conn.execute(select(sale_items).where(sale_items.c.sale_id == sale_id)
                                                            .order_by(sale_items.c.sku)).mappings()]
            return result

    def list_movements(self, sku=None):
        query = select(movements).order_by(movements.c.created_at.desc())
        if sku:
            query = query.where(movements.c.sku == sku)
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(query).mappings()]

    def backup(self):
        # Read a consistent database snapshot, including embedded uploaded images.
        with self.engine.connect() as conn:
            if self.engine.dialect.name == "postgresql":
                conn = conn.execution_options(isolation_level="REPEATABLE READ")
            with conn.begin():
                if self.engine.dialect.name == "sqlite":
                    conn.exec_driver_sql("BEGIN")
                out = {"schema_version": 1, "created_at": now(), "tables": {}}
                for table in (products, sales, sale_items, movements, settings):
                    rows = [dict(r) for r in conn.execute(select(table)).mappings()]
                    for row in rows:
                        for key, value in row.items():
                            if isinstance(value, bytes):
                                row[key] = {"base64": base64.b64encode(value).decode()}
                    out["tables"][table.name] = rows
        return json.dumps(out, ensure_ascii=False, indent=2)

    def restore_into_empty(self, raw):
        """Restores an exported backup into a NEW database only, never overwrites sales."""
        content = json.loads(raw)
        if content.get("schema_version") != 1:
            raise InventoryError("Versión de respaldo no compatible.")
        with self.engine.begin() as conn:
            for table in (products, sales, sale_items, movements, settings):
                if conn.execute(select(table).limit(1)).first():
                    raise InventoryError("La restauración necesita una base nueva y vacía.")
            for table in (products, sales, sale_items, movements, settings):
                rows = content["tables"][table.name]
                for row in rows:
                    for key, value in row.items():
                        if isinstance(value, dict) and "base64" in value:
                            row[key] = base64.b64decode(value["base64"], validate=True)
                if rows:
                    conn.execute(insert(table), rows)
