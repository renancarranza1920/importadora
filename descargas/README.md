# Descargas de IMPORTADORA

Los paquetes están guardados en este repositorio para descargarlos desde GitHub. Abre el archivo y pulsa **Download raw file**, o usa los enlaces siguientes.

| Paquete | Contenido | Descargar |
| --- | --- | --- |
| Primera campaña A06, A13 y A15 | 6 PNG: tres diseños en publicación e historia; textos y pasos de la prueba | [ZIP inicial](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/primera-campana-A06-A13-A15.zip) |
| Todos los anuncios | 48 PNG de las 24 referencias: carpetas Samsung e iPhone, documentos HTML, galería y CSV de textos/enlaces | [ZIP de anuncios](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/meta-ads-importadora.zip) |
| Solo iPhone | 12 PNG de 6 referencias: iPhone 13/14, X y 17 Pro Max/18 Pro Max según proveedor; textos incluidos | [ZIP de iPhone](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/anuncios-iphone.zip) |
| Proyecto web | Código, fotografías originales, pruebas y documentación; sin bases, contraseñas ni secretos | [ZIP del proyecto](https://github.com/renancarranza1920/importadora/raw/refs/heads/main/descargas/importadora-publicar.zip) |

Precios y cantidades de las piezas provienen del catálogo inicial: confirma precio, existencias y compatibilidad en tu tienda antes de invertir. Las 24 referencias están incluidas. IP17PM-01, IP17PM-02 e IP17PM-03 se entregan como borradores con la etiqueta conjunta 17 Pro Max / 18 Pro Max indicada por el proveedor y una nota visible de ajuste físico pendiente.

**48 imágenes no significa 48 modelos de teléfono.** Son 24 referencias/diseños, cada uno en publicación e historia. Samsung tiene 18 referencias (36 imágenes); iPhone tiene 6 (12 imágenes). `REFERENCIAS.csv` en el ZIP permite comprobar cada referencia y sus dos archivos. Las compatibilidades compartidas se indican en la misma pieza.

Los formatos son publicación 1080×1350 e historia 1080×1920. Los textos indican mínimo de tres unidades combinadas y envíos a todo el país: económico a puntos específicos según el total de compra y personalizado a domicilio por $5.

Para actualizar la tienda en Oracle usa Git y el script, sin descargar un ZIP:

```bash
cd ~/importadora
git switch main
git pull --ff-only origin main
bash scripts/actualizar_oracle.sh importadora
```

`SHA256SUMS` permite comprobar la integridad de los cuatro paquetes. Los archivos de esta carpeta no se copian a la imagen Docker de la aplicación.
