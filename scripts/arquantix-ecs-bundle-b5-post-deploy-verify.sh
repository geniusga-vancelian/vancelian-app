#!/usr/bin/env bash
# Post-deploy neutre B5 — bundle parent controller · flags OFF · aucun runtime.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-bundle-b5-post-deploy-verify.payload.b64"
[[ -f "$PAYLOAD" ]] || { echo "Payload manquant: $PAYLOAD" >&2; exit 1; }
B64="$(tr -d '\n' < "$PAYLOAD")"
CMD=$(B64="$B64" python3 - <<'PY'
import json, os, shlex
b64=os.environ["B64"]
code="import zlib,base64; exec(zlib.decompress(base64.b64decode("+json.dumps(b64)+")))"
print("cd /app && python3 -c "+shlex.quote(code))
PY
)
exec "$ROOT_DIR/scripts/arquantix-ecs-run-job.sh" arquantix-api arquantix-api "$CMD"
