"""
État du cron « Refresh Data » (backfill des barres en retard).
Stocké dans un fichier pour éviter une migration DB. Actif par défaut.
Log des dernières exécutions en mémoire.
"""
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List

# Fichier dans api/data/ (créé à la volée)
API_DIR = Path(__file__).resolve().parent.parent.parent
CRON_ENABLED_FILE = API_DIR / "data" / "cron_refresh_enabled"

# Intervalle en secondes (toutes les minutes)
CRON_INTERVAL_SECONDS = 60

# Derniers logs (en mémoire, max 200)
_CRON_LOGS: List[Dict[str, Any]] = []
_MAX_LOGS = 200


def is_cron_enabled() -> bool:
    """True si le cron refresh est activé. Par défaut True (fichier absent ou contenu 1)."""
    if not CRON_ENABLED_FILE.exists():
        return True
    try:
        return CRON_ENABLED_FILE.read_text().strip() == "1"
    except Exception:
        return True


def set_cron_enabled(enabled: bool) -> None:
    """Active ou désactive le cron refresh."""
    CRON_ENABLED_FILE.parent.mkdir(parents=True, exist_ok=True)
    CRON_ENABLED_FILE.write_text("1" if enabled else "0")


def add_cron_log(job: str, download_summary: List[Dict[str, Any]]) -> None:
    """Enregistre une exécution du cron (datetime UTC, job, bars par asset/période)."""
    entry = {
        "datetime": datetime.now(timezone.utc).isoformat(),
        "job": job,
        "bars_by_asset_period": download_summary if download_summary else [],
    }
    _CRON_LOGS.append(entry)
    while len(_CRON_LOGS) > _MAX_LOGS:
        _CRON_LOGS.pop(0)


def get_cron_logs(limit: int = 100) -> List[Dict[str, Any]]:
    """Retourne les derniers logs (les plus récents en dernier)."""
    return list(_CRON_LOGS[-limit:])
