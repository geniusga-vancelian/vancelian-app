#!/usr/bin/env bash
# Test contrôlé Global User Transaction Lock V1 — flag ON job only · TD flags OFF.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODE="${1:-full}"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-global-lock-controlled-test.payload.b64"
[[ -f "$PAYLOAD" ]] || { echo "Payload manquant: $PAYLOAD" >&2; exit 1; }
B64="$(tr -d '\n' < "$PAYLOAD")"
TEST_RUN_ID="${GLOBAL_LOCK_TEST_RUN_ID:-$(uuidgen 2>/dev/null | tr -d '-' || python3 -c 'import uuid; print(uuid.uuid4().hex)')}"
CMD=$(B64="$B64" GLOBAL_LOCK_TEST_MODE="$MODE" GLOBAL_LOCK_TEST_RUN_ID="$TEST_RUN_ID" python3 - <<'PY'
import json, os, shlex
b64=os.environ["B64"]
mode=os.environ.get("GLOBAL_LOCK_TEST_MODE","full")
run_id=os.environ.get("GLOBAL_LOCK_TEST_RUN_ID","")
code=(
    "import os,zlib,base64; "
    f"os.environ['GLOBAL_LOCK_TEST_MODE']={json.dumps(mode)}; "
    f"os.environ['GLOBAL_LOCK_TEST_RUN_ID']={json.dumps(run_id)}; "
    "exec(zlib.decompress(base64.b64decode("+json.dumps(b64)+")))"
)
print("cd /app && python3 -c "+shlex.quote(code))
PY
)
echo "==> Global lock controlled test mode=$MODE run_id=$TEST_RUN_ID"
exec "$ROOT_DIR/scripts/arquantix-ecs-run-job.sh" arquantix-api arquantix-api "$CMD"
