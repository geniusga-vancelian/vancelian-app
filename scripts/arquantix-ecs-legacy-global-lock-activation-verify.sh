#!/usr/bin/env bash
# Vérification pré/post activation GLOBAL_USER_TRANSACTION_LOCK_ENABLED.
# Usage:
#   LEGACY_GLOBAL_LOCK_VERIFY_MODE=pre_activation ./scripts/arquantix-ecs-legacy-global-lock-activation-verify.sh
#   LEGACY_GLOBAL_LOCK_VERIFY_MODE=post_activation ./scripts/arquantix-ecs-legacy-global-lock-activation-verify.sh
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-legacy-global-lock-activation-verify.payload.b64"
[[ -f "$PAYLOAD" ]] || { echo "Payload manquant: $PAYLOAD" >&2; exit 1; }
B64="$(tr -d '\n' < "$PAYLOAD")"
CMD=$(B64="$B64" LEGACY_GLOBAL_LOCK_VERIFY_MODE="${LEGACY_GLOBAL_LOCK_VERIFY_MODE:-pre_activation}" python3 - <<'PY'
import json, os, shlex
b64=os.environ["B64"]
mode=os.environ.get("LEGACY_GLOBAL_LOCK_VERIFY_MODE","pre_activation")
code=(
    "import os; os.environ['LEGACY_GLOBAL_LOCK_VERIFY_MODE']="+json.dumps(mode)+"; "
    "import zlib,base64; exec(zlib.decompress(base64.b64decode("+json.dumps(b64)+")))"
)
print("cd /app && python3 -c "+shlex.quote(code))
PY
)
exec "$ROOT_DIR/scripts/arquantix-ecs-run-job.sh" arquantix-api arquantix-api "$CMD"
