# Fotografías mejoradas para anuncios

24 archivos, uno por referencia. Las 24 fotos del proveedor siguen intactas en `assets/products/` y continúan siendo las que usa la tienda. A13-01/A15-01 y A13-02/A15-02 comparten fotografías originales idénticas; las mejoras se reutilizan también en esos pares.

Se optimizaron digitalmente mediante `image_gen`, usando los originales como referencia y procurando conservar colores, motivos, encuadre y geometría. Las fuentes miden entre 124 y 400 píxeles por lado. La mejora aumenta la nitidez visual, pero puede interpretar letras, texturas y detalles diminutos que no se distinguen en el original; no equivale a recuperar una fotografía original en HD ni comprueba compatibilidad física. Para detalles exactos, usar fotografías de alta resolución del proveedor o fotografías propias del inventario.

`MANIFIESTO.json` identifica cada original, versión mejorada, dimensiones y hashes. El generador de anuncios prefiere estas versiones; `--original-photos` conserva la alternativa de usar las fuentes del proveedor. Ningún script sustituye fotos almacenadas en la base de producción.
