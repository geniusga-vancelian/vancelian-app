#!/usr/bin/env bash
# Test contrôlé prod B3c — 1 parent · 1 child · 1 buy leg USDC→AAVE Base.
#
# Usage :
#   ./scripts/arquantix-ecs-bundle-b3c-controlled-test.sh baseline
#   BUNDLE_B3C_TEST_CONFIRM=1 PORTFOLIO_ID=<uuid> AMOUNT_USDC=1 \
#     ./scripts/arquantix-ecs-bundle-b3c-controlled-test.sh setup_parent_child
#   BUNDLE_B3C_TEST_CONFIRM=1 CHILD_INTENT_ID=<uuid> SWAP_ID=<uuid> \
#     ./scripts/arquantix-ecs-bundle-b3c-controlled-test.sh attach_existing_swap
#   BUNDLE_B3C_TEST_CONFIRM=1 CHILD_INTENT_ID=<uuid> \
#     ./scripts/arquantix-ecs-bundle-b3c-controlled-test.sh settle_child
#   BUNDLE_B3C_TEST_CONFIRM=1 CHILD_INTENT_ID=<uuid> BUNDLE_B3C_TEST_REPEAT=1 \
#     ./scripts/arquantix-ecs-bundle-b3c-controlled-test.sh settle_child
#   PARENT_INTENT_ID=<uuid> CHILD_INTENT_ID=<uuid> \
#     ./scripts/arquantix-ecs-bundle-b3c-controlled-test.sh audit
#   BUNDLE_B3C_TEST_CONFIRM=1 PARENT_INTENT_ID=<uuid> CHILD_INTENT_ID=<uuid> \
#     ./scripts/arquantix-ecs-bundle-b3c-controlled-test.sh rollback_or_cleanup
#
# Modes read-only : baseline · audit
# Modes write     : setup_parent_child · attach_existing_swap · settle_child · rollback_or_cleanup
#                   (exigent BUNDLE_B3C_TEST_CONFIRM=1)
#
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-bundle-b3c-controlled-test.payload.b64"
MODE="${1:-}"

if [[ -z "$MODE" ]]; then
  echo "Usage: $0 <baseline|setup_parent_child|attach_existing_swap|settle_child|audit|rollback_or_cleanup>" >&2
  exit 1
fi
shift || true

[[ -f "$PAYLOAD" ]] || { echo "Payload manquant: $PAYLOAD" >&2; exit 1; }
B64="$(tr -d '\n' < "$PAYLOAD")"

CMD=$(BUNDLE_B3C_TEST_MODE="$MODE" \
  BUNDLE_B3C_TEST_CONFIRM="${BUNDLE_B3C_TEST_CONFIRM:-}" \
  BUNDLE_B3C_TEST_REPEAT="${BUNDLE_B3C_TEST_REPEAT:-}" \
  TEST_RUN_ID="${TEST_RUN_ID:-}" \
  PORTFOLIO_ID="${PORTFOLIO_ID:-}" \
  AMOUNT_USDC="${AMOUNT_USDC:-}" \
  PARENT_INTENT_ID="${PARENT_INTENT_ID:-}" \
  CHILD_INTENT_ID="${CHILD_INTENT_ID:-}" \
  SWAP_ID="${SWAP_ID:-}" \
  B64="$B64" python3 - <<'PY'
import json, os, shlex
b64=os.environ["B64"]
mode=os.environ["BUNDLE_B3C_TEST_MODE"]
exports=[]
for key in (
    "BUNDLE_B3C_TEST_MODE",
    "BUNDLE_B3C_TEST_CONFIRM",
    "BUNDLE_B3C_TEST_REPEAT",
    "TEST_RUN_ID",
    "PORTFOLIO_ID",
    "AMOUNT_USDC",
    "PARENT_INTENT_ID",
    "CHILD_INTENT_ID",
    "SWAP_ID",
):
    val=os.environ.get(key,"")
    if val:
        exports.append(f"{key}={shlex.quote(val)}")
prefix=" ".join(exports)
code="import zlib,base64; exec(zlib.decompress(base64.b64decode("+json.dumps(b64)+")))"
inner=f"{prefix} python3 -c {shlex.quote(code)}" if prefix else f"python3 -c {shlex.quote(code)}"
print("cd /app && "+inner)
PY
)

echo "==> B3c controlled test mode=$MODE"
exec "$ROOT_DIR/scripts/arquantix-ecs-run-job.sh" arquantix-api arquantix-api "$CMD"
