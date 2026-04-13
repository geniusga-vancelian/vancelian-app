"""Phase 4C.4 / 4C.6 — évaluation go/no-go pour couper ``ALLOW_LEGACY_UNAUTHENTICATED_KYC`` / routes legacy.

Décision support (pas d’enforcement) : agrège les compteurs Phase 4C.3 + paramètres
configurables. Les compteurs in-process sont **cumulatifs depuis le démarrage du process**
(sauf reset manuel) — voir ``observation_note`` ; pour une fenêtre glissante, croiser
avec Prometheus / logs / SIEM.

Phase 4C.6 : ``confidence_score`` (0.0–1.0) et ``confidence_band`` sont **informatifs** ;
seul ``ready`` fait foi pour la décision go/no-go.

Phase 4C.7 : prise en compte optionnelle de ``last_24h_hits`` / ``last_7d_hits`` (snapshot Phase 4C.5)
avec seuils ``LEGACY_SHUTDOWN_MAX_LAST_24H_HITS`` / ``LEGACY_SHUTDOWN_MAX_LAST_7D_HITS`` (0 = désactivé).
Les critères cumulatifs existants sont conservés.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.env import allow_legacy_unauthenticated_kyc, is_dev_mode
from services.persons.legacy_persons_metrics import (
    LAST_24H_HITS,
    LAST_7D_HITS,
    LEGACY_PERSONS_ENDPOINT_HIT_TOTAL,
)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        return int(str(raw).strip())
    except ValueError:
        return default


def _truthy_env(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower().strip() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class LegacyPersonsShutdownReadinessConfig:
    """Seuils — valeurs ``<= 0`` sur les max *hits* signifient « critère désactivé » (sauf max_unauth)."""

    max_total_hits: int = 0  # 0 = pas de plafond sur le volume total
    max_unauthenticated_hits: int = 0  # prêt si unauthenticated <= ce seuil (0 = aucun hit non auth)
    max_admin_hits: int = -1  # -1 = illimité ; 0 = aucun hit admin autorisé
    max_owner_hits: int = -1
    require_successor_identity_evidence: bool = False
    min_successor_identity_hits: int = 1
    manual_override_ready: bool = False
    manual_override_block: bool = False
    # Phase 4C.7 — 0 = critère désactivé (pas de blocage sur cette fenêtre).
    max_last_24h_hits: int = 0
    max_last_7d_hits: int = 0


def legacy_shutdown_readiness_config_from_env() -> LegacyPersonsShutdownReadinessConfig:
    return LegacyPersonsShutdownReadinessConfig(
        max_total_hits=_int_env("LEGACY_SHUTDOWN_MAX_TOTAL_HITS", 0),
        max_unauthenticated_hits=_int_env("LEGACY_SHUTDOWN_MAX_UNAUTHENTICATED_HITS", 0),
        max_admin_hits=_int_env("LEGACY_SHUTDOWN_MAX_ADMIN_HITS", -1),
        max_owner_hits=_int_env("LEGACY_SHUTDOWN_MAX_OWNER_HITS", -1),
        require_successor_identity_evidence=_truthy_env("LEGACY_SHUTDOWN_REQUIRE_SUCCESSOR_EVIDENCE", "false"),
        min_successor_identity_hits=max(0, _int_env("LEGACY_SHUTDOWN_MIN_SUCCESSOR_IDENTITY_HITS", 1)),
        manual_override_ready=_truthy_env("LEGACY_SHUTDOWN_MANUAL_OVERRIDE_READY", "false"),
        manual_override_block=_truthy_env("LEGACY_SHUTDOWN_MANUAL_OVERRIDE_BLOCK", "false"),
        max_last_24h_hits=_int_env("LEGACY_SHUTDOWN_MAX_LAST_24H_HITS", 0),
        max_last_7d_hits=_int_env("LEGACY_SHUTDOWN_MAX_LAST_7D_HITS", 0),
    )


def summarize_traffic_from_metrics_snapshot(metrics_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """Agrège les séries Phase 4C.3 et les fenêtres Phase 4C.5 (sans identifiants personne)."""
    total = int(metrics_snapshot.get(LEGACY_PERSONS_ENDPOINT_HIT_TOTAL, 0) or 0)
    unauthenticated = 0
    admin_hits = 0
    owner_hits = 0
    for s in metrics_snapshot.get("series", []) or []:
        labels = s.get("labels") or {}
        v = int(s.get("value", 0) or 0)
        if labels.get("authenticated") == "false":
            unauthenticated += v
        cc = labels.get("caller_category")
        if cc == "admin":
            admin_hits += v
        elif cc == "owner":
            owner_hits += v
    last_24h = int(metrics_snapshot.get(LAST_24H_HITS, 0) or 0)
    last_7d = int(metrics_snapshot.get(LAST_7D_HITS, 0) or 0)
    return {
        "total_hits": total,
        "unauthenticated_hits": unauthenticated,
        "admin_hits": admin_hits,
        "owner_hits": owner_hits,
        "last_24h_hits": last_24h,
        "last_7d_hits": last_7d,
    }


OBSERVATION_NOTE = (
    "Compteurs in-process cumulatifs depuis le démarrage (Phase 4C.3), sauf reset ; "
    "last_24h_hits / last_7d_hits proviennent des fenêtres glissantes Phase 4C.5 (même process). "
    "Croiser avec SIEM pour validation si besoin."
)


def _blocking_reasons(
    *,
    cfg: LegacyPersonsShutdownReadinessConfig,
    traffic: Dict[str, Any],
    successor_identity_hits: int,
) -> List[str]:
    reasons: List[str] = []
    total = int(traffic["total_hits"])
    unauth = int(traffic["unauthenticated_hits"])
    admin_hits = int(traffic["admin_hits"])
    owner_hits = int(traffic["owner_hits"])

    if unauth > cfg.max_unauthenticated_hits:
        reasons.append("unauthenticated_traffic_above_threshold")

    if cfg.max_total_hits > 0 and total > cfg.max_total_hits:
        reasons.append("total_traffic_above_threshold")

    if cfg.max_admin_hits >= 0 and admin_hits > cfg.max_admin_hits:
        reasons.append("admin_usage_above_threshold")

    if cfg.max_owner_hits >= 0 and owner_hits > cfg.max_owner_hits:
        reasons.append("owner_usage_above_threshold")

    if cfg.require_successor_identity_evidence and successor_identity_hits < cfg.min_successor_identity_hits:
        reasons.append("insufficient_successor_identity_evidence")

    last_24h = int(traffic.get("last_24h_hits", 0) or 0)
    last_7d = int(traffic.get("last_7d_hits", 0) or 0)
    if cfg.max_last_24h_hits > 0 and last_24h > cfg.max_last_24h_hits:
        reasons.append("recent_24h_traffic_above_threshold")
    if cfg.max_last_7d_hits > 0 and last_7d > cfg.max_last_7d_hits:
        reasons.append("recent_7d_traffic_above_threshold")

    return sorted(reasons)


# Phase 4C.6 — pénalités déterministes (somme plafonnée à [0, 1] après clamp).
_PENALTY_UNAUTHENTICATED_PRESENT = 0.5
_PENALTY_TOTAL_ABOVE_THRESHOLD = 0.2
_PENALTY_ADMIN_ABOVE_ALLOWANCE = 0.2
_PENALTY_OWNER_ABOVE_ALLOWANCE = 0.1
_PENALTY_SUCCESSOR_EVIDENCE_MISSING = 0.2
_PENALTY_RECENT_24H_ABOVE = 0.1
_PENALTY_RECENT_7D_ABOVE = 0.1


def _compute_confidence_score(
    cfg: LegacyPersonsShutdownReadinessConfig,
    traffic: Dict[str, Any],
    successor_identity_hits: int,
) -> float:
    """Score de 1.0 (aucun signal négatif) à 0.0 (plusieurs pénalités). Indépendant de ``ready``."""
    total = int(traffic["total_hits"])
    unauth = int(traffic["unauthenticated_hits"])
    admin_hits = int(traffic["admin_hits"])
    owner_hits = int(traffic["owner_hits"])
    last_24h = int(traffic.get("last_24h_hits", 0) or 0)
    last_7d = int(traffic.get("last_7d_hits", 0) or 0)

    score = 1.0
    if unauth > 0:
        score -= _PENALTY_UNAUTHENTICATED_PRESENT
    if cfg.max_total_hits > 0 and total > cfg.max_total_hits:
        score -= _PENALTY_TOTAL_ABOVE_THRESHOLD
    if cfg.max_admin_hits >= 0 and admin_hits > cfg.max_admin_hits:
        score -= _PENALTY_ADMIN_ABOVE_ALLOWANCE
    if cfg.max_owner_hits >= 0 and owner_hits > cfg.max_owner_hits:
        score -= _PENALTY_OWNER_ABOVE_ALLOWANCE
    if cfg.require_successor_identity_evidence and successor_identity_hits < cfg.min_successor_identity_hits:
        score -= _PENALTY_SUCCESSOR_EVIDENCE_MISSING
    if cfg.max_last_24h_hits > 0 and last_24h > cfg.max_last_24h_hits:
        score -= _PENALTY_RECENT_24H_ABOVE
    if cfg.max_last_7d_hits > 0 and last_7d > cfg.max_last_7d_hits:
        score -= _PENALTY_RECENT_7D_ABOVE
    return max(0.0, min(1.0, score))


def _confidence_band(score: float) -> str:
    s = max(0.0, min(1.0, score))
    if s >= 0.9:
        return "very_safe"
    if s >= 0.7:
        return "mostly_safe"
    if s >= 0.4:
        return "caution"
    return "not_safe"


def _round_confidence(score: float) -> float:
    return round(max(0.0, min(1.0, score)), 4)


def _recommendation(
    *,
    ready: bool,
    allow_legacy: bool,
    manual_override_ready: bool,
    manual_override_block: bool,
) -> str:
    if manual_override_block:
        return "keep_enabled"
    if not allow_legacy:
        return "already_disabled"
    if manual_override_ready:
        return "manual_override_ready"
    if not ready:
        return "keep_enabled"
    if is_dev_mode():
        return "disable_in_staging_first"
    return "ready_to_disable_production"


@dataclass
class LegacyPersonsShutdownReadinessResult:
    ready: bool
    blocking_reasons: List[str]
    traffic_summary: Dict[str, Any]
    recommendation: str
    confidence_score: float = 1.0
    confidence_band: str = "very_safe"
    observation_note: str = OBSERVATION_NOTE
    allow_legacy_unauthenticated_kyc: bool = False
    config_effective: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ready": self.ready,
            "confidence_score": _round_confidence(self.confidence_score),
            "confidence_band": self.confidence_band,
            "blocking_reasons": self.blocking_reasons,
            "traffic_summary": self.traffic_summary,
            "recommendation": self.recommendation,
            "observation_note": self.observation_note,
            "allow_legacy_unauthenticated_kyc": self.allow_legacy_unauthenticated_kyc,
            "config_effective": self.config_effective,
        }


def evaluate_legacy_persons_shutdown_readiness(
    *,
    metrics_snapshot: Dict[str, Any],
    config: Optional[LegacyPersonsShutdownReadinessConfig] = None,
    successor_identity_hits: int = 0,
    allow_legacy_kyc_flag: Optional[bool] = None,
) -> LegacyPersonsShutdownReadinessResult:
    cfg = config or legacy_shutdown_readiness_config_from_env()
    allow_legacy = (
        allow_legacy_kyc_flag if allow_legacy_kyc_flag is not None else allow_legacy_unauthenticated_kyc()
    )
    traffic = summarize_traffic_from_metrics_snapshot(metrics_snapshot)

    cfg_dict = {
        "max_total_hits": cfg.max_total_hits,
        "max_unauthenticated_hits": cfg.max_unauthenticated_hits,
        "max_admin_hits": cfg.max_admin_hits,
        "max_owner_hits": cfg.max_owner_hits,
        "require_successor_identity_evidence": cfg.require_successor_identity_evidence,
        "min_successor_identity_hits": cfg.min_successor_identity_hits,
        "manual_override_ready": cfg.manual_override_ready,
        "manual_override_block": cfg.manual_override_block,
        "max_last_24h_hits": cfg.max_last_24h_hits,
        "max_last_7d_hits": cfg.max_last_7d_hits,
    }

    if not allow_legacy:
        return LegacyPersonsShutdownReadinessResult(
            ready=True,
            blocking_reasons=[],
            traffic_summary=traffic,
            recommendation="already_disabled",
            confidence_score=1.0,
            confidence_band=_confidence_band(1.0),
            allow_legacy_unauthenticated_kyc=False,
            config_effective=cfg_dict,
        )

    if cfg.manual_override_block:
        return LegacyPersonsShutdownReadinessResult(
            ready=False,
            blocking_reasons=["manual_override_block"],
            traffic_summary=traffic,
            recommendation=_recommendation(
                ready=False,
                allow_legacy=allow_legacy,
                manual_override_ready=False,
                manual_override_block=True,
            ),
            confidence_score=0.0,
            confidence_band=_confidence_band(0.0),
            allow_legacy_unauthenticated_kyc=allow_legacy,
            config_effective=cfg_dict,
        )

    if cfg.manual_override_ready:
        return LegacyPersonsShutdownReadinessResult(
            ready=True,
            blocking_reasons=[],
            traffic_summary=traffic,
            recommendation=_recommendation(
                ready=True,
                allow_legacy=allow_legacy,
                manual_override_ready=True,
                manual_override_block=False,
            ),
            confidence_score=1.0,
            confidence_band=_confidence_band(1.0),
            allow_legacy_unauthenticated_kyc=allow_legacy,
            config_effective=cfg_dict,
        )

    reasons = _blocking_reasons(
        cfg=cfg,
        traffic=traffic,
        successor_identity_hits=successor_identity_hits,
    )
    ready = len(reasons) == 0
    conf = _compute_confidence_score(cfg, traffic, successor_identity_hits)
    return LegacyPersonsShutdownReadinessResult(
        ready=ready,
        blocking_reasons=reasons,
        traffic_summary=traffic,
        recommendation=_recommendation(
            ready=ready,
            allow_legacy=allow_legacy,
            manual_override_ready=False,
            manual_override_block=False,
        ),
        confidence_score=conf,
        confidence_band=_confidence_band(conf),
        allow_legacy_unauthenticated_kyc=allow_legacy,
        config_effective=cfg_dict,
    )


def build_legacy_persons_shutdown_readiness_report(
    *,
    successor_identity_hits: int = 0,
    metrics_snapshot: Optional[Dict[str, Any]] = None,
    config: Optional[LegacyPersonsShutdownReadinessConfig] = None,
) -> Dict[str, Any]:
    """Résumé structuré pour admin / scripts (dict JSON-sérialisable)."""
    from services.persons.legacy_persons_metrics import get_legacy_persons_metrics

    snap = metrics_snapshot if metrics_snapshot is not None else get_legacy_persons_metrics().snapshot()
    result = evaluate_legacy_persons_shutdown_readiness(
        metrics_snapshot=snap,
        config=config,
        successor_identity_hits=successor_identity_hits,
    )
    return result.as_dict()
