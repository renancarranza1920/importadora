# Actualizar la tienda en Oracle Cloud

El propietario ejecuta la tienda desde `~/importadora` en Ubuntu, con Docker y Python 3.12. El Dockerfile mostrado instala `requirements.txt`, copia el proyecto a `/app` y ejecuta Streamlit en el puerto interno 8501. Esa estructura es compatible con estos cambios: las dependencias de ejecución no cambiaron. El contenedor web confirmado se llama `importadora` y publica `127.0.0.1:8501->8501`; PostgreSQL 18 corre por separado en `importadora_db`. El propietario no usa Compose. No tenemos acceso al servidor ni conocemos sus volúmenes, dominio, variables, red o comando original. No detengas ni recrees `importadora_db` para cambios de interfaz.

## Actualización rápida del contenedor existente

El propietario actualiza el checkout directamente desde la rama `main` de su repositorio. Primero integra los cambios en esa rama; los archivos preparados en una sesión de Codex no implican por sí solos un push. Después, en Oracle:

```bash
cd ~/importadora
git switch main
git pull --ff-only origin main
bash scripts/actualizar_oracle.sh importadora
```

El script respalda `app.py`, `order_views.py`, `styles.css` y `shop.py` cuando existe, copia únicamente esos cuatro archivos y reinicia **ese mismo contenedor**. Conserva sus puertos, variables y montajes; no copia, elimina ni reinicia el inventario. Valida el código antes del reinicio, espera la salud HTTP y restaura el código anterior si falla. El breve reinicio cierra sesiones del navegador; recarga la tienda después. No uses `sudo` salvo que tu usuario realmente lo necesite para Docker.

Este método sirve para actualizar ahora sin adivinar el comando `docker run`. Permanece al reiniciar ese contenedor; **al recrearlo desde una imagen antigua perderías la actualización de código**. Para actualizaciones duraderas, reconstruye la imagen y recréalo con la configuración real del despliegue existente, una vez comprobada la persistencia.

Si Git informa cambios locales o ramas divergentes, revisa y conserva esos cambios antes de continuar; no fuerces un reset. El Dockerfile actual utiliza `COPY . .`: un `git pull` actualiza los archivos del servidor, mientras que el script aplica el código al contenedor existente. No basta con reiniciar una imagen que todavía contiene el código anterior. El ZIP de la entrega queda como respaldo opcional, no como el flujo habitual.

## Reconstruir la imagen

Se incluye `deploy/Dockerfile` como alternativa al Dockerfile existente, para no sobrescribir el archivo que mostraste. Mantiene Python 3.12, añade una comprobación de salud y evita actualizar pip sin necesidad. `.dockerignore` excluye entornos locales, secretos, contraseñas, bases, respaldos y anuncios del contexto. Conserva `data/catalog_seed.json`.

```bash
cd ~/importadora
docker build -f deploy/Dockerfile -t importadora:actualizada .
```

Construir una imagen no actualiza el contenedor existente. Para recrearlo más adelante, primero recupera los montajes, red y variables existentes de manera segura. No se ha inventado un nuevo `docker run`: debemos conservar la configuración del servidor. No pegues `docker inspect` completo en el chat porque puede contener credenciales. La actualización rápida usa el mismo contenedor y no requiere recordar su comando de creación.

## Comprobar persistencia antes de recrear

Consulta solo los montajes, sin valores de variables:

```bash
docker inspect --format '{{range .Mounts}}{{println .Type .Source "->" .Destination}}{{end}}' importadora
```

Si la tienda utiliza SQLite, `data/inventory.db` debe estar en almacenamiento persistente, normalmente un montaje que cubra `/app/data`. Si no hay montaje, **no elimines ni recrees el contenedor antes de respaldar y preparar esa persistencia**. La actualización rápida de código no lo elimina. Si usa PostgreSQL, conserva su conexión existente sin publicarla ni imprimirla. La aplicación exige PostgreSQL con `APP_ENV=production`; si tu despliegue actual usa SQLite, conserva su `APP_ENV=local`. No cambies estos ajustes por suposición.

Verifica después: catálogo, filtro de modelo, asistente, pedido de 1–2 unidades bloqueado y de 3 habilitado, acceso administrador y existencias. La comprobación de salud confirma el servidor HTTP; también hay que comprobar la aplicación. Los anuncios preparados provienen del catálogo inicial y no se deben tomar como stock actual de Oracle.
