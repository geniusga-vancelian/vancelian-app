#!/usr/bin/env bash
# Nettoyage Docker : conteneurs arrêtés uniquement — AUCUN volume supprimé.
#
# Comportement par défaut : affiche la liste des conteneurs « exited » éligibles et NE SUPPRIME RIEN.
# Suppression réelle : bash scripts/docker_safe_cleanup.sh --force
#
# N'utilise jamais : docker volume prune, docker system prune --volumes, compose down -v
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "docker absent du PATH." >&2
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon indisponible." >&2
  exit 1
fi

list_exited() {
  echo "=== Conteneurs status=exited (éligibles à « docker container prune ») ==="
  docker ps -a --filter "status=exited" --format '{{.ID}} {{.Names}} {{.Status}}' 2>/dev/null || true
  echo ""
}

case "${1:-}" in
  --force)
    list_exited
    echo "→ docker container prune -f  (supprime uniquement les conteneurs arrêtés ; les volumes sont conservés)"
    docker container prune -f
    echo "✓ Terminé. Les volumes nommés (dont arquantix_arquantix-db-data) ne sont pas affectés."
    ;;
  --dry-run|"")
    list_exited
    echo "Aucune suppression (mode par défaut). Pour exécuter le prune :"
    echo "  bash scripts/docker_safe_cleanup.sh --force"
    ;;
  -h|--help)
    grep '^#' "$0" | grep -v '^#!' | sed 's/^# //' | head -18
    ;;
  *)
    echo "Usage: $0 [--dry-run] | --force" >&2
    exit 2
    ;;
esac
