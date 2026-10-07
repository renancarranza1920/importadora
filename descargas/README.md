# Descargas de IMPORTADORA

Los paquetes están en GitHub. Abre un ZIP y pulsa **Download raw file**, o usa estos enlaces:

La prueba piloto de **mariposas crema y negro** usa una sola imagen con los dos colores y cuatro referencias: crema A13-02 (20) y A15-02 (20); negro A13-01 (26) y A15-01 (25). A13 5G / A04S comparte la cantidad de su referencia; A15 tiene existencias separadas. Precio $2 por unidad y mínimo 3 unidades mixtas. Datos al 07/10/2026.

- [Descargar imagen de mariposas](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/mariposas-crema-negro.png)
- [Descargar campaña unificada: imagen, datos y texto](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/campana-mariposas-unificada.zip)

Esta pieza reúne fotografías representativas del diseño; el ajuste corresponde a cada modelo. Para el piloto, seleccionar **imagen única**, destino WhatsApp y presupuesto **total de $2**, no diario. Las cantidades son estáticas y deben actualizarse si cambia el inventario.

| Paquete | Contenido | Descargar |
| --- | --- | --- |
| Campaña de mayor stock | 10 imágenes: A06-03 (45), A13-01 (26), A15-01 (25), A13-02 (20), A15-02 (20); textos incluidos | [ZIP prioritario](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/campana-stock-prioritario.zip) |
| Primera campaña A06, A13 y A15 | 6 imágenes: A06-03, A13-01 y A15-01; 96 unidades entre esas referencias | [ZIP inicial](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/primera-campana-A06-A13-A15.zip) |
| Todos los anuncios | 48 imágenes de las 24 referencias, Samsung e iPhone; 270 unidades; HTML editable, galería, fotografías, lista de referencias y CSV de textos/enlaces | [ZIP de anuncios](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/meta-ads-importadora.zip) |
| Solo iPhone | 12 imágenes de 6 referencias; textos y fotografías incluidos | [ZIP de iPhone](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/anuncios-iphone.zip) |
| Proyecto web | Código, originales, fotografías mejoradas, consulta de existencias, pruebas y documentación; sin bases, contraseñas ni secretos | [ZIP del proyecto](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/importadora-publicar.zip) |

Cada imagen muestra **QUEDAN N UNIDADES** y **Stock al 07/10/2026**, según la consulta de Oracle compartida por el propietario. Las cantidades se comparten entre los modelos compatibles de cada referencia. Estos anuncios son archivos estáticos: hay que actualizarlos cuando cambien las existencias. `PRIORIDAD-STOCK.csv` ordena las referencias de mayor a menor stock.

**48 imágenes son 24 referencias/diseños en dos formatos.** Samsung: 18 referencias, 36 imágenes. iPhone: 6 referencias, 12 imágenes. Los JPG se exportan con calidad 95 %, publicación 1080×1350 e historia 1080×1920. Las fotografías mejoradas están incluidas una sola vez por referencia; los documentos HTML las usan sin duplicar archivos.

Las fotos se optimizaron digitalmente a partir de fuentes pequeñas. La mejora no recupera con certeza detalles originalmente ilegibles; los originales siguen en `assets/products/`. Los nombres, compatibilidades, precios y cantidades proceden juntos de la consulta actual de Oracle. Se conservan variantes como 5G, paréntesis y todos los modelos separados con `/`, tanto en las imágenes como en JSON y CSV. IP17PM-01, IP17PM-02 e IP17PM-03 conservan la etiqueta 17 Pro Max / 18 Pro Max indicada por el proveedor y la nota de ajuste físico pendiente visible.

Cada imagen indica **MÍNIMO 3 UNIDADES MIXTAS** y **Puedes combinar modelos y diseños**. El pie dice **Confirma disponibilidad**. Envío económico a puntos específicos según el total de compra; personalizado a domicilio por $5, ambos a todo el país.

Los iPhone base se anuncian como **iPhone 13 normal / iPhone 14 normal** y **iPhone X normal**. Los Pro Max se identifican como Pro Max. Los campos originales del sistema se conservan separados de los nombres públicos de los anuncios.

Para descargar los cambios en Oracle:

```bash
cd ~/importadora
git switch main
git pull --ff-only origin main
```

Esta entrega actualiza anuncios y herramientas; no cambia el código de la web y no requiere reiniciar contenedores. Cuando recibas cambios de interfaz, aplícalos con `bash scripts/actualizar_oracle.sh importadora` después de descargar `main`.

`SHA256SUMS` comprueba la integridad de los ZIP y de la imagen unificada. Esta carpeta y las fotografías de campaña se excluyen del contexto Docker.
