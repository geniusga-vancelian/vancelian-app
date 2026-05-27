#!/usr/bin/env bash
# Seeds prod : instruments Base + bundles PE + config CMS Vault Builder (Two Kings, Crypto Majors).
#
# Prérequis : images ECS déployées (scripts présents dans l'image), AWS CLI + accès ECS.
# Usage :
#   bash scripts/arquantix-prod-seed-base-bundles.sh
#   bash scripts/arquantix-prod-seed-base-bundles.sh --dry-run   # affiche les commandes seulement
#
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_JOB="$REPO_ROOT/scripts/arquantix-ecs-run-job.sh"
chmod +x "$RUN_JOB"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

run_api() {
  local label="$1"
  local cmd="$2"
  echo ""
  echo "━━ API: $label ━━"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  $cmd"
    return 0
  fi
  "$RUN_JOB" arquantix-api arquantix-api "$cmd"
}

run_web() {
  local label="$1"
  local cmd="$2"
  echo ""
  echo "━━ Web (Prisma CMS): $label ━━"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "  $cmd"
    return 0
  fi
  "$RUN_JOB" vancelian-next vancelian-next "$cmd"
}

echo "Arquantix prod — seed Base bundles + instruments"
echo "Cluster: ${ECS_CLUSTER:-arquantix-cluster}"

run_api "sync_base_allowed_instruments" \
  "cd /app && python3 scripts/sync_base_allowed_instruments.py"

run_api "seed_pe_crypto_assets" \
  "cd /app && python3 scripts/seed_pe_crypto_assets.py"

run_api "bootstrap_crypto_bundle_base_portfolio" \
  "cd /app && python3 scripts/bootstrap_crypto_bundle_base_portfolio.py"

run_api "delete_legacy_crypto_bundles" \
  "cd /app && python3 scripts/delete_legacy_crypto_bundles.py"

run_web "delete_legacy_crypto_bundle_configs" \
  "cd /app && npx tsx scripts/delete-legacy-crypto-bundle-configs.ts"

run_web "seed_crypto_base_bundles_portfolio_config" \
  "cd /app && npx tsx scripts/seed-crypto-base-bundles-portfolio-config.ts"

echo ""
echo "✅ Seeds prod terminés."
