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
- Buscar nombres completos aunque el catálogo use abreviaturas: «iPhone 17 Pro Max» encuentra «iPhone 17PM». El catálogo y el inventario muestran hasta 30 artículos sin paginar; a partir de 31 usan botones para avanzar o retroceder.
- Agregar varios artículos a una venta, cambiar cantidades y confirmar el pago para descontarlos.
- Carrito con fotos, precio unitario, subtotales y total para el cliente. Al confirmar se genera y se intenta descargar un ticket PNG para compartir; también queda disponible en la última venta y en el historial. El ticket no incluye datos de empresa, cliente ni notas internas.
- Consultar ventas y descargar comprobantes internos en HTML, imprimibles desde el navegador.
- Anular una venta completa y devolver sus unidades al inventario una sola vez.
- Crear productos de cualquier categoría, añadir fotos, editar precios y archivar referencias.
- Administrar existencias desde tarjetas con foto y accesos directos a editar o reponer. Al crear o editar, previsualiza la foto principal y añade hasta ocho fotos reales (5 MB por foto); puedes quitar fotos seleccionadas antes de guardar. El carrito muestra un carrete de fotos reales, con zoom al pasar el mouse y desplazamiento horizontal en el celular.
- Registrar entradas o salidas justificadas y consultar su historial.
- Exportar inventario, ventas y movimientos en CSV, y un respaldo completo en JSON.

## Pedidos públicos por WhatsApp

Comparte `https://importadora-myrr4sgdikyma8ew9bmgcm.streamlit.app/?vista=pedidos` después de actualizar la app. Con `PUBLIC_CATALOG = true`, el cliente ve un catálogo independiente, sin menú administrativo. Puede agregar productos, revisar **Mi pedido** y tocar **Pedir por WhatsApp** sin indicar teléfono; el nombre es opcional. Se guarda la solicitud y se intenta abrir WhatsApp con el mensaje preparado para **+503 7311 3611**. Si el navegador bloquea la apertura, queda **Continuar en WhatsApp**. El cliente pulsa Enviar en WhatsApp; la app no envía mensajes automáticamente ni sabe si fueron enviados. No se muestran indicaciones de envío ni del tipo de tienda.

Para administrar, entra a `https://importadora-myrr4sgdikyma8ew9bmgcm.streamlit.app/?vista=admin` e inicia sesión. **Solicitudes** abre una bandeja de pedidos nuevos, con los más recientes primero. Las etiquetas **Nuevas**, **Contactadas**, **Con venta**, **Canceladas** y **Todas** muestran sus contadores. En computadora se presenta como tabla; en pantallas estrechas, como tarjetas con cliente, referencia, fecha, unidades, total y estado. Busca por nombre, número de solicitud o contacto, y toca **Abrir solicitud**. No hay que elegir pedidos en un combo. La bandeja pagina de doce en doce; dentro del detalle puedes ir a **Anterior**, **Siguiente** o **Volver a solicitudes**, conservando la búsqueda, estado y página.

En el detalle revisa fotos y disponibilidad, usa **Usar disponibles**, quita artículos con cantidad cero o agrega una alternativa. Guarda los ajustes y acuerda los cambios con el cliente. Busca el número de solicitud en el chat recibido; el número del cliente solo estará en WhatsApp, no se obtiene automáticamente desde el enlace. Puedes copiar el resumen actualizado para responder y marcarlo como contactado. Las solicitudes no reservan ni descuentan unidades.

Para cerrar, confirma que el cliente aceptó y que recibiste el pago. La venta verifica nuevamente stock y precios, descuenta unidades y genera el ticket PNG en una sola confirmación. Si otra sesión ya confirmó o cambió el pedido, no se duplica la venta. Una solicitud cancelada no puede convertirse en venta; una venta ya registrada se anula desde **Ventas**, manteniendo el historial.

El pedido original y la última revisión se conservan en la base y los respaldos (versión 3, compatible al restaurar respaldos anteriores). Solo el administrador ve la bandeja; el cliente solo ve el pedido registrado en su propia sesión. El carrito sin registrar no sobrevive necesariamente a un cierre o reinicio. Se admiten hasta 20 referencias por pedido y cinco solicitudes por sesión en diez minutos; este límite no sustituye protección avanzada contra abuso.

## Publicación

Sigue **[la guía para publicar en internet](docs/PUBLICAR_EN_INTERNET.md)**. La combinación preparada es Streamlit Community Cloud para ejecutar la app y PostgreSQL en Neon para conservar tus datos.

**App publicada:** https://importadora-myrr4sgdikyma8ew9bmgcm.streamlit.app/. Para actualizarla, sube los cambios a la rama conectada en Streamlit; consulta «Actualizar la app ya publicada (redeploy)» en la guía. No subas contraseñas o conexiones privadas al repositorio.

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
| `order_views.py` | Carrito público, enlace a WhatsApp y revisión privada de solicitudes |
| `ticket.py` | Ticket PNG para el cliente a partir de la venta confirmada |
| `data/catalog_seed.json` | Catálogo inicial auditado con huella del PDF |
| `assets/products/` | 24 imágenes originales, una por referencia |
| `styles.css` | Apariencia y adaptación de pantalla |
| `.streamlit/secrets.toml.example` | Configuración de ejemplo para publicar |
| `scripts/` | Importación, contraseñas y recuperación de respaldo |
| `tests/` | Pruebas de inventario y formularios |

## Detalles de operación

Para ajustar una fotografía: **Inventario → Editar artículo → Encuadre de la foto en las tarjetas**. Ajusta zoom (100–200 %) y centro horizontal/vertical, revisa la vista previa y pulsa **Guardar cambios**. El encuadre se conserva por producto en catálogo, inventario y carrito, sin modificar la imagen original. El zoom inicial es 115 %; al pasar el mouse o enfocar la imagen con el teclado se amplía más.

Los precios se guardan en centavos enteros. Una venta se registra junto con sus movimientos en una sola transacción: si cualquier artículo no tiene stock, se rechaza la venta completa. Una clave única evita descontar dos veces la misma confirmación. Las fotos nuevas se guardan en la base, para que no dependan del disco temporal del servidor.

El acceso de administrador dura hasta 12 horas; cerrarlo borra el carrito de esa sesión. El carrito aún no confirmado vive en la sesión del navegador y no reserva unidades. Las ventas confirmadas permanecen en la base. El catálogo vuelve a consultar existencias cada 30 segundos; al confirmar siempre comprueba nuevamente stock y precios.

Esta primera versión utiliza una sola cuenta de administrador. No incluye cobros en línea, crédito a clientes, devoluciones parciales ni facturación fiscal. Los medios de pago registran cómo cobraste; no procesan dinero. Puedes agregar categorías distintas a protectores sin cambiar el código.

## Cambiar la contraseña local

```powershell
python scripts/cambiar_clave_local.py
```

Para la nube, genera un hash con `python scripts/hash_password.py` y cambia `ADMIN_PASSWORD_HASH` en Secrets. La app invalida las sesiones con la contraseña anterior al interactuar.
