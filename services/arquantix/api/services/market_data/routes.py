"""
Market Data routes - Instrument management and data fetching
"""
import os
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

# Relative path for logo_url so the client can prepend its own base (avoids localhost on device).
MEDIA_LOGO_PATH_PREFIX = "/media/"

from database import get_db, MarketDataInstrument, MarketDataBarD1, MarketDataBar5m
from auth import get_current_user, AdminUser
from services.market_data.quotes_repo import (
    get_latest_quotes_by_instrument_ids,
    get_latest_quotes_by_provider_symbols,
    quotes_to_payload,
)
from services.market_data.bars_1m_repo import get_bars_1m
from services.market_data.bars_5m_repo import get_bars_5m
from services.market_data.bars_1h_repo import get_bars_1h
from services.market_data.bars_4h_repo import get_bars_4h
from services.market_data.bars_1d_repo import get_bars_1d
from services.market_data.bars_1w_repo import get_bars_1w
from services.market_data.chart_period_config import CHART_PERIODS
from services.market_data.chart_history_service import get_chart_history
from services.market_data.market_summary_repo import get_market_summaries
from services.market_data.top_movers_repo import get_top_movers
from services.market_data.ohlc_holes import compute_ohlc_holes_for_instruments
from services.market_data.candles_backfill_service import run_backfill

router = APIRouter(prefix="/api/market-data", tags=["market-data"])

# Timeframes pour le backfill des barres en retard (dernière barre → maintenant)
BACKFILL_LAG_TIMEFRAMES = ["5m", "1h", "4h", "1d", "1w"]


# ============================================================================
# Core V1 Instruments (CORE_V1 Universe)
# ============================================================================

CORE_V1_INSTRUMENTS = [
    {"symbol": "BTC", "name": "Bitcoin", "asset_class": "crypto", "weekend_tradable": "true"},
    {"symbol": "ETH", "name": "Ethereum", "asset_class": "crypto", "weekend_tradable": "true"},
    {"symbol": "SOL", "name": "Solana", "asset_class": "crypto", "weekend_tradable": "true"},
    {"symbol": "URTH", "name": "iShares MSCI World ETF", "asset_class": "etf", "weekend_tradable": "false"},
    {"symbol": "QQQ", "name": "Invesco QQQ Trust", "asset_class": "etf", "weekend_tradable": "false"},
    {"symbol": "DIA", "name": "SPDR Dow Jones Industrial Average ETF", "asset_class": "etf", "weekend_tradable": "false"},
    {"symbol": "GLD", "name": "SPDR Gold Trust", "asset_class": "etf", "weekend_tradable": "false"},
]


# ============================================================================
# Schemas
# ============================================================================

class InstrumentCreate(BaseModel):
    symbol: str
    name: Optional[str] = None
    asset_class: str  # "crypto", "etf", "equity", "forex", "index", "commodities"
    weekend_tradable: bool = False
    provider: str = "binance"
    provider_symbol: Optional[str] = None
    is_active: bool = True


class InstrumentUpdate(BaseModel):
    name: Optional[str] = None
    asset_class: Optional[str] = None
    weekend_tradable: Optional[bool] = None
    provider: Optional[str] = None
    provider_symbol: Optional[str] = None
    is_active: Optional[bool] = None


class InstrumentResponse(BaseModel):
    id: int
    symbol: str
    name: Optional[str]
    asset_class: str
    weekend_tradable: str
    provider: str
    provider_symbol: Optional[str]
    is_active: str
    created_at: Optional[str]

    class Config:
        from_attributes = True


# ============================================================================
# Routes
# ============================================================================

@router.get("/instruments")
def list_instruments(
    is_active: Optional[str] = None,
    asset_class: Optional[str] = None,
    provider: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List market data instruments, optionally filtered by is_active, asset_class, provider."""
    query = db.query(MarketDataInstrument)

    if asset_class is not None:
        query = query.filter(MarketDataInstrument.asset_class == asset_class.lower())
    if provider is not None:
        query = query.filter(MarketDataInstrument.provider == provider.lower())

    # Filter by is_active if provided (is_active is stored as string "true"/"false" in DB)
    if is_active is not None:
        # Convert to string format for comparison
        is_active_str = is_active.lower() if isinstance(is_active, str) else ("true" if is_active else "false")
        query = query.filter(MarketDataInstrument.is_active == is_active_str)
    
    instruments = query.order_by(MarketDataInstrument.symbol).all()
    
    # Return in format expected by frontend: { instruments: [...] }
    return {
        "instruments": [
            {
                "id": inst.id,
                "symbol": inst.symbol,
                "name": inst.name,
                "asset_class": inst.asset_class,
                "weekend_tradable": inst.weekend_tradable,
                "provider": inst.provider,
                "provider_symbol": inst.provider_symbol,
                "is_active": inst.is_active,
                "created_at": inst.created_at.isoformat() if inst.created_at else None,
            }
            for inst in instruments
        ]
    }


@router.get("/ohlc-holes")
def get_ohlc_holes(
    instrument_ids: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retourne les trous OHLC (M5, H1, H4, D1, W1) pour les instruments demandés.
    Si instrument_ids absent, utilise tous les instruments crypto Binance."""
    if instrument_ids:
        ids = [int(x.strip()) for x in instrument_ids.split(",") if x.strip()]
    else:
        rows = (
            db.query(MarketDataInstrument.id)
            .filter(
                MarketDataInstrument.asset_class == "crypto",
                MarketDataInstrument.provider == "binance",
            )
            .all()
        )
        ids = [r.id for r in rows]
    data = compute_ohlc_holes_for_instruments(db, ids)
    return {"data": data}


PERIOD_TO_TIMEFRAME = {"M1": "1m", "M5": "5m", "H1": "1h", "H4": "4h", "D1": "1d", "W1": "1w"}


def _need_backfill(info):
    """True si trous, retard, ou table vide pour cette période."""
    if not info:
        return True
    bar_count = info.get("bar_count", 0)
    if bar_count == 0:
        return True
    holes = info.get("holes") or []
    missing = info.get("missing_bars_to_now")
    if missing is None:
        missing = 0
    return len(holes) > 0 or missing > 0


def run_backfill_lag_logic(db: Session):
    """
    Logique du refresh (analyse trous -> backfill cible -> analyse apres).
    Utilisee par POST /backfill-lag et par le cron. Retourne le meme dict.
    """
    rows = (
        db.query(MarketDataInstrument.id)
        .filter(
            MarketDataInstrument.asset_class.in_(["crypto", "forex"]),
            MarketDataInstrument.provider == "binance",
        )
        .all()
    )
    ids = [r.id for r in rows]
    if not ids:
        return {
            "download_summary": [],
            "holes_analysis_after": [],
            "summary": {"total_holes_remaining": 0, "total_missing_bars_to_now_remaining": 0, "message": "Aucun instrument Binance."},
        }
    holes_before = compute_ohlc_holes_for_instruments(db, ids)
    need_backfill_set = set()
    for row in holes_before:
        symbol = (row.get("symbol") or "").strip()
        if not symbol:
            continue
        for period in ("M1", "M5", "H1", "H4", "D1", "W1"):
            info = row.get(period) or {}
            if _need_backfill(info):
                tf = PERIOD_TO_TIMEFRAME.get(period)
                if tf:
                    need_backfill_set.add((symbol, tf))
    results = {}
    for (symbol, tf) in sorted(need_backfill_set, key=lambda x: (x[1], x[0])):
        summary = run_backfill(db, timeframe=tf, symbol=symbol)
        if tf not in results:
            results[tf] = {"instrument_details": [], "candles_upserted": 0}
        results[tf]["instrument_details"] = (results[tf].get("instrument_details") or []) + (summary.get("instrument_details") or [])
        results[tf]["candles_upserted"] = (results[tf].get("candles_upserted") or 0) + (summary.get("candles_upserted") or 0)

    # S’assurer que tout est bien persisté (sécurité après les commits dans run_backfill)
    try:
        db.commit()
    except Exception:
        db.rollback()

    holes_after = compute_ohlc_holes_for_instruments(db, ids)
    total_holes_remaining = 0
    total_missing_bars_to_now_remaining = 0
    for row in holes_after:
        for period in ("M1", "M5", "H1", "H4", "D1", "W1"):
            info = row.get(period) or {}
            total_holes_remaining += len(info.get("holes") or [])
            m = info.get("missing_bars_to_now")
            if m is not None and m > 0:
                total_missing_bars_to_now_remaining += m

    by_instrument = {}
    for tf in results:
        for d in (results.get(tf) or {}).get("instrument_details") or []:
            iid = d.get("instrument_id")
            sym = d.get("provider_symbol") or ""
            if iid not in by_instrument:
                by_instrument[iid] = {"instrument_id": iid, "provider_symbol": sym, "bars_by_period": {}}
            n = d.get("candles_upserted") or 0
            by_instrument[iid]["bars_by_period"][tf] = n
    download_summary = list(by_instrument.values())
    download_summary.sort(key=lambda x: (x.get("provider_symbol") or ""))

    return {
        "download_summary": download_summary,
        "holes_analysis_after": holes_after,
        "summary": {
            "total_holes_remaining": total_holes_remaining,
            "total_missing_bars_to_now_remaining": total_missing_bars_to_now_remaining,
            "message": "Trous restants: {} (lacunes), {} barres en retard. Normalement 0 apres refresh.".format(
                total_holes_remaining, total_missing_bars_to_now_remaining
            ),
        },
    }


@router.get("/cron-refresh-status")
def get_cron_refresh_status():
    """Indique si le cron Refresh Data est actif (toutes les minutes)."""
    from services.market_data.cron_refresh import is_cron_enabled, CRON_INTERVAL_SECONDS
    return {"enabled": is_cron_enabled(), "interval_seconds": CRON_INTERVAL_SECONDS}


@router.get("/cron-refresh-logs")
def get_cron_refresh_logs(limit: int = 100):
    """Derniers logs d'exécution du cron (datetime, job, bars par asset/période JSON)."""
    from services.market_data.cron_refresh import get_cron_logs
    return {"logs": get_cron_logs(limit=min(limit, 200))}


@router.post("/cron-refresh-status")
def post_cron_refresh_status(
    body: dict,
    current_user: AdminUser = Depends(get_current_user),
):
    """Active ou desactive le cron Refresh Data."""
    from services.market_data.cron_refresh import set_cron_enabled
    enabled = body.get("enabled")
    if enabled is None:
        raise HTTPException(status_code=400, detail="enabled required")
    set_cron_enabled(bool(enabled))
    return {"enabled": bool(enabled)}


@router.post("/backfill-lag")
def post_backfill_lag(
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    1) Analyse des trous par asset/periode. 2) Telecharge uniquement les (asset, periode) avec trous ou retard.
    3) Relance l'analyse et renvoie trous restants (normalement 0).
    """
    return run_backfill_lag_logic(db)


@router.post("/instruments", response_model=InstrumentResponse, status_code=status.HTTP_201_CREATED)
def create_instrument(
    instrument: InstrumentCreate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new market data instrument"""
    # Check if symbol already exists
    existing = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.symbol == instrument.symbol
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Instrument with symbol '{instrument.symbol}' already exists"
        )
    
    # Create new instrument
    db_instrument = MarketDataInstrument(
        symbol=instrument.symbol,
        name=instrument.name,
        asset_class=instrument.asset_class,
        weekend_tradable="true" if instrument.weekend_tradable else "false",
        provider=instrument.provider or "binance",
        provider_symbol=instrument.provider_symbol or instrument.symbol,
        is_active="true" if instrument.is_active else "false",
    )
    
    db.add(db_instrument)
    db.commit()
    db.refresh(db_instrument)
    
    return {
        "id": db_instrument.id,
        "symbol": db_instrument.symbol,
        "name": db_instrument.name,
        "asset_class": db_instrument.asset_class,
        "weekend_tradable": db_instrument.weekend_tradable,
        "provider": db_instrument.provider,
        "provider_symbol": db_instrument.provider_symbol,
        "is_active": db_instrument.is_active,
        "created_at": db_instrument.created_at.isoformat() if db_instrument.created_at else None,
    }


@router.put("/instruments/{instrument_id}", response_model=InstrumentResponse)
def update_instrument(
    instrument_id: int,
    instrument_update: InstrumentUpdate,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing market data instrument"""
    db_instrument = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.id == instrument_id
    ).first()
    
    if not db_instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument with ID {instrument_id} not found"
        )
    
    # Update fields
    update_data = instrument_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        if key == "weekend_tradable" and value is not None:
            setattr(db_instrument, key, "true" if value else "false")
        elif key == "is_active" and value is not None:
            setattr(db_instrument, key, "true" if value else "false")
        else:
            setattr(db_instrument, key, value)
    
    db.commit()
    db.refresh(db_instrument)
    
    return {
        "id": db_instrument.id,
        "symbol": db_instrument.symbol,
        "name": db_instrument.name,
        "asset_class": db_instrument.asset_class,
        "weekend_tradable": db_instrument.weekend_tradable,
        "provider": db_instrument.provider,
        "provider_symbol": db_instrument.provider_symbol,
        "is_active": db_instrument.is_active,
        "created_at": db_instrument.created_at.isoformat() if db_instrument.created_at else None,
    }


@router.delete("/instruments/{instrument_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_instrument(
    instrument_id: int,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a market data instrument"""
    db_instrument = db.query(MarketDataInstrument).filter(
        MarketDataInstrument.id == instrument_id
    ).first()
    
    if not db_instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument with ID {instrument_id} not found"
        )
    
    db.delete(db_instrument)
    db.commit()
    return None


@router.get("/quotes/latest")
def get_latest_quotes(
    symbols: Optional[str] = None,
    instrument_ids: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get latest market quotes by provider symbols (e.g. BTCUSDT) or instrument IDs.
    At least one of symbols or instrument_ids must be provided."""
    if not symbols and not instrument_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'symbols' or 'instrument_ids' must be provided",
        )
    quotes = []
    seen_ids = set()
    if instrument_ids:
        id_strs = [s.strip() for s in instrument_ids.split(",") if s.strip()]
        ids = []
        for s in id_strs:
            try:
                ids.append(int(s))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid instrument_id: '{s}'",
                )
        if ids:
            for q in get_latest_quotes_by_instrument_ids(db, ids):
                if q.instrument_id not in seen_ids:
                    seen_ids.add(q.instrument_id)
                    quotes.append(q)
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        if sym_list:
            for q in get_latest_quotes_by_provider_symbols(db, sym_list):
                if q.instrument_id not in seen_ids:
                    seen_ids.add(q.instrument_id)
                    quotes.append(q)
    from services.market_data.fx import get_eurusdt_rate
    rate = float(get_eurusdt_rate(db, strict=False))
    return {"quotes": quotes_to_payload(quotes, eurusdt_rate=rate)}


@router.get("/market-summary")
def get_market_summary(
    symbols: Optional[str] = None,
    instrument_ids: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get market summary per instrument: price, 24h change (abs/pct), volume_24h, sparkline_24h.
    At least one of symbols or instrument_ids must be provided. If both, results are merged and deduplicated by instrument_id.
    Public (no auth) for dev / mobile client."""
    if not symbols and not instrument_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'symbols' or 'instrument_ids' must be provided",
        )
    ids: Optional[List[int]] = None
    if instrument_ids:
        id_strs = [s.strip() for s in instrument_ids.split(",") if s.strip()]
        ids = []
        for s in id_strs:
            try:
                ids.append(int(s))
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid instrument_id: '{s}'",
                )
    sym_list: Optional[List[str]] = None
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    summaries = get_market_summaries(db, instrument_ids=ids, provider_symbols=sym_list, include_eur=True)
    if summaries:
        id_list = [s["instrument_id"] for s in summaries]
        logo_rows = (
            db.query(MarketDataInstrument.id, MarketDataInstrument.logo_filename)
            .filter(MarketDataInstrument.id.in_(id_list))
            .all()
        )
        id_to_logo = {r.id: (f"{MEDIA_LOGO_PATH_PREFIX}{r.logo_filename}" if r.logo_filename else None) for r in logo_rows}
        for s in summaries:
            s["logo_url"] = id_to_logo.get(s["instrument_id"])
    return {"summaries": summaries}


@router.get("/all-crypto")
def get_all_crypto(db: Session = Depends(get_db)):
    """List all active crypto instruments with market summary (price, 24h change). Public for mobile."""
    instruments = (
        db.query(MarketDataInstrument)
        .filter(
            MarketDataInstrument.asset_class == "crypto",
            MarketDataInstrument.is_active == "true",
        )
        .order_by(MarketDataInstrument.symbol)
        .all()
    )
    if not instruments:
        return {"summaries": []}
    provider_symbols = [i.provider_symbol for i in instruments if i.provider_symbol]
    if not provider_symbols:
        return {"summaries": []}
    summaries = get_market_summaries(db, provider_symbols=provider_symbols, include_eur=True)
    id_to_inst = {i.id: i for i in instruments}
    result = []
    for rank, s in enumerate(summaries, start=1):
        inst = id_to_inst.get(s.get("instrument_id"))
        if not inst:
            continue
        logo_url = None
        if getattr(inst, "logo_filename", None):
            logo_url = f"{MEDIA_LOGO_PATH_PREFIX}{inst.logo_filename}"
        result.append({
            "instrument_id": s["instrument_id"],
            "symbol": inst.symbol,
            "name": (inst.name or inst.symbol or "").strip() or s.get("symbol", ""),
            "provider_symbol": s.get("symbol"),
            "price": s.get("price"),
            "price_eur": s.get("price_eur"),
            "change_24h_pct": s.get("change_24h_pct"),
            "change_24h_abs": s.get("change_24h_abs"),
            "market_cap_rank": rank,
            "logo_url": logo_url,
        })
    return {"summaries": result}


@router.get("/top-movers")
def get_top_movers_route(
    limit: int = 10,
    symbols: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Top gainers, losers, and volume over the last 24h. Optional symbols filter (provider symbols e.g. BTCUSDT).
    Public (no auth) for dev / mobile client."""
    if limit < 1 or limit > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be between 1 and 50",
        )
    sym_list: Optional[List[str]] = None
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    result = get_top_movers(db, limit=limit, provider_symbols=sym_list)
    all_summaries = (result.get("top_gainers") or []) + (result.get("top_losers") or []) + (result.get("top_volume") or [])
    if all_summaries:
        id_list = list({s["instrument_id"] for s in all_summaries})
        logo_rows = (
            db.query(MarketDataInstrument.id, MarketDataInstrument.logo_filename)
            .filter(MarketDataInstrument.id.in_(id_list))
            .all()
        )
        id_to_logo = {r.id: (f"{MEDIA_LOGO_PATH_PREFIX}{r.logo_filename}" if r.logo_filename else None) for r in logo_rows}
        for s in all_summaries:
            s["logo_url"] = id_to_logo.get(s["instrument_id"])
    return result


@router.get("/candles/1m")
def get_candles_1m(
    symbol: Optional[str] = None,
    instrument_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 500,
    db: Session = Depends(get_db),
):
    """Get 1m candles by symbol or instrument_id. Public (no auth)."""
    from datetime import datetime

    if not symbol and instrument_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'symbol' or 'instrument_id' must be provided",
        )
    if symbol and instrument_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'symbol' or 'instrument_id', not both",
        )
    limit = max(1, min(limit, 500))
    start_dt = None
    end_dt = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid start_time format")
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid end_time format")

    resolved_instrument_id = instrument_id
    provider_symbol = symbol
    if symbol:
        inst = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == symbol.strip().upper())
            .first()
        )
        if not inst:
            return {"candles": []}
        resolved_instrument_id = inst.id
        provider_symbol = inst.provider_symbol or symbol
    else:
        inst = db.query(MarketDataInstrument).filter(MarketDataInstrument.id == instrument_id).first()
        if not inst:
            return {"candles": []}
        provider_symbol = inst.provider_symbol or ""

    bars = get_bars_1m(
        db,
        resolved_instrument_id,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    candles = [
        {
            "instrument_id": b.instrument_id,
            "symbol": provider_symbol,
            "open_time": b.open_time.isoformat() if b.open_time else None,
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        }
        for b in bars
    ]
    return {"candles": candles}


@router.get("/candles/5m")
def get_candles_5m(
    symbol: Optional[str] = None,
    instrument_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 300,
    db: Session = Depends(get_db),
):
    """Get 5m candles by symbol (provider symbol e.g. BTCUSDT) or instrument_id.
    At least one of symbol or instrument_id must be provided.
    Public (no auth) for mobile / asset detail chart."""
    from datetime import datetime

    if not symbol and instrument_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'symbol' or 'instrument_id' must be provided",
        )
    if symbol and instrument_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'symbol' or 'instrument_id', not both",
        )
    limit = max(1, min(limit, 500))
    start_dt = None
    end_dt = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_time format (use ISO 8601)",
            )
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_time format (use ISO 8601)",
            )

    resolved_instrument_id = instrument_id
    provider_symbol = symbol
    if symbol:
        inst = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == symbol.strip().upper())
            .first()
        )
        if not inst:
            return {"candles": []}
        resolved_instrument_id = inst.id
        provider_symbol = inst.provider_symbol or symbol
    else:
        inst = db.query(MarketDataInstrument).filter(MarketDataInstrument.id == instrument_id).first()
        if not inst:
            return {"candles": []}
        provider_symbol = inst.provider_symbol or ""

    bars = get_bars_5m(
        db,
        resolved_instrument_id,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    candles = [
        {
            "instrument_id": b.instrument_id,
            "symbol": provider_symbol,
            "open_time": b.open_time.isoformat() if b.open_time else None,
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        }
        for b in bars
    ]
    return {"candles": candles}


@router.get("/candles/1h")
def get_candles_1h(
    symbol: Optional[str] = None,
    instrument_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 300,
    db: Session = Depends(get_db),
):
    """Get 1h candles by symbol (provider symbol e.g. BTCUSDT) or instrument_id.
    At least one of symbol or instrument_id must be provided.
    Public (no auth) for mobile / asset detail chart."""
    from datetime import datetime

    if not symbol and instrument_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'symbol' or 'instrument_id' must be provided",
        )
    if symbol and instrument_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'symbol' or 'instrument_id', not both",
        )
    limit = max(1, min(limit, 500))
    start_dt = None
    end_dt = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_time format (use ISO 8601)",
            )
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_time format (use ISO 8601)",
            )

    resolved_instrument_id = instrument_id
    provider_symbol = symbol
    if symbol:
        inst = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == symbol.strip().upper())
            .first()
        )
        if not inst:
            return {"candles": []}
        resolved_instrument_id = inst.id
        provider_symbol = inst.provider_symbol or symbol
    else:
        inst = db.query(MarketDataInstrument).filter(MarketDataInstrument.id == instrument_id).first()
        if not inst:
            return {"candles": []}
        provider_symbol = inst.provider_symbol or ""

    bars = get_bars_1h(
        db,
        resolved_instrument_id,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    candles = [
        {
            "instrument_id": b.instrument_id,
            "symbol": provider_symbol,
            "open_time": b.open_time.isoformat() if b.open_time else None,
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        }
        for b in bars
    ]
    return {"candles": candles}


@router.get("/candles/4h")
def get_candles_4h(
    symbol: Optional[str] = None,
    instrument_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 300,
    db: Session = Depends(get_db),
):
    """Get 4h candles by symbol (provider symbol e.g. BTCUSDT) or instrument_id.
    At least one of symbol or instrument_id must be provided.
    Public (no auth) for mobile / asset detail chart."""
    from datetime import datetime

    if not symbol and instrument_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'symbol' or 'instrument_id' must be provided",
        )
    if symbol and instrument_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'symbol' or 'instrument_id', not both",
        )
    limit = max(1, min(limit, 500))
    start_dt = None
    end_dt = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_time format (use ISO 8601)",
            )
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_time format (use ISO 8601)",
            )

    resolved_instrument_id = instrument_id
    provider_symbol = symbol
    if symbol:
        inst = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == symbol.strip().upper())
            .first()
        )
        if not inst:
            return {"candles": []}
        resolved_instrument_id = inst.id
        provider_symbol = inst.provider_symbol or symbol
    else:
        inst = db.query(MarketDataInstrument).filter(MarketDataInstrument.id == instrument_id).first()
        if not inst:
            return {"candles": []}
        provider_symbol = inst.provider_symbol or ""

    bars = get_bars_4h(
        db,
        resolved_instrument_id,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    candles = [
        {
            "instrument_id": b.instrument_id,
            "symbol": provider_symbol,
            "open_time": b.open_time.isoformat() if b.open_time else None,
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        }
        for b in bars
    ]
    return {"candles": candles}


@router.get("/candles/1d")
def get_candles_1d(
    symbol: Optional[str] = None,
    instrument_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 300,
    db: Session = Depends(get_db),
):
    """Get 1d candles by symbol (provider symbol e.g. BTCUSDT) or instrument_id.
    At least one of symbol or instrument_id must be provided.
    Public (no auth) for mobile / asset detail chart."""
    from datetime import datetime

    if not symbol and instrument_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'symbol' or 'instrument_id' must be provided",
        )
    if symbol and instrument_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'symbol' or 'instrument_id', not both",
        )
    limit = max(1, min(limit, 500))
    start_dt = None
    end_dt = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_time format (use ISO 8601)",
            )
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_time format (use ISO 8601)",
            )

    resolved_instrument_id = instrument_id
    provider_symbol = symbol
    if symbol:
        inst = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == symbol.strip().upper())
            .first()
        )
        if not inst:
            return {"candles": []}
        resolved_instrument_id = inst.id
        provider_symbol = inst.provider_symbol or symbol
    else:
        inst = db.query(MarketDataInstrument).filter(MarketDataInstrument.id == instrument_id).first()
        if not inst:
            return {"candles": []}
        provider_symbol = inst.provider_symbol or ""

    bars = get_bars_1d(
        db,
        resolved_instrument_id,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    candles = [
        {
            "instrument_id": b.instrument_id,
            "symbol": provider_symbol,
            "open_time": b.open_time.isoformat() if b.open_time else None,
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        }
        for b in bars
    ]
    return {"candles": candles}


@router.get("/candles/1w")
def get_candles_1w(
    symbol: Optional[str] = None,
    instrument_id: Optional[int] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    limit: int = 300,
    db: Session = Depends(get_db),
):
    """Get 1w candles by symbol (provider symbol e.g. BTCUSDT) or instrument_id.
    At least one of symbol or instrument_id must be provided.
    Public (no auth) for mobile / asset detail chart."""
    from datetime import datetime

    if not symbol and instrument_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one of 'symbol' or 'instrument_id' must be provided",
        )
    if symbol and instrument_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'symbol' or 'instrument_id', not both",
        )
    limit = max(1, min(limit, 500))
    start_dt = None
    end_dt = None
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_time format (use ISO 8601)",
            )
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_time format (use ISO 8601)",
            )

    resolved_instrument_id = instrument_id
    provider_symbol = symbol
    if symbol:
        inst = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == symbol.strip().upper())
            .first()
        )
        if not inst:
            return {"candles": []}
        resolved_instrument_id = inst.id
        provider_symbol = inst.provider_symbol or symbol
    else:
        inst = db.query(MarketDataInstrument).filter(MarketDataInstrument.id == instrument_id).first()
        if not inst:
            return {"candles": []}
        provider_symbol = inst.provider_symbol or ""

    bars = get_bars_1w(
        db,
        resolved_instrument_id,
        start_time=start_dt,
        end_time=end_dt,
        limit=limit,
    )
    candles = [
        {
            "instrument_id": b.instrument_id,
            "symbol": provider_symbol,
            "open_time": b.open_time.isoformat() if b.open_time else None,
            "open": float(b.open),
            "high": float(b.high),
            "low": float(b.low),
            "close": float(b.close),
            "volume": float(b.volume),
        }
        for b in bars
    ]
    return {"candles": candles}


@router.get("/chart-history")
def get_chart_history_endpoint(
    symbol: Optional[str] = None,
    instrument_id: Optional[int] = None,
    period: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Unified chart history for UI period selectors. Backend drives timeframe and date range.
    Query params: exactly one of symbol or instrument_id, and period (1j, 1s, 1m, 1a, 5a).
    Public (no auth) for mobile."""
    if not symbol and instrument_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exactly one of 'symbol' or 'instrument_id' must be provided",
        )
    if symbol and instrument_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'symbol' or 'instrument_id', not both",
        )
    if not period or period not in CHART_PERIODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid or missing 'period'. Allowed: {list(CHART_PERIODS)}",
        )
    payload = get_chart_history(
        db,
        symbol=symbol,
        instrument_id=instrument_id,
        period=period,
    )
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Instrument not found",
        )
    return payload


def _bar_open_time_to_date_str(open_time):
    """Safely convert bar open_time to ISO date string."""
    if open_time is None:
        return None
    try:
        if hasattr(open_time, "date"):
            d = open_time.date()
        else:
            d = open_time
        return d.isoformat() if d is not None else None
    except Exception:
        return None


@router.get("/instruments/{instrument_id}/bars")
def get_instrument_bars(
    instrument_id: int,
    start: Optional[str] = None,
    end: Optional[str] = None,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get historical bars for a specific instrument"""
    import logging
    from datetime import date, datetime

    logger = logging.getLogger(__name__)

    try:
        # Verify instrument exists
        instrument = db.query(MarketDataInstrument).filter(
            MarketDataInstrument.id == instrument_id
        ).first()

        if not instrument:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Instrument with ID {instrument_id} not found"
            )

        # Parse dates
        start_date = None
        end_date = None

        if start:
            try:
                start_date = datetime.strptime(start, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid start date format. Use YYYY-MM-DD"
                )

        if end:
            try:
                end_date = datetime.strptime(end, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid end date format. Use YYYY-MM-DD"
                )

        # Binance: use 1d candles (market_data_bars_1d); fallback: MarketDataBarD1
        if instrument.provider == "binance":
            from datetime import timezone
            start_dt = datetime(start_date.year, start_date.month, start_date.day, tzinfo=timezone.utc) if start_date else None
            end_dt = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc) if end_date else None
            bars_1d = get_bars_1d(db, instrument_id, start_time=start_dt, end_time=end_dt, limit=2000)
            bars_payload = []
            for b in bars_1d:
                date_str = _bar_open_time_to_date_str(getattr(b, "open_time", None))
                if not date_str:
                    continue
                try:
                    bars_payload.append({
                        "date": date_str,
                        "open": float(b.open),
                        "high": float(b.high),
                        "low": float(b.low),
                        "close": float(b.close),
                        "volume": int(float(b.volume)),
                    })
                except (TypeError, ValueError):
                    continue
            return {
                "instrument_id": instrument_id,
                "symbol": instrument.symbol,
                "bars": bars_payload,
                "count": len(bars_payload),
                "start_date": bars_payload[0]["date"] if bars_payload else None,
                "end_date": bars_payload[-1]["date"] if bars_payload else None,
            }

        # Fallback: MarketDataBarD1
        query = db.query(MarketDataBarD1).filter(
            MarketDataBarD1.instrument_id == instrument_id
        )
        if start_date:
            query = query.filter(MarketDataBarD1.date >= start_date)
        if end_date:
            query = query.filter(MarketDataBarD1.date <= end_date)
        bars = query.order_by(MarketDataBarD1.date).all()

        return {
            "instrument_id": instrument_id,
            "symbol": instrument.symbol,
            "bars": [
                {
                    "date": bar.date.isoformat(),
                    "open": float(bar.open),
                    "high": float(bar.high),
                    "low": float(bar.low),
                    "close": float(bar.close),
                    "volume": int(bar.volume),
                }
                for bar in bars
            ],
            "count": len(bars),
            "start_date": bars[0].date.isoformat() if bars else None,
            "end_date": bars[-1].date.isoformat() if bars else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_instrument_bars failed for instrument_id=%s: %s", instrument_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load bars: {e!s}",
        )
