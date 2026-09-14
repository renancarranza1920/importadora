# De esta computadora a tu celular: publicación gratuita

La app está creada y funciona localmente. Para tener una dirección pública necesitas conectar tres servicios a tus propias cuentas. Esta guía permite hacerlo sin alquilar un servidor ni comprar un dominio.

## Qué hace cada servicio

| Servicio | Para qué sirve | Plan para comenzar |
| --- | --- | --- |
| GitHub | Guarda el código y las 24 fotografías iniciales | Free, repositorio privado |
| Streamlit Community Cloud | Ejecuta la app y te da una dirección HTTPS | Gratuito |
| Neon | Guarda productos, ventas, cantidades y fotos nuevas en PostgreSQL | Free, con límites de uso |

La computadora puede estar apagada una vez publicada. La app del celular consulta la base de datos en internet, así que todos los dispositivos ven el mismo inventario.

Streamlit declara que Community Cloud es gratuito. Neon publica un plan Free sin tarjeta con 0.5 GB por proyecto y límites de cómputo; comprueba las cuotas que muestre tu cuenta antes de elegir el plan. Consulta [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) y [los planes vigentes de Neon](https://neon.com/pricing). No hace falta contratar un plan de pago para comenzar con este catálogo.

## 1. Crear tus cuentas

Abre [GitHub](https://github.com/), [Neon](https://console.neon.tech/) y [Streamlit Community Cloud](https://share.streamlit.io/). Puedes usar GitHub para acceder a Neon y Streamlit. Completa tú las verificaciones de correo y la creación de tus contraseñas. Guarda tus accesos en tu gestor de contraseñas.

## 2. Subir el proyecto a GitHub

La opción sencilla es instalar [GitHub Desktop desde su página oficial](https://desktop.github.com/download/), iniciar sesión y agregar esta carpeta como repositorio local. Al publicar, marca **Keep this code private**.

También puedes subir los archivos desde la web de GitHub a un repositorio privado llamado `importadora`. La estructura debe conservarse: `app.py` debe estar en la raíz del repositorio, y las imágenes dentro de `assets/products/`.

Incluye estos archivos y carpetas:

- `app.py`, `inventory.py`, `auth.py`, `styles.css` y `requirements.txt`.
- `data/catalog_seed.json` y toda la carpeta `assets/`.
- `.streamlit/config.toml` y `.streamlit/secrets.toml.example`.
- `.gitignore`, `README.md`, `docs/`, `scripts/`, `tests/`, `requirements-dev.txt` e `INICIAR_APP.bat`.

**No subas** `ACCESO_LOCAL.txt`, `data/admin_password.hash`, `data/inventory.db`, `.streamlit/secrets.toml`, respaldos, logs, ni la carpeta `tmp/`. `.gitignore` los excluye si utilizas Git, pero no controla los archivos que arrastres manualmente a la web.

En la entrega se incluye un ZIP de publicación que solo contiene archivos seguros para el repositorio. Descomprímelo y conserva las carpetas al subirlo. GitHub no ejecuta la app por sí mismo; Streamlit la leerá desde allí.

## 3. Crear la base de datos gratuita en Neon

1. En [Neon Console](https://console.neon.tech/), crea un proyecto llamado `importadora` con el plan **Free**.
2. Elige una región de Estados Unidos cercana a Centroamérica entre las disponibles.
3. Abre **Connect**. Selecciona PostgreSQL y copia la cadena de conexión. Si aparece la opción de conexión agrupada (*pooled*), puedes utilizarla.
4. Guarda esa cadena de forma privada. Contiene el usuario y la contraseña de tu base de datos. No la pegues en GitHub ni en un chat.

La cadena se parece a `postgresql://usuario:contraseña@servidor/base?sslmode=require`. Copia solo la URL, sin `psql`, sin comillas de consola y sin comandos adicionales. Conserva `sslmode=require` y cualquier otro parámetro que genere Neon.

La app creará sus tablas e importará el catálogo al conectarse por primera vez. No necesitas escribir SQL.

## 4. Elegir la contraseña de administrador

Abre PowerShell en la carpeta del proyecto y ejecuta:

```powershell
python scripts/hash_password.py
```

Escribe una contraseña de al menos 12 caracteres y repítela. No verás los caracteres mientras escribes. El programa produce una línea `ADMIN_PASSWORD_HASH = "..."`. Copia esa línea para el siguiente paso. Es un hash, no la contraseña original; para entrar a la app usarás la contraseña que elegiste.

## 5. Publicar en Streamlit

1. En [Streamlit Community Cloud](https://share.streamlit.io/), conecta tu GitHub y permite el acceso al repositorio privado que creaste.
2. Pulsa **Create app**, y selecciona la opción para desplegar una app existente.
3. Selecciona tu repositorio `importadora`, la rama `main` y el archivo principal **`app.py`**.
4. Elige un subdominio disponible; por ejemplo, uno que incluya el nombre que después elijas para tu importadora. La dirección terminará en `.streamlit.app`.
5. Abre **Advanced settings**. Selecciona Python **3.14** si está disponible; el proyecto se probó con esa versión. El código también está escrito para Python 3.12 o superior.
6. En **Secrets**, pega y completa:

```toml
APP_ENV = "production"
BUSINESS_NAME = "IMPORTADORA"
CURRENCY = "USD"
TIMEZONE = "America/El_Salvador"
PUBLIC_CATALOG = true
DATABASE_URL = "PEGA_AQUI_LA_URL_PRIVADA_DE_NEON"
ADMIN_PASSWORD_HASH = "PEGA_AQUI_EL_HASH_GENERADO"
```

Si copiaste la línea completa generada por el programa, reemplaza la línea entera de `ADMIN_PASSWORD_HASH`. No pongas la contraseña normal en lugar del hash.

7. Guarda y pulsa **Deploy**. Espera a que se instalen las dependencias.
8. Para compartir el catálogo sin exigir una cuenta de Streamlit a tus clientes, configura la visibilidad de la app como pública en Streamlit. El repositorio puede mantenerse privado. La app seguirá exigiendo tu contraseña para registrar ventas y administrar.

`PUBLIC_CATALOG = true` permite ver fotografías, precios, modelos y existencias sin tu contraseña de administrador. Si prefieres que todo requiera acceso, usa `PUBLIC_CATALOG = false`.

La documentación oficial muestra [cómo seleccionar el repositorio y configurar Secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) y [cómo guardar secretos sin subirlos al código](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

## 6. Probar desde el celular antes de salir a vender

1. Abre tu dirección `https://...streamlit.app` desde el celular usando datos móviles. Esto comprueba que accedes por internet, sin depender de esta computadora.
2. Revisa las fotos, busca **A26** y comprueba que aparecen las referencias compatibles A16/A17/A26. Busca **iPhone 14** y comprueba las referencias 13/14.
3. Entra en **Acceso administrador**. En pantalla pequeña, abre primero el menú lateral con el botón de la esquina superior izquierda.
4. Revisa el inventario inicial: **24 referencias, 360 unidades y $902.50 a precio de venta**. Si ya registraste movimientos reales, tus cantidades serán distintas.
5. Agrega una unidad de **A06-01** a una venta. Escribe `PRUEBA DE PUBLICACIÓN` como cliente, revisa el total de **$3.00** y confirma.
6. Comprueba que A06-01 bajó de **10 a 9**. En otro dispositivo, espera hasta 30 segundos o vuelve a abrir el catálogo y comprueba el mismo saldo.
7. En **Ventas**, abre esa venta y anúlala con el motivo `Fin de prueba; mercancía no entregada`, confirmando que la unidad regresa al inventario. Debe volver a **10**. La venta quedará anulada en el historial; no se sumará a las ventas confirmadas.
8. Reinicia la app desde Streamlit y verifica que la venta anulada y los movimientos siguen presentes. No uses una venta de un cliente real para esta prueba.
9. Descarga un respaldo en **Ayuda y respaldo**.

## 7. Usarla como acceso directo

En Android, abre el menú de Chrome y usa **Agregar a pantalla principal**. En iPhone, abre la app en Safari, toca **Compartir** y **Agregar a inicio**. Esto crea un acceso directo; necesitas internet para confirmar ventas.

Para tu jornada: catálogo → agregar artículos → nueva venta → revisar cantidad y pago → confirmar. Espera el mensaje de venta confirmada antes de entregar. Si se interrumpe la conexión después de confirmar, consulta **Ventas** antes de volver a registrar el pedido.

## Conservar y recuperar tus datos

Descarga un respaldo JSON al finalizar cada jornada. Incluye las tablas y las fotos que añadas después; las imágenes iniciales permanecen en el proyecto. Mantén también una copia del proyecto.

Para restaurar un respaldo en un archivo local nuevo:

```powershell
python scripts/restore_backup.py ruta\respaldo.json --local-output data\recuperado.db
```

Para recuperar en la nube, crea una base nueva en Neon, configura su URL en la variable de entorno privada `RESTORE_DATABASE_URL` y ejecuta `python scripts/restore_backup.py ruta\respaldo.json`. La herramienta exige que esté vacía. Después verifica los datos y cambia `DATABASE_URL` en Streamlit a la nueva base.

La app no reemplaza datos existentes al restaurar ni vuelve a importar las cantidades del catálogo en una base restaurada. No borres el proyecto de Neon: allí está el inventario real.

Si empiezas a vender en la copia local antes de publicar, restaura su respaldo en una base Neon nueva **antes del primer inicio de Streamlit**. Si primero arrancas la nube, se importará el catálogo inicial; la app no mezcla automáticamente las ventas locales y las de la nube.

## Qué esperar del plan gratuito

Los planes gratuitos tienen límites y pueden necesitar unos segundos para activarse tras estar inactivos. Neon suspende el cómputo tras inactividad para reducir uso; consulta [Scale to Zero](https://neon.com/docs/introduction/scale-to-zero). Abre la app antes de salir y vigila el consumo en tu panel de Neon. Cierra las pestañas al terminar: el catálogo abierto consulta existencias cada 30 segundos.

Esta configuración es una forma económica de comenzar; la disponibilidad final depende de las plataformas y de sus cuotas. No es necesario comprar un dominio para obtener HTTPS. Cuando el negocio crezca, podrás cambiar el plan manteniendo el mismo código y PostgreSQL.

## Si aparece un error

| Problema | Qué revisar |
| --- | --- |
| «No se pudo iniciar la base de datos» | DATABASE_URL completa, SSL, proyecto Neon activo y hash configurado |
| «Contraseña incorrecta» | Escribe tu contraseña normal, no el hash; si hace falta genera otro hash y actualiza Secrets |
| «No matching distribution» | Python seleccionado y versiones de requirements.txt; consulta el log de despliegue |
| No aparecen imágenes | Carpeta assets/products/ subida con los mismos nombres y mayúsculas |
| El stock cambió mientras vendías | Revisa cantidades y precios del carrito; la app evita vender unidades inexistentes |
| El celular pide una cuenta de Streamlit | Revisa la visibilidad de la app en Community Cloud |

Si compartes un error para recibir ayuda, omite contraseñas y cadenas de conexión.
