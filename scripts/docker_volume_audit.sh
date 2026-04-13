#!/usr/bin/env bash
# Audit lecture seule des volumes Docker liés à Arquantix (aucune suppression).
# Usage : bash scripts/docker_volume_audit.sh
set -euo pipefail

if ! command -v docker >/dev/null 2>&1 || ! docker info >/dev/null 2>&1; then
  echo "Docker indisponible." >&2
  exit 1
fi

echo "=== Volumes dont le nom contient « arquantix » ==="
docker volume ls --format '{{.Name}}' 2>/dev/null | grep -i arquantix || echo "(aucun)"
echo ""

echo "=== Volumes attendus par le compose actuel (référence) ==="
for v in arquantix_arquantix-db-data arquantix_arquantix-redis-data; do
  if docker volume inspect "$v" >/dev/null 2>&1; then
    echo "--- $v ---"
    docker volume inspect "$v" --format '  Created: {{.CreatedAt}}
  Mountpoint: {{.MountPoint}}
  Driver: {{.Driver}}'
    if command -v du >/dev/null 2>&1; then
      mp="$(docker volume inspect "$v" --format '{{.MountPoint}}' 2>/dev/null || true)"
      if [[ -n "$mp" && -d "$mp" ]]; then
        echo -n "  Taille (du -sh) : "
        du -sh "$mp" 2>/dev/null || echo "(indisponible depuis l’hôte — Docker Desktop VM)"
      fi
    fi
  else
    echo "--- $v --- ABSENT (sera créé au premier up sans external si jamais utilisé)"
  fi
  echo ""
done

echo "=== Synthèse ==="
echo "Volume DB principal attendu par docker-compose.arquantix.yml : arquantix_arquantix-db-data"
echo "Volume Redis principal : arquantix_arquantix-redis-data"
echo "Autres volumes *arquantix* listés ci-dessus = historiques / expérimentations (données non utilisées par le compose actuel sauf si migration manuelle)."
