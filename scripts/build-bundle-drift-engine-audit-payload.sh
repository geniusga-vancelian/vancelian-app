#!/usr/bin/env bash
# Génère le payload ECS (drift_engine embarqué + audit vue gérant).
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIFT_PY="${ROOT_DIR}/services/arquantix/api/services/portfolio_engine/bundles/drift_engine.py"
PLANNER_PY="${ROOT_DIR}/services/arquantix/api/services/portfolio_engine/bundles/rebalance_planner.py"
AUDIT_PY="${ROOT_DIR}/scripts/_bundle-drift-engine-audit-inline.py"
PAYLOAD="${ROOT_DIR}/scripts/arquantix-ecs-bundle-drift-engine-audit.payload.b64"

[[ -f "$DRIFT_PY" ]] || { echo "Manquant: $DRIFT_PY" >&2; exit 1; }
[[ -f "$PLANNER_PY" ]] || { echo "Manquant: $PLANNER_PY" >&2; exit 1; }
[[ -f "$AUDIT_PY" ]] || { echo "Manquant: $AUDIT_PY" >&2; exit 1; }

python3 - "$DRIFT_PY" "$PLANNER_PY" "$AUDIT_PY" "$PAYLOAD" <<'PY'
import base64
import pathlib
import sys
import zlib

drift_path, planner_path, audit_path, payload_path = sys.argv[1:5]
def _strip_future_import(src: str) -> str:
    lines = src.splitlines()
    out: list[str] = []
    skipped_doc = False
    for line in lines:
        stripped = line.strip()
        if not skipped_doc and (stripped.startswith('"""') or stripped.startswith("'''")):
            out.append(line)
            if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                skipped_doc = True
            elif stripped.endswith('"""') or stripped.endswith("'''"):
                skipped_doc = True
            continue
        if stripped == "from __future__ import annotations":
            continue
        out.append(line)
    return "\n".join(out).lstrip("\n")


drift_src = _strip_future_import(pathlib.Path(drift_path).read_text(encoding="utf-8"))
planner_src = _strip_future_import(pathlib.Path(planner_path).read_text(encoding="utf-8"))
audit_src = _strip_future_import(pathlib.Path(audit_path).read_text(encoding="utf-8"))

bootstrap = '''from __future__ import annotations

"""ECS prod — bootstrap drift_engine + rebalance_planner si pas encore déployés."""
import sys
import types


def _ensure_pkg(pkg_name: str) -> None:
    if pkg_name not in sys.modules:
        sys.modules[pkg_name] = types.ModuleType(pkg_name)


def _bootstrap_module(name: str, src: str) -> None:
    try:
        __import__(name)
        return
    except ImportError:
        pass
    for pkg_name in (
        "services",
        "services.portfolio_engine",
        "services.portfolio_engine.bundles",
    ):
        _ensure_pkg(pkg_name)
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    exec(compile(src, name + ".py", "exec"), mod.__dict__)


_bootstrap_module(
    "services.portfolio_engine.bundles.drift_engine",
    DRIFT_ENGINE_SRC,
)
_bootstrap_module(
    "services.portfolio_engine.bundles.rebalance_planner",
    REBALANCE_PLANNER_SRC,
)
'''

combined = (
    bootstrap.replace("DRIFT_ENGINE_SRC", repr(drift_src)).replace(
        "REBALANCE_PLANNER_SRC",
        repr(planner_src),
    )
    + "\n"
    + audit_src
)

compressed = zlib.compress(combined.encode("utf-8"), level=9)
encoded = base64.b64encode(compressed).decode("ascii")
pathlib.Path(payload_path).write_text(encoded + "\n", encoding="utf-8")
print(f"Payload écrit: {payload_path} ({len(encoded)} chars b64, {len(combined)} chars source)")
PY

chmod +x "${ROOT_DIR}/scripts/build-bundle-drift-engine-audit-payload.sh" 2>/dev/null || true
