#!/usr/bin/env bash
# Audit prod lecture seule — réconciliation crypto multi-couches.
# Usage : ./scripts/arquantix-ecs-audit-person-crypto.sh gaelitier@gmail.com
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EMAIL="${1:-}"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-audit-person-crypto.payload.b64"
if [[ -z "$EMAIL" ]]; then echo "Usage: $0 <email>" >&2; exit 1; fi
if [[ ! -f "$PAYLOAD" ]]; then echo "Payload manquant: $PAYLOAD" >&2; exit 1; fi
B64="$(tr -d '\n' < "$PAYLOAD")"
CMD=$(EMAIL="$EMAIL" B64="$B64" python3 - <<'PY'
import json, os, shlex
email, b64 = os.environ["EMAIL"], os.environ["B64"]
code = "import zlib,base64; exec(zlib.decompress(base64.b64decode(" + json.dumps(b64) + ")))"
print("cd /app && AUDIT_EMAIL=" + shlex.quote(email) + " python3 -c " + shlex.quote(code))
PY
)
exec "$ROOT_DIR/scripts/arquantix-ecs-run-job.sh" arquantix-api arquantix-api "$CMD"
