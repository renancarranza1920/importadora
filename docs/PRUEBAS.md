# Verificación de IMPORTADORA

Fecha de última verificación: 16 de septiembre de 2026.

## Bordes y encuadre de fotos

- 36 pruebas aprobadas. Nuevas comprobaciones del guardado y reapertura del encuadre, límites de zoom, conservación de existencias y restauración del encuadre desde respaldo.
- Chrome local a 1440 y 390 píxeles: formularios con bordes, campos de texto, cantidades, selector de pago y notas. Editor con vista previa; zoom guardado al 150 % y ampliación al pasar el mouse en carrito al 247,5 %.
- La preferencia por producto se guarda en `settings` dentro de la misma transacción de edición; no requiere cambiar las tablas existentes. Las imágenes originales se conservan.
- La lectura de la URL publicada no estuvo disponible; la comprobación se realizó sobre el proyecto local con una base temporal.

## Actualización del recurso de base de datos

- 34 pruebas aprobadas. La caché de conexión ahora incluye la huella de `inventory.py`, para reconstruir el recurso al actualizar su implementación.
- Prueba de regresión: actualización desde una base sin tabla de fotos, creación de la tabla nueva y conservación de existencias previamente ajustadas.
- Al publicar, subir juntos `app.py` e `inventory.py`. Si el servidor conserva una versión anterior del módulo, reiniciar la app desde Streamlit.

## Inventario visual y fotos reales

- 33 pruebas automatizadas aprobadas. Cobertura nueva: persistencia de varias fotos, sustitución y eliminación, validación de imágenes, guardado atómico ante errores y versiones desactualizadas, respaldo/restauración y compatibilidad con respaldos anteriores.
- Chrome con base temporal: acceso desde tarjeta a edición, subida múltiple con vista previa, guardado, carrete en carrito, zoom al pasar el mouse y ancho del carrete a 1440 y 390 píxeles.
- La tabla adicional `product_photos` se crea al iniciar la app; no altera las existencias. Los nuevos respaldos usan versión 2; se siguen admitiendo respaldos de versión 1.

## Carrito visual y ticket para el cliente

- 30 pruebas automatizadas: confirmación, descarga disponible, PNG válido, nombres largos y omisión de notas y datos privados en el ticket.
- Chrome: fotos y tarjetas dentro de pantalla a 1440 y 390 píxeles; venta en SQLite temporal y descarga automática de un archivo PNG confirmadas.
- El ticket se genera desde los importes históricos de la venta y se puede descargar nuevamente en Ventas. Las ventas anuladas generan una imagen marcada como anulada.
- La descarga automática depende de las políticas del navegador; queda un botón de descarga manual. No se realizaron ventas en la app publicada.

## Corrección de iconos y vistas

- **29 pruebas automatizadas aprobadas** con Python 3.12, Streamlit 1.63.0 y SQLAlchemy 2.0.52 (`.venv/Scripts/python -m pytest tests -q`).
- Chrome sin ventana: catálogo a 1440, 768 y 390 píxeles; fuentes nativas de iconos conservadas, 12 tarjetas dentro del ancho visible sin superponerse y apertura de «Ver detalles» correcta. En móvil las tarjetas aprovechan el ancho disponible.
- Nuevas pruebas: reinicio de paginación al ordenar, búsqueda sin resultados, limpieza de filtros y búsqueda sin tildes.
- Se mantienen las pruebas de acceso, ventas, cantidades, anulaciones, ajustes, edición concurrente y respaldo.
- La primera ejecución excedió el tiempo de arranque de una prueba; la segunda ejecución completa terminó con 29 aprobadas en 11,96 segundos.
- Se utilizaron bases SQLite temporales. No se probaron escrituras contra PostgreSQL ni contra la app publicada; estos cambios quedan pendientes de subir a GitHub.

## Verificación anterior (13 de septiembre)

**27 pruebas automatizadas aprobadas**, con Python 3.14, Streamlit 1.63.0 y SQLAlchemy 2.0.49. El servidor local devuelve HTTP 200 y su comprobación de salud responde `ok`.

Las pruebas usan bases SQLite temporales. La base entregada conserva **24 referencias, 360 unidades y cero ventas**.

## Cobertura

- Conciliación de todas las referencias, fotografías, cantidades y valor con el catálogo inicial.
- Conservación de compatibilidades, incluidos A16/A17/A26 y los nombres iPhone del PDF.
- Venta con precio histórico, descuento exacto y movimiento con saldo.
- Reinicio e importación repetida sin reponer artificialmente el inventario.
- Doble solicitud y solicitudes simultáneas de la misma venta sin duplicación.
- Dos ventas concurrentes que compiten por el stock: solo se acepta la que tiene unidades.
- Carrito de varios artículos: reversión completa si uno no tiene disponibilidad.
- Rechazo de cantidades negativas, cero, decimales y tipos inválidos.
- Rechazo de precios desactualizados y artículos archivados.
- Anulaciones repetidas y concurrentes sin reponer dos veces.
- Ajustes justificados, repetidos sin duplicación y sin existencias negativas.
- Edición que detecta cambios de otra sesión.
- Creación de artículos de otra categoría y persistencia de fotos subidas.
- Respaldo y restauración en base vacía, con imágenes y ventas conservadas.
- Hash de contraseña y rechazo del acceso incorrecto.
- Modo de producción bloqueado cuando falta acceso o se intenta usar SQLite temporal.
- Formularios reales de Streamlit: búsqueda pública, acceso, carrito, confirmación, alta, reposición, anulación, navegación y salida.

## Pendiente al publicar

No hubo navegador conectado disponible en este entorno. Por ello, **la revisión visual en un celular real sigue pendiente**; no se afirma que se haya hecho. La app incluye estilos adaptables y las pantallas fueron verificadas mediante Streamlit AppTest.

También faltan la conexión real a Neon y la prueba de despliegue en Streamlit con tus cuentas. La guía incluye un recorrido de venta y anulación para verificar el inventario desde dos dispositivos y después de reiniciar la nube.

## Repetir pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
```

El PDF se revisó visualmente y se extrajo por la posición de cada tarjeta. Se usó el último nombre dibujado en cada tarjeta para respetar las compatibilidades que fueron añadidas sobre los títulos anteriores. Los precios se extrajeron como centavos enteros, sin estimarlos por la foto.
