# Auditoría de calidad — 16 de septiembre de 2026

Revisión del código, reglas de inventario y recorridos de clientes y administración. Los cambios se realizaron sobre el proyecto local. Las pruebas utilizan bases temporales; no modifican la tienda publicada.

## Cambios realizados

1. **Precios del carrito:** agregar otra unidad conserva el precio pendiente de revisión. Si el precio cambió, la venta exige aceptarlo explícitamente antes de confirmar.
2. **Contingencias de existencias:** el carrito de venta incorpora «Actualizar disponibilidad» y «Usar disponibles» cuando faltan unidades. Se mantiene la validación transaccional al confirmar.
3. **Navegación del carrito:** accesos directos para seguir agregando productos y volver al catálogo desde un carrito vacío, tanto en venta como en pedido público.
4. **Formularios:** alta de productos y ajustes conservan los datos tras una validación fallida. Se limpian después de guardar correctamente. Cambiar de referencia reinicia el formulario de ajuste, incluida su confirmación.
5. **Validación de fotos:** límites visibles y efectivos de 5 MB por archivo y ocho fotos reales. Una imagen dañada o demasiadas fotos muestran el motivo y bloquean el guardado sin ocultar el formulario. Contador de fotos y vista previa de archivos válidos.
6. **Calidad de las imágenes:** transparencias sobre fondo blanco; fotos existentes sin recompresión al modificar el carrete. Las nuevas se normalizan desde el archivo original. Se conserva el color de las imágenes al quitar la mezcla de color del CSS.
7. **Fotos accesibles:** indicador «Sin foto disponible», descripciones del carrete, foco visible y carga/decodificación diferida en tarjetas y carretes. Esta mejora no elimina del tráfico los bytes de las imágenes embebidas.
8. **Búsqueda en inventario:** reconoce palabras sin tildes, marca y categoría; botón para limpiar filtros y retorno a la primera página al cambiar la búsqueda.
9. **Pedido público:** quitar productos actualiza inmediatamente el contador y la vista vacía. El pedido anterior queda en un bloque separado y cerrado al preparar otro, con su enlace a WhatsApp conservado.
10. **Revisión de solicitudes:** botón de guardado deshabilitado si no hay cambios; nombre del cliente mostrado como texto y sin separador sobrante cuando no tiene teléfono. El total presenta unidades, referencias e importe con el mismo diseño del carrito de venta.
11. **Importes y validaciones:** el límite de total de venta se aplica también a solicitudes nuevas y editadas; las pantallas bloquean la confirmación de totales fuera del límite. Los precios de solicitudes se validan como centavos enteros. Mensajes de campos obligatorios en español.
12. **Anulaciones:** una devolución no puede superar el límite de existencias. Si un producto excede el máximo, se revierte toda la operación, conservando la venta y los demás saldos.
13. **Historial de movimientos:** orden de saldos por referencia conservado aunque el reloj repita un instante o retroceda. No se modifica el historial anterior.
14. **Diseño global:** bordes uniformes, mayor contraste y tamaño de referencias/etiquetas, estados de agotado y archivado diferenciados, números alineados, totales adaptables y navegación pública con selección más visible.
15. **Interacciones:** transiciones cortas en botones, bordes y sombras de tarjetas; zoom suave de 400 ms con solo un 8 % adicional, conservando el encuadre configurable. La preferencia de reducir movimiento desactiva las animaciones y transiciones.
16. **Móvil y teclado:** controles principales de al menos 44 px, foco visible, campos de texto a 16 px en móvil, carrete con desplazamiento horizontal contenido y notificaciones que caben en pantallas pequeñas. La navegación pública sigue desplazándose con la página.
17. **Verificación:** trece regresiones automatizadas nuevas, revisión visual en navegador, comprobación de dependencias y paquete de publicación actualizado con documentación y pruebas.
18. **Compatibilidad con Streamlit:** apertura de WhatsApp y descarga automática mediante `st.iframe`, sustituyendo la API obsoleta; inicialización de cantidades sin asignar valores predeterminados duplicados a los widgets.
19. **Catálogo público más compacto:** filtros avanzados en un panel desplegable para llegar antes a las fotos desde el celular. La búsqueda permanece visible y ofrece restablecerla cuando no hay resultados. La limpieza asigna valores explícitos para restablecer también los campos del navegador durante una actualización parcial.
20. **Ticket con tildes:** fuente Noto Sans incluida en `assets/fonts/`, con su licencia, para dibujar correctamente tildes, diéresis y eñes en el PNG. El paquete verifica que incluya la fuente.

## Verificación automatizada

`python -m pytest tests -q`: **61 pruebas aprobadas**. `python -m pip check`: dependencias compatibles.

Se comprueban formularios reales de Streamlit; acceso y cierre de sesión; precios y cantidades; dos ventas simultáneas sin sobreventa; reintentos sin duplicados; devoluciones; edición concurrente; fotos; tickets; pedidos y conversión; respaldo/restauración; compatibilidad al actualizar módulos.

Las doce pruebas nuevas en `tests/test_quality.py` cubren los fallos corregidos: precio al agregar otra unidad, ajuste visual del carrito, datos conservados tras errores, reinicio seguro de ajustes, búsqueda y paginación, eliminación pública, pedido anterior separado, devolución que excede existencias, reloj repetido, total de solicitudes, transparencias y conservación de fotos existentes. Una regresión adicional en `tests/test_ticket.py` comprueba los glifos españoles del ticket.

## Verificación visual

Chrome local en ventanas de **320, 390, 768 y 1440 píxeles**: catálogo, pedido, tarjetas, navegación sin superposición, avisos dentro de pantalla, carrito de venta y bordes de formularios. Zoom comprobado en estado inicial, intermedio y final; preferencia de movimiento reducido comprobada.

Recorridos: pedido sin teléfono con destino WhatsApp interceptado; alta con fotos inválidas y exceso de archivos, corrección y guardado; conservación de campos al cambiar zoom/subir fotos; confirmación de pago, descarga PNG y apertura de las secciones administrativas. No se envían mensajes reales.

## Límites y publicación

- La URL publicada no pudo abrirse con la herramienta de consulta. La evidencia corresponde a la versión local modificada.
- Las transacciones se probaron en SQLite temporal. Queda verificar el despliegue con PostgreSQL y el comportamiento de WhatsApp/descargas en un teléfono físico, especialmente Safari/iOS.
- Esta revisión no incluye una prueba de carga ni una auditoría externa de seguridad. La limitación de solicitudes por sesión que ya existía no sustituye una protección contra tráfico automatizado masivo.
- El navegador puede bloquear la apertura o descarga automática. Se conservan los botones manuales de WhatsApp y ticket.
- Subir juntos los archivos del paquete `output/importadora-publicar.zip`, manteniendo sus carpetas. El ZIP excluye bases locales y secretos. Consultar `docs/PUBLICAR_EN_INTERNET.md` para actualizar y reiniciar Streamlit.

Después de publicar, comprobar con una solicitud de prueba: catálogo → pedido → WhatsApp → revisión administrativa. Verificar también la edición de fotos y una venta/anulación controlada con ticket.
