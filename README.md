# IMPORTADORA

App web de catálogo mayorista, inventario y ventas, en español y con precios en USD.

El catálogo suministrado ya está importado: **24 referencias, 360 unidades y $902.50 de valor inicial a precio de venta**. Los nombres con varios modelos representan un único artículo compatible, con existencias compartidas. Las imágenes son las originales extraídas del PDF.

## Abrir en esta computadora

1. Haz doble clic en **INICIAR_APP.bat**.
2. Abre **http://localhost:8501**.
3. Consulta **ACCESO_LOCAL.txt** para tu contraseña. En el menú entra a **Acceso administrador**.

La base local está en `data/inventory.db`. Reiniciar la app no vuelve a cargar las cantidades iniciales. Mantén abierta la terminal mientras uses esta copia. El archivo `.bat` instala las dependencias si hace falta; requiere Python 3.12 o superior y conexión a internet durante la primera instalación.

## Qué puedes hacer

- Mostrar un catálogo con fotografías, precios, disponibilidad y búsqueda por modelo compatible, marca o referencia.
- Agregar varios artículos a una venta, cambiar cantidades y confirmar el pago para descontarlos.
- Consultar ventas y descargar comprobantes internos en HTML, imprimibles desde el navegador.
- Anular una venta completa y devolver sus unidades al inventario una sola vez.
- Crear productos de cualquier categoría, añadir fotos, editar precios y archivar referencias.
- Registrar entradas o salidas justificadas y consultar su historial.
- Exportar inventario, ventas y movimientos en CSV, y un respaldo completo en JSON.

## Publicar gratis y abrir desde tu celular

Sigue **[la guía para publicar en internet](docs/PUBLICAR_EN_INTERNET.md)**. La combinación preparada es Streamlit Community Cloud para ejecutar la app y PostgreSQL en Neon para conservar tus datos.

**Estado de entrega: funciona en esta computadora. Todavía no hay una dirección pública.** Crear o conectar tus cuentas de GitHub, Neon y Streamlit es el paso pendiente para publicarla. No compartas contraseñas o conexiones privadas en el chat ni las subas al repositorio.

`localhost` solo funciona en esta computadora. Cuando publiques en Streamlit usarás una dirección HTTPS desde el celular con Wi-Fi o datos móviles; no necesitas mantener encendida esta computadora.

## Verificación

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

Las pruebas crean bases temporales; no modifican el inventario real. Ver [PRUEBAS.md](docs/PRUEBAS.md) para los resultados y el recorrido de comprobación.

## Estructura

| Archivo | Uso |
| --- | --- |
| `app.py` | Pantallas y formularios de Streamlit |
| `inventory.py` | Base de datos y transacciones de ventas |
| `auth.py` | Autenticación y límite de intentos |
| `data/catalog_seed.json` | Catálogo inicial auditado con huella del PDF |
| `assets/products/` | 24 imágenes originales, una por referencia |
| `styles.css` | Apariencia y adaptación de pantalla |
| `.streamlit/secrets.toml.example` | Configuración de ejemplo para publicar |
| `scripts/` | Importación, contraseñas y recuperación de respaldo |
| `tests/` | Pruebas de inventario y formularios |

## Detalles de operación

Los precios se guardan en centavos enteros. Una venta se registra junto con sus movimientos en una sola transacción: si cualquier artículo no tiene stock, se rechaza la venta completa. Una clave única evita descontar dos veces la misma confirmación. Las fotos nuevas se guardan en la base, para que no dependan del disco temporal del servidor.

El acceso de administrador dura hasta 12 horas; cerrarlo borra el carrito de esa sesión. El carrito aún no confirmado vive en la sesión del navegador y no reserva unidades. Las ventas confirmadas permanecen en la base. El catálogo vuelve a consultar existencias cada 30 segundos; al confirmar siempre comprueba nuevamente stock y precios.

Esta primera versión utiliza una sola cuenta de administrador. No incluye cobros en línea, crédito a clientes, devoluciones parciales ni facturación fiscal. Los medios de pago registran cómo cobraste; no procesan dinero. Puedes agregar categorías distintas a protectores sin cambiar el código.

## Cambiar la contraseña local

```powershell
python scripts/cambiar_clave_local.py
```

Para la nube, genera un hash con `python scripts/hash_password.py` y cambia `ADMIN_PASSWORD_HASH` en Secrets. La app invalida las sesiones con la contraseña anterior al interactuar.
