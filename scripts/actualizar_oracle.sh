#!/usr/bin/env bash
# Update only application files in an existing container, preserving its runtime
# settings, ports, mounts and database. Rebuild/recreate separately with Compose.
set -euo pipefail
if [[ $# != 1 ]]; then
  echo "Uso: bash scripts/actualizar_oracle.sh NOMBRE_DEL_CONTENEDOR" >&2
  exit 2
fi
container="$1"
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"
for source_file in app.py order_views.py shop.py styles.css; do
  test -f "$source_file"
done
test "$(docker inspect --format '{{.State.Running}}' "$container")" = true
docker exec "$container" python -c "from pathlib import Path; assert Path('/app/app.py').is_file(), 'El contenedor debe ejecutar la tienda desde /app'"
mkdir -p backups
backup_file="$project_root/backups/codigo-$(date -u +%Y%m%dT%H%M%SZ)-$$.tar"
# No database or credential file is copied; filenames below are fixed.
existing_files=(app.py order_views.py styles.css)
if docker exec "$container" test -f /app/shop.py; then existing_files+=(shop.py); fi
docker exec "$container" tar -C /app -cf - "${existing_files[@]}" > "$backup_file"
tar -tf "$backup_file" >/dev/null
rollback() {
  echo "La actualización falló; restaurando el código anterior." >&2
  docker cp "$backup_file" "$container:/tmp/importadora-code-rollback.tar"
  docker exec "$container" tar -C /app -xf /tmp/importadora-code-rollback.tar
  docker restart "$container" >/dev/null
  echo "Código anterior restaurado desde $backup_file. Comprueba el servicio." >&2
}
trap rollback ERR
for source_file in app.py order_views.py shop.py styles.css; do
  docker cp "$source_file" "$container:/app/$source_file" >/dev/null
done
docker exec "$container" python -c "from pathlib import Path; [compile(Path('/app', n).read_text(), n, 'exec') for n in ('app.py', 'order_views.py', 'shop.py')]"
docker restart "$container" >/dev/null
ready=false
for attempt in {1..20}; do
  if docker exec "$container" python -c "import urllib.request; assert urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=3).read().strip() == b'ok'" >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 2
done
if [[ "$ready" != true ]]; then
  false # Trigger the rollback handler.
fi
trap - ERR
echo "Aplicación actualizada. Respaldo de código: $backup_file"
echo "Comprueba el catálogo y el pedido en tu web. Esta actualización permanece al reiniciar el contenedor, pero una recreación requiere reconstruir la imagen con el código actualizado."
