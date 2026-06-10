#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INLINE="${ROOT_DIR}/scripts/_bundle-active-operation-audit-inline.py"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-bundle-active-operation-audit.payload.b64"
[[ -f "$INLINE" ]] || { echo "Manquant: $INLINE" >&2; exit 1; }
python3 - "$INLINE" "$PAYLOAD" <<'PY'
import base64, pathlib, sys, zlib
src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
encoded = base64.b64encode(zlib.compress(src.encode("utf-8"), level=9)).decode("ascii")
pathlib.Path(sys.argv[2]).write_text(encoded + "\n", encoding="utf-8")
print(f"Payload: {sys.argv[2]} ({len(encoded)} chars)")
PY
