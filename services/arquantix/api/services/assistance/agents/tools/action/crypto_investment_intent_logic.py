"""Logique déterministe — ``crypto_investment_intent`` (sans LLM).

Réutilise les mêmes agrégats que le flux invest (cash + positions) ; les
``resolved_id`` / soldes ne sont produits qu’ici ou via merge post-résolution."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Literal, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import MarketDataInstrument

_ASSET_ALIASES: dict[str, str] = {
    "bitcoin": "BTC",
    "btc": "BTC",
    "ethereum": "ETH",
    "eth": "ETH",
    "solana": "SOL",
    "sol": "SOL",
    "dogecoin": "DOGE",
    "doge": "DOGE",
    "xrp": "XRP",
    "ripple": "XRP",
    "usdc": "USDC",
    "eurc": "EURC",
    "usdt": "USDT",
    "tether": "USDT",
    "stablecoin": "USDC",
    "stablecoins": "USDC",
}


def _norm_short_symbol(raw: str) -> str:
    if not raw:
        return ""
    u = raw.strip().upper()
    for quote in ("USDT", "USDC", "BUSD", "USD"):
        if u.endswith(quote) and len(u) > len(quote):
            return u[: -len(quote)]
    return u


def _fmt_money(val: Any) -> str:
    try:
        d = Decimal(str(val))
        return f"{d:.2f}"
    except Exception:  # noqa: BLE001
        return "0.00"


def infer_target_candidate_symbol_for_crypto_intent(
    *,
    slots_fragment: Optional[dict[str, Any]],
) -> Optional[str]:
    """Symbole cible plausible avant résolution catalogue (pour détect conflits de brouillon)."""
    if not isinstance(slots_fragment, dict):
        return None
    sym = str(slots_fragment.get("symbol") or "").strip().upper()
    if sym:
        return sym
    return guess_symbol_from_raw(str(slots_fragment.get("raw") or ""))


def crypto_intent_target_asset_supersedes_active_draft(
    *,
    prev_slots: dict[str, Any],
    patch_slots: dict[str, Any],
) -> bool:
    """True si la fusion du patch avec l’état précédent mélangerait deux cibles distinctes."""

    pt = prev_slots.get("target_asset") if isinstance(prev_slots.get("target_asset"), dict) else {}
    nt = patch_slots.get("target_asset") if isinstance(patch_slots.get("target_asset"), dict) else {}

    prev_c = infer_target_candidate_symbol_for_crypto_intent(
        slots_fragment=pt if pt else None,
    )
    inc_c = infer_target_candidate_symbol_for_crypto_intent(
        slots_fragment=nt if nt else None,
    )
    if not inc_c:
        return False
    if not prev_c:
        return False
    return inc_c != prev_c


def guess_symbol_from_raw(raw: str) -> Optional[str]:
    """Heuristique légère sur texte libre (token + alias)."""
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip().lower()
    s = re.sub(r"\s+", " ", s)
    for token in re.findall(r"[a-zA-Z]{2,}", s):
        t = token.lower()
        if t in _ASSET_ALIASES:
            return _ASSET_ALIASES[t]
    return None


def _resolve_instrument_row(
    db: Session,
    *,
    raw_symbol: str,
    short_symbol: str,
) -> Optional[MarketDataInstrument]:
    candidates = {raw_symbol, short_symbol}
    if raw_symbol == short_symbol and raw_symbol:
        for quote in ("USDT", "USDC", "BUSD"):
            candidates.add(f"{raw_symbol}{quote}")
    candidates.discard("")
    if not candidates:
        return None
    return (
        db.query(MarketDataInstrument)
        .filter(
            or_(
                MarketDataInstrument.symbol.in_(candidates),
                MarketDataInstrument.provider_symbol.in_(candidates),
            ),
            MarketDataInstrument.is_active == "true",
            MarketDataInstrument.asset_class == "crypto",
        )
        .first()
    )


def resolve_market_instrument_for_intent(
    db: Session,
    *,
    raw_text: Optional[str],
    explicit_symbol: Optional[str] = None,
) -> tuple[Optional[MarketDataInstrument], str, list[str]]:
    """Résout l’instrument cible. Retourne (row, status, errors)."""
    sym_guess: Optional[str] = None
    if explicit_symbol and str(explicit_symbol).strip():
        sym_guess = str(explicit_symbol).strip().upper()
    else:
        sym_guess = guess_symbol_from_raw(raw_text or "")

    if not sym_guess:
        return None, "failed", ["target_asset_symbol_introuvable"]

    short = _norm_short_symbol(sym_guess)
    inst = _resolve_instrument_row(db, raw_symbol=sym_guess, short_symbol=short)
    if inst is None:
        return None, "failed", [f"instrument_introuvable:{sym_guess}"]

    return inst, "resolved", []


def instrument_resolved_id(inst: MarketDataInstrument) -> str:
    ps = (inst.provider_symbol or "").strip()
    if ps:
        return ps.lower().replace("/", "_").replace("-", "_")
    return inst.symbol.strip().lower()


def merge_slots_payload(
    existing: Optional[dict[str, Any]],
    patch: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Fusion profonde des sous-objets ``slots.*``."""

    def _merge(base: Any, incoming: Any) -> Any:
        if isinstance(base, dict) and isinstance(incoming, dict):
            out = dict(base)
            for k, v in incoming.items():
                if v is None:
                    continue
                if k in out:
                    out[k] = _merge(out.get(k), v)
                else:
                    out[k] = v
            return out
        return incoming if incoming is not None else base

    ex = dict(existing or {})
    inc = dict(patch or {})
    # racine peut contenir plusieurs clés ; on merge récursivement dicts
    return _merge(ex, inc)  # type: ignore[return-value]


def infer_stage_from_slots(slots: dict[str, Any]) -> str:
    ta = slots.get("target_asset") if isinstance(slots, dict) else {}
    src = slots.get("source_account") if isinstance(slots, dict) else {}
    amt = slots.get("amount") if isinstance(slots, dict) else {}
    if not isinstance(ta, dict):
        ta = {}
    if not isinstance(src, dict):
        src = {}
    if not isinstance(amt, dict):
        amt = {}

    has_target = bool(
        (str(ta.get("raw") or "").strip())
        or (str(ta.get("symbol") or "").strip()),
    )
    has_src = bool(str(src.get("raw") or "").strip())
    has_amt = (
        amt.get("value") is not None
        or bool(str(amt.get("raw") or "").strip())
        or bool(amt.get("use_all_available"))
    )
    if has_target and has_src and has_amt:
        return "draft_ready_for_backend_validation"
    return "draft_pending_slots"


def collect_invest_source_items(
    *,
    cash: dict[str, Any],
    crypto: dict[str, Any],
    buy_symbol_upper: Optional[str],
) -> list[dict[str, Any]]:
    """Liste des comptes sources (fiat + wallets) pour matching — pas de deep-link."""

    items: list[dict[str, Any]] = []
    ca = cash.get("cash_account") if isinstance(cash, dict) else None
    if isinstance(ca, dict) and ca.get("available_balance") is not None:
        bal = ca.get("available_balance")
        cur = str(ca.get("currency") or "EUR").upper()
        items.append(
            {
                "account_key": "fiat",
                "label": "Compte Euro",
                "balance": float(bal),
                "currency": cur,
                "source_kind": "fiat",
                "balance_display": _fmt_money(bal),
            },
        )

    positions = crypto.get("positions") if isinstance(crypto, dict) else None
    if isinstance(positions, list):
        for raw in positions:
            if not isinstance(raw, dict):
                continue
            asset = str(raw.get("asset") or "").strip().upper()
            if not asset:
                continue
            try:
                bal_f = float(raw.get("balance"))
            except (TypeError, ValueError):
                continue
            if bal_f <= 0:
                continue
            if buy_symbol_upper and asset == buy_symbol_upper:
                continue
            name = str(raw.get("name") or asset)
            items.append(
                {
                    "account_key": f"crypto:{asset}",
                    "label": f"Wallet {asset}",
                    "subtitle": name,
                    "balance": bal_f,
                    "currency": asset,
                    "source_kind": "crypto",
                    "balance_display": _fmt_money(bal_f),
                },
            )
    return items


def _eur_source_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for it in items:
        if str(it.get("source_kind") or "") == "fiat":
            out.append(it)
            continue
        cur = str(it.get("currency") or "").upper()
        lab = str(it.get("label") or "").lower()
        if cur == "EUR" or "euro" in lab:
            out.append(it)
    return out


def match_source_account(
    raw: Optional[str],
    items: list[dict[str, Any]],
    *,
    selected_option_id: Optional[str] = None,
) -> tuple[Optional[dict[str, Any]], str, list[str]]:
    """Match contrôlé ; ambiguïté explicite (ex. plusieurs EUR)."""
    if selected_option_id and str(selected_option_id).strip():
        oid = str(selected_option_id).strip()
        for it in items:
            if str(it.get("account_key") or "") == oid:
                return it, "resolved", []
        return None, "failed", ["source_account_option_id_inconnu"]

    if not raw or not str(raw).strip():
        return None, "skipped", []

    rl = str(raw).strip().lower()
    if not items:
        return None, "failed", ["source_accounts_indisponibles"]

    eur_tokens = (
        "€" in rl
        or "eur" in rl.split()
        or "euro" in rl
        or "euros" in rl
        or "compte euro" in rl
    )
    if eur_tokens:
        cands = _eur_source_rows(items)
        if len(cands) > 1:
            return None, "ambiguous", ["plusieurs_sources_eur_non_resolues"]
        if len(cands) == 1:
            it = cands[0]
            return it, "resolved", []

    # matching par symbole USDC / USDT / …
    for sym in ("USDC", "USDT", "EURC", "BTC", "ETH"):
        if sym.lower() in rl:
            matches = [
                it
                for it in items
                if str(it.get("currency") or "").upper() == sym
                or sym.lower() in str(it.get("label") or "").lower()
            ]
            if len(matches) > 1:
                return None, "ambiguous", [f"plusieurs_sources_{sym.lower()}"]
            if len(matches) == 1:
                return matches[0], "resolved", []

    # unique fiat fallback (un seul compte cash)
    fiat_only = [it for it in items if str(it.get("source_kind")) == "fiat"]
    if len(fiat_only) == 1 and ("compte" in rl or eur_tokens):
        return fiat_only[0], "resolved", []

    return None, "ambiguous", ["source_account_non_resolu"]


def clarification_backend_options_from_source_items(
    items: list[dict[str, Any]],
    *,
    restrict_to: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, str]]:
    """Options QCM backend : ``option_id`` = vérité métier (ex. ``account_key``)."""
    seq = restrict_to if restrict_to is not None else items
    opts: list[dict[str, str]] = []
    for it in seq:
        oid = str(it.get("account_key") or "").strip()
        if not oid:
            continue
        lab = (str(it.get("label") or oid).strip() or oid)[:256]
        opts.append({"option_id": oid, "label": lab})
    return opts


def clarification_reason_for_source_errors(errors: list[str]) -> str:
    if any("plusieurs_sources_eur" in e for e in errors):
        return "multiple_eur_sources"
    if any(e.startswith("plusieurs_sources_") for e in errors):
        return "multiple_matching_sources"
    if "source_account_option_id_inconnu" in errors:
        return "invalid_option_id"
    return "source_account_unclear"


def items_for_source_account_clarification(
    *,
    errors: list[str],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sous-ensemble pertinent à afficher en QCM après statut ``ambiguous``."""
    for e in errors:
        if "plusieurs_sources_eur" in e:
            return _eur_source_rows(items)
        if e.startswith("plusieurs_sources_"):
            tail = e.split("plusieurs_sources_", 1)[-1]
            sym = tail.upper()
            return [
                it
                for it in items
                if str(it.get("currency") or "").upper() == sym
                or sym.lower() in str(it.get("label") or "").lower()
            ]
    return list(items)


def infer_crypto_intent_confirmation_from_text(
    text: Optional[str],
) -> Literal["confirm", "decline", "unknown"]:
    """Interprétation déterministe courte (FR) — hors LLM."""
    if text is None or not str(text).strip():
        return "unknown"
    t = str(text).strip().lower()
    t_compact = re.sub(r"[\s`'’]+", " ", t)
    # Négations/excuses en premier (évite « oui mais non » trop naïf via fin de phrase).
    if re.search(
        r"\b(non|nan|nope|arr[êe]te|annul|abandon|refus|refuser|pas confir|incorrect)\b",
        t_compact,
    ):
        return "decline"
    if re.search(
        r"\b(oui|ok|okay|dac|d’accord|d accord|valide|valider|confirm|exact|"
        r"c[’']est bon|c est bon|go|vas[- ]?y|aller[- ]?y|parfait|"
        r"merci oui|accepted)\b",
        t_compact,
    ):
        return "confirm"
    return "unknown"


def build_confirmation_summary_fr(slots: dict[str, Any]) -> str:
    """Résumé court pour ``confirmation.summary`` (pas d’exécution)."""
    ta = slots.get("target_asset") if isinstance(slots.get("target_asset"), dict) else {}
    src = slots.get("source_account") if isinstance(slots.get("source_account"), dict) else {}
    amt = slots.get("amount") if isinstance(slots.get("amount"), dict) else {}
    assert isinstance(ta, dict) and isinstance(src, dict) and isinstance(amt, dict)
    tgt = ta.get("label") or ta.get("symbol") or ta.get("raw") or "cet actif"
    src_lab = src.get("label") or src.get("raw") or "votre compte source"
    if amt.get("use_all_available"):
        amt_s = "l’ensemble du disponible sur la source"
    elif amt.get("value") is not None:
        ccy = str(amt.get("currency") or "EUR").upper()
        amt_s = f"{amt.get('value')} {ccy}"
    else:
        amt_s = str(amt.get("raw") or "le montant mentionné")
    return (
        f"Si je comprends bien, vous souhaitez investir environ {amt_s} depuis "
        f"« {src_lab} » pour vous positionner sur {tgt}. C’est bien cela ? "
        f"Aucune exécution n’est réalisée depuis le chat."
    )


__all__ = [
    "build_confirmation_summary_fr",
    "clarification_backend_options_from_source_items",
    "clarification_reason_for_source_errors",
    "collect_invest_source_items",
    "crypto_intent_target_asset_supersedes_active_draft",
    "infer_crypto_intent_confirmation_from_text",
    "infer_stage_from_slots",
    "infer_target_candidate_symbol_for_crypto_intent",
    "instrument_resolved_id",
    "items_for_source_account_clarification",
    "match_source_account",
    "merge_slots_payload",
    "resolve_market_instrument_for_intent",
]
