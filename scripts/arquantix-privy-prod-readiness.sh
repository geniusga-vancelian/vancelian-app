#!/usr/bin/env bash
# Sonde readiness Privy (infra + client optionnel) — local ou prod.
#
# Usage :
#   ./scripts/arquantix-privy-prod-readiness.sh
#   ./scripts/arquantix-privy-prod-readiness.sh --api https://api.arquantix.com
#   ./scripts/arquantix-privy-prod-readiness.sh --person 8b0e0044-f1ef-47a5-99d4-370598a77492
#
# Nécessite des en-têtes admin (Zero Trust) si l’API exige l’auth :
#   ADMIN_HEADERS='-H X-Actor-Type:admin -H X-Actor-Id:ops -H X-Actor-Roles:admin'
set -euo pipefail

API_BASE="${API_BASE:-http://localhost:8000}"
PERSON_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --api) API_BASE="$2"; shift 2 ;;
    --person) PERSON_ID="$2"; shift 2 ;;
    *) echo "Option inconnue: $1" >&2; exit 1 ;;
  esac
done

ADMIN_HEADERS=${ADMIN_HEADERS:-"-H X-Actor-Type:admin -H X-Actor-Id:admin@test.local -H X-Actor-Roles:admin"}

echo "==> API $API_BASE"

echo ""
echo "--- db-status"
curl -sf "$API_BASE/api/diagnostics/db-status" | python3 -m json.tool || echo "(db-status failed)"

echo ""
echo "--- privy infra-readiness (admin)"
# shellcheck disable=SC2086
curl -sf $ADMIN_HEADERS "$API_BASE/api/admin/privy-wallet/infra-readiness" | python3 -m json.tool || echo "(infra-readiness failed — auth ou route)"

if [[ -n "$PERSON_ID" ]]; then
  echo ""
  echo "--- privy customer-readiness $PERSON_ID"
  # shellcheck disable=SC2086
  curl -sf $ADMIN_HEADERS "$API_BASE/api/admin/privy-wallet/customer-readiness/$PERSON_ID" | python3 -m json.tool || echo "(customer-readiness failed)"
fi

echo ""
echo "--- webhook route (sans signature → 401 attendu si secret configuré)"
code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_BASE/api/webhooks/privy" -H 'Content-Type: application/json' -d '{}')
echo "POST /api/webhooks/privy → HTTP $code (401/403 = route OK + vérif active)"
