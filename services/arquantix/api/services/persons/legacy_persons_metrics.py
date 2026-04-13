"""Compteurs agrégés — hits sur les endpoints persons legacy (Phase 4C.3 / 4C.5).

Même approche que ``services/price_alerts/metrics`` : compteurs en mémoire, thread-safe,
sans dépendance Prometheus — exposables via ``snapshot()`` (scraping admin / dashboards).

Phase 4C.5 : fenêtres glissantes ``last_24h_hits`` / ``last_7d_hits`` via horodatages UTC
(un float par hit, aucun PII). Le total cumulatif process-lifetime est inchangé.

Cardinalité bornée : ``endpoint_name`` (2 valeurs), ``caller_category`` (3), booléens en ``true``/``false``.
Aucun identifiant personne dans les labels ni dans la fenêtre glissante.
"""
from __future__ import annotations

import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, DefaultDict, Deque, Dict, List, Tuple

# Nom logique aligné sur les conventions Prometheus (counter *_total + labels).
LEGACY_PERSONS_ENDPOINT_HIT_TOTAL = "legacy_persons_endpoint_hit_total"

LAST_24H_HITS = "last_24h_hits"
LAST_7D_HITS = "last_7d_hits"

_SEVEN_DAYS_SEC = 7 * 24 * 3600
_TWENTY_FOUR_H_SEC = 24 * 3600
# Plafond dur : au-delà, on retire les plus anciens (après élagage 7 j). Rare en charge normale.
_MAX_ROLLING_TIMESTAMPS = 100_000

_LabelKey = Tuple[str, str, str, str, str]


def _utc_now_ts() -> float:
    """Horloge injectable pour les tests (monkeypatch du symbole dans ce module)."""
    return datetime.now(timezone.utc).timestamp()


class LegacyPersonsMetrics:
    """Compteur unique ``legacy_persons_endpoint_hit_total`` découpé par labels."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._total = 0
        self._by_labels: DefaultDict[_LabelKey, int] = defaultdict(int)
        # Horodatages UTC (secondes) des hits — aucune donnée personnelle.
        self._recent_ts: Deque[float] = deque()

    def _prune_unlocked(self, now: float) -> None:
        cutoff_7d = now - _SEVEN_DAYS_SEC
        while self._recent_ts and self._recent_ts[0] < cutoff_7d:
            self._recent_ts.popleft()
        while len(self._recent_ts) > _MAX_ROLLING_TIMESTAMPS:
            self._recent_ts.popleft()

    def _rolling_counts_unlocked(self, now: float) -> Tuple[int, int]:
        self._prune_unlocked(now)
        cutoff_24h = now - _TWENTY_FOUR_H_SEC
        last_24h = sum(1 for t in self._recent_ts if t >= cutoff_24h)
        last_7d = len(self._recent_ts)
        return last_24h, last_7d

    def record_hit(
        self,
        *,
        endpoint_name: str,
        method: str,
        authenticated: bool,
        caller_category: str,
        allow_legacy_unauthenticated_kyc: bool,
    ) -> None:
        aut = "true" if authenticated else "false"
        leg = "true" if allow_legacy_unauthenticated_kyc else "false"
        key: _LabelKey = (endpoint_name, method, aut, caller_category, leg)
        with self._lock:
            self._total += 1
            self._by_labels[key] += 1
            now = _utc_now_ts()
            self._recent_ts.append(now)
            self._prune_unlocked(now)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            now = _utc_now_ts()
            last_24h, last_7d = self._rolling_counts_unlocked(now)
            series: List[Dict[str, Any]] = []
            for key in sorted(self._by_labels.keys()):
                en, meth, aut, cc, leg = key
                count = self._by_labels[key]
                series.append(
                    {
                        "labels": {
                            "endpoint_name": en,
                            "method": meth,
                            "authenticated": aut,
                            "caller_category": cc,
                            "allow_legacy_unauthenticated_kyc": leg,
                        },
                        "value": count,
                    }
                )
            return {
                "metric": LEGACY_PERSONS_ENDPOINT_HIT_TOTAL,
                LEGACY_PERSONS_ENDPOINT_HIT_TOTAL: self._total,
                LAST_24H_HITS: last_24h,
                LAST_7D_HITS: last_7d,
                "series": series,
            }

    def reset_for_tests(self) -> None:
        with self._lock:
            self._total = 0
            self._by_labels.clear()
            self._recent_ts.clear()


_metrics = LegacyPersonsMetrics()

# Version d’export stable pour consommateurs externes (scraping, jobs, SIEM léger).
LEGACY_PERSONS_METRICS_EXPORT_KIND = "legacy_persons_metrics_v1"


def build_legacy_persons_metrics_export() -> Dict[str, Any]:
    """Export JSON déterministe pour admin HTTP, scripts ou jobs (cron).

    Reprend ``snapshot()`` tel quel (totaux, fenêtres 24h/7j, séries à labels bornés).
    Peut être persisté hors process pour continuité après redémarrage.
    """
    snap = get_legacy_persons_metrics().snapshot()
    return {
        "export_kind": LEGACY_PERSONS_METRICS_EXPORT_KIND,
        "exported_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "metrics": snap,
    }


def get_legacy_persons_metrics() -> LegacyPersonsMetrics:
    return _metrics
