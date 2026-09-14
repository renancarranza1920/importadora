# Verificación de IMPORTADORA

Fecha: 13 de septiembre de 2026.

## Resultado realizado

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
