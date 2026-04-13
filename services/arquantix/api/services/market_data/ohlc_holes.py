"""
Détection des trous dans les historiques OHLC par instrument et par période (M5, H1, H4, D1, W1).
Un trou = absence de barre attendue entre deux barres consécutives.
Analyse aussi le retard entre la dernière barre en base et la datetime courante (UTC).
"""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database import MarketDataInstrument
from services.market_data.bars_1m_repo import get_bars_1m
from services.market_data.bars_5m_repo import get_bars_5m
from services.market_data.bars_1h_repo import get_bars_1h
from services.market_data.bars_4h_repo import get_bars_4h
from services.market_data.bars_1d_repo import get_bars_1d
from services.market_data.bars_1w_repo import get_bars_1w


# Limite de barres par période pour le scan (éviter des requêtes trop lourdes)
HOLE_SCAN_LIMIT = 50_000

# Périodes OHLC supportées
OHLC_PERIODS = ("M1", "M5", "H1", "H4", "D1", "W1")

# Pas attendu entre deux barres consécutives (timezone-aware géré par les datetimes des bars)
STEP_BY_PERIOD = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
    "W1": timedelta(weeks=1),
}


def _get_open_times(
    session: Session,
    instrument_id: int,
    period: str,
) -> List[Any]:
    """Retourne la liste des open_time triés par ordre croissant pour la période donnée."""
    limit = HOLE_SCAN_LIMIT
    if period == "M1":
        bars = get_bars_1m(session, instrument_id, limit=limit)
    elif period == "M5":
        bars = get_bars_5m(session, instrument_id, limit=limit)
    elif period == "H1":
        bars = get_bars_1h(session, instrument_id, limit=limit)
    elif period == "H4":
        bars = get_bars_4h(session, instrument_id, limit=limit)
    elif period == "D1":
        bars = get_bars_1d(session, instrument_id, limit=limit)
    elif period == "W1":
        bars = get_bars_1w(session, instrument_id, limit=limit)
    else:
        return []
    return [b.open_time for b in bars if b.open_time is not None]


def _expected_bar_count(first_ot: Any, last_ot: Any, step: timedelta) -> int:
    """Nombre de barres attendu entre first_ot et last_ot (inclus) pour le pas donné.
    M5: 12 barres/heure, H1: 24 barres/jour, H4: 6 barres/jour, D1: 1/jour, W1: 1/semaine."""
    if first_ot is None or last_ot is None or step.total_seconds() <= 0:
        return 0
    delta = last_ot - first_ot
    if delta.total_seconds() < 0:
        return 0
    # nombre d'intervalles + 1 (début et fin inclus)
    n = int(delta.total_seconds() / step.total_seconds()) + 1
    return max(0, n)


def _missing_bars_to_now(last_ot: Any, step: timedelta) -> int:
    """Nombre de barres OHLC manquantes entre la dernière barre en base et maintenant (UTC).
    = nombre de périodes complètes écoulées depuis last_ot."""
    if last_ot is None or step.total_seconds() <= 0:
        return 0
    now = datetime.now(timezone.utc)
    # rendre last_ot comparable (UTC) si naive
    if last_ot.tzinfo is None:
        last_ot = last_ot.replace(tzinfo=timezone.utc)
    delta = now - last_ot
    if delta.total_seconds() <= 0:
        return 0
    return int(delta.total_seconds() / step.total_seconds())


def compute_holes_for_period(
    session: Session,
    instrument_id: int,
    period: str,
) -> Dict[str, Any]:
    """
    Pour un instrument et une période OHLC, retourne:
    - start_datetime: première barre (ISO)
    - end_datetime: dernière barre (ISO)
    - bar_count: nombre de barres en mémoire
    - expected_bar_count: nombre attendu (cohérence plage + timeframe)
    - consistency_note: "Cohérent" ou message d'incohérence
    - holes: liste de { "start": ISO, "end": ISO } pour chaque trou détecté.
    """
    step = STEP_BY_PERIOD.get(period)
    now_iso = datetime.now(timezone.utc).isoformat()
    empty_lag = {
        "current_datetime_utc": now_iso,
        "missing_bars_to_now": None,
        "lag_note": "—",
    }
    if not step:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "bar_count": 0,
            "expected_bar_count": 0,
            "consistency_note": "—",
            "holes": [],
            **empty_lag,
        }

    open_times = _get_open_times(session, instrument_id, period)
    bar_count = len(open_times)
    if bar_count == 0:
        return {
            "start_datetime": None,
            "end_datetime": None,
            "bar_count": 0,
            "expected_bar_count": 0,
            "consistency_note": "Aucune barre",
            "holes": [],
            "current_datetime_utc": now_iso,
            "missing_bars_to_now": None,
            "lag_note": "Aucune barre",
        }
    if bar_count == 1:
        start_iso = open_times[0].isoformat()
        missing = _missing_bars_to_now(open_times[0], step)
        lag_note = "À jour" if missing <= 1 else f"Retard: {missing} barres (dernière: {start_iso})"
        return {
            "start_datetime": start_iso,
            "end_datetime": start_iso,
            "bar_count": 1,
            "expected_bar_count": 1,
            "consistency_note": "Cohérent",
            "holes": [],
            "current_datetime_utc": now_iso,
            "missing_bars_to_now": missing,
            "lag_note": lag_note,
        }

    start_iso = open_times[0].isoformat()
    end_iso = open_times[-1].isoformat()
    expected = _expected_bar_count(open_times[0], open_times[-1], step)
    holes: List[Dict[str, str]] = []
    tolerance = timedelta(seconds=1)

    for i in range(len(open_times) - 1):
        prev = open_times[i]
        next_ot = open_times[i + 1]
        expected_next = prev + step
        if next_ot > expected_next + tolerance:
            holes.append({
                "start": expected_next.isoformat(),
                "end": next_ot.isoformat(),
            })

    if bar_count == expected and len(holes) == 0:
        consistency_note = "Cohérent"
    else:
        missing = expected - bar_count
        if missing > 0 and len(holes) > 0:
            consistency_note = f"Attendu: {expected}, en mémoire: {bar_count}, trous: {len(holes)}"
        elif missing > 0:
            consistency_note = f"Manquantes: {missing} (attendu: {expected})"
        else:
            consistency_note = f"Trous: {len(holes)} (attendu: {expected})"

    missing_to_now = _missing_bars_to_now(open_times[-1], step)
    lag_note = "À jour" if missing_to_now <= 1 else f"Retard: {missing_to_now} barres (dernière: {end_iso})"

    return {
        "start_datetime": start_iso,
        "end_datetime": end_iso,
        "bar_count": bar_count,
        "expected_bar_count": expected,
        "consistency_note": consistency_note,
        "holes": holes,
        "current_datetime_utc": now_iso,
        "missing_bars_to_now": missing_to_now,
        "lag_note": lag_note,
    }


def compute_ohlc_holes_for_instruments(
    session: Session,
    instrument_ids: List[int],
) -> List[Dict[str, Any]]:
    """
    Pour chaque instrument_id, calcule les trous pour M5, H1, H4, D1, W1.
    Retourne une liste de { instrument_id, symbol?, M5: {...}, H1: {...}, ... }.
    """
    result = []
    for iid in instrument_ids:
        inst = session.query(MarketDataInstrument).filter(MarketDataInstrument.id == iid).first()
        symbol = (inst.provider_symbol or inst.symbol or str(iid)) if inst else str(iid)
        row = {
            "instrument_id": iid,
            "symbol": symbol,
            "M1": compute_holes_for_period(session, iid, "M1"),
            "M5": compute_holes_for_period(session, iid, "M5"),
            "H1": compute_holes_for_period(session, iid, "H1"),
            "H4": compute_holes_for_period(session, iid, "H4"),
            "D1": compute_holes_for_period(session, iid, "D1"),
            "W1": compute_holes_for_period(session, iid, "W1"),
        }
        result.append(row)
    return result
