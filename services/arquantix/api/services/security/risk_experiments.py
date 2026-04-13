"""
A/B testing déterministe sur les poids de risque (Phase 5F).

Assignation stable : ``sha256(experiment_id + user_id)`` — pas d’aléa par requête.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from typing import Dict, Optional

logger = logging.getLogger("arquantix.security.risk_experiments")


def _sanitize_exp_id(exp_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_]", "_", (exp_id or "").strip())
    return s[:64] or "default"


def assign_variant(user_id: str, experiment_id: str, *, control_ratio_pct: int = 50) -> str:
    """
    ``control`` vs ``variant_a`` — répartition 50/50 par défaut (modifiable via env).
    """
    if not str(user_id).strip() or not str(experiment_id).strip():
        return "control"
    try:
        ratio = int(os.getenv("RISK_EXPERIMENT_CONTROL_RATIO_PCT", str(control_ratio_pct)))
        ratio = max(1, min(99, ratio))
    except ValueError:
        ratio = 50
    digest = hashlib.sha256(f"{experiment_id}:{user_id}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return "control" if bucket < ratio else "variant_a"


def load_variant_weight_overrides(experiment_id: str, variant: str) -> Dict[str, float]:
    """
    Overrides JSON pour la variante — **jamais** lu pour ``control``.

    Variables d’environnement (exemple) ::
        RISK_EXPERIMENT_<EXP>_VARIANT_A_WEIGHTS_JSON={"device_new":22}
    """
    if variant == "control":
        return {}
    sid = _sanitize_exp_id(experiment_id)
    raw = (
        os.getenv(f"RISK_EXPERIMENT_{sid}_VARIANT_A_WEIGHTS_JSON")
        or os.getenv("RISK_EXPERIMENT_VARIANT_A_WEIGHTS_JSON")
        or ""
    ).strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return {str(k): float(v) for k, v in data.items()}
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("Invalid experiment weights JSON for %s: %s", sid, e)
        return {}
