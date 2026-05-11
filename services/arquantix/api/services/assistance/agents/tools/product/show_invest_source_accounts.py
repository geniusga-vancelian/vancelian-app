"""Tool ``show_invest_source_accounts`` — agent **product**, autonomy **L0**.

Pilote CAL : liste des comptes / wallets utilisables comme **source**
d'un investissement (crypto spot, bundle crypto), alignée sur
``/api/app/cash`` + ``/api/app/crypto-positions`` (``TestClientService``).

Émet un embed ``invest_source_account_list`` : chaque ligne porte un
``deep_link`` vers ``vancelian://app/invest/...`` qui ouvre le flux
natif directement à l'étape **montant** (compte source présélectionné).

Phase 1 : aucune exécution transactionnelle côté assistance — navigation
Flutter uniquement. Un enregistrement ``assistance_action_drafts`` est
écrit pour audit / ``pending_action``.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import quote
from uuid import UUID

from services.assistance.action_drafts_repo import create_action_draft
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.portfolio_engine.clients.models import Client as PeClient
from services.portfolio_engine.products.catalog import CatalogService
from services.test_clients.service import TestClientService

logger = logging.getLogger(__name__)

_SVC = TestClientService()
_CATALOG = CatalogService()


def _coerce_uuid(value: Any) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None


def _fmt_money(val: Any) -> str:
    try:
        d = Decimal(str(val))
        return f"{d:.2f}"
    except Exception:  # noqa: BLE001
        return "0.00"


def _normalize_quote_currency(ccy: Optional[str]) -> Optional[str]:
    """Devise pour deep-link / brouillon (EUR/USD, …)."""
    if ccy is None or not str(ccy).strip():
        return None
    u = str(ccy).strip().upper()
    if u in {"EURO", "EUROS", "€"}:
        return "EUR"
    if u in {"$", "USD", "DOLLAR", "DOLLARS", "US DOLLAR"}:
        return "USD"
    return u[:16]


def _amount_ccy_query(*, amount: Optional[float], currency: Optional[str]) -> str:
    """Suffixe query `&amount=&ccy=` aligné sur ``show_invest_confirmation_draft``."""
    if amount is None:
        return ""
    try:
        af = float(amount)
    except (TypeError, ValueError):
        return ""
    if af <= 0:
        return ""
    ccy = _normalize_quote_currency(currency) or "EUR"
    amt = quote(f"{af:.8f}".rstrip("0").rstrip("."), safe="")
    ccy_q = quote(ccy, safe="")
    return f"&amount={amt}&ccy={ccy_q}"


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "show_invest_source_accounts",
        "description": (
            "Affiche dans le chat la liste des comptes (fiat + wallets crypto) "
            "depuis lesquels le client peut financer un investissement. "
            "À utiliser quand le client veut investir en crypto ou dans un "
            "bundle crypto — **après** avoir identifié la cible (symbole ou "
            "UUID produit). Chaque ligne est cliquable et mène au flux natif "
            "avec le compte source présélectionné. "
            "Ne invente pas de soldes : ils viennent des données agrégées serveur."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_kind": {
                    "type": "string",
                    "description": "Type de cible : crypto_buy | bundle.",
                    "enum": ["crypto_buy", "bundle"],
                },
                "target_id": {
                    "type": "string",
                    "description": (
                        "Identifiant cible : pour crypto_buy le SYMBOL (ex. BTC) ; "
                        "pour bundle l'UUID du produit crypto_bundle."
                    ),
                },
                "amount_from": {
                    "type": "number",
                    "description": (
                        "OPTIONNEL — montant que le client veut mobiliser depuis la "
                        "devise ``currency_from`` (ex. 1000 quand il dit « 1000 € »). "
                        "À transmettre dès que le montant est connu dans le tour."
                    ),
                },
                "currency_from": {
                    "type": "string",
                    "description": (
                        "OPTIONNEL — devise du montant (EUR, USD, …). Défaut implicite "
                        "EUR si le client cite des euros sans préciser."
                    ),
                },
            },
            "required": ["target_kind", "target_id"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "product",
}


def _allowed_crypto_assets_for_target(
    db, *, target_kind: str, target_id: str
) -> Optional[set[str]]:
    """Pour bundle : upper-set des entry assets autorisés ; sinon None (pas de filtre)."""
    if target_kind != "bundle":
        return None
    uid = _coerce_uuid(target_id)
    if uid is None:
        return set()
    for row in _CATALOG.get_public_catalog(db, product_type="crypto_bundle"):
        if str(row.id).lower() == str(uid).lower():
            return {a.strip().upper() for a in (row.entry_assets_allowed or []) if a}
    return set()


def execute(
    ctx: ToolContext,
    *,
    target_kind: str,
    target_id: str,
    amount_from: Optional[float] = None,
    currency_from: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    if not ctx.client_id:
        return {
            "ok": False,
            "error": "client_required",
            "message": "Connexion client requise pour lister les comptes sources.",
        }

    cid = _coerce_uuid(ctx.client_id)
    if cid is None:
        return {"ok": False, "error": "invalid_client_id"}

    client = ctx.db.get(PeClient, cid)
    if client is None:
        return {"ok": False, "error": "client_not_found"}

    tk = (target_kind or "").strip().lower()
    tid = (target_id or "").strip()
    if tk not in {"crypto_buy", "bundle"} or not tid:
        return {"ok": False, "error": "invalid_target"}

    buy_symbol_upper = tid.upper() if tk == "crypto_buy" else None

    try:
        cash = _SVC.get_cash_data(ctx.db, client=client)
        crypto = _SVC.get_crypto_positions(ctx.db, client=client)
    except Exception:  # noqa: BLE001
        logger.exception(
            "show_invest_source_accounts.bootstrap_error conv=%s", ctx.conversation_id
        )
        return {"ok": False, "error": "data_unavailable"}

    bundle_allowed = _allowed_crypto_assets_for_target(ctx.db, target_kind=tk, target_id=tid)

    items: list[dict[str, Any]] = []

    # Fiat (compte cash)
    ca = cash.get("cash_account") if isinstance(cash, dict) else None
    if isinstance(ca, dict) and ca.get("available_balance") is not None:
        bal = ca.get("available_balance")
        cur = str(ca.get("currency") or "EUR").upper()
        account_key = "fiat"
        dl = _build_deep_link(
            target_kind=tk,
            target_id=tid,
            account_key=account_key,
            amount_from=amount_from,
            currency_from=currency_from,
        )
        items.append(
            {
                "account_key": account_key,
                "label": "Compte Euro",
                "balance": float(bal),
                "currency": cur,
                "source_kind": "fiat",
                "balance_display": _fmt_money(bal),
                "deep_link": dl,
                "disabled": False,
            }
        )

    # Crypto positions
    positions = crypto.get("positions") if isinstance(crypto, dict) else None
    if isinstance(positions, list):
        for raw in positions:
            if not isinstance(raw, dict):
                continue
            asset = str(raw.get("asset") or "").strip().upper()
            if not asset:
                continue
            bal_raw = raw.get("balance")
            try:
                bal_f = float(bal_raw)
            except (TypeError, ValueError):
                continue
            if bal_f <= 0:
                continue
            if buy_symbol_upper and asset == buy_symbol_upper:
                continue
            if bundle_allowed is not None and len(bundle_allowed) > 0:
                if asset not in bundle_allowed:
                    continue

            account_key = f"crypto:{asset}"
            dl = _build_deep_link(
                target_kind=tk,
                target_id=tid,
                account_key=account_key,
                amount_from=amount_from,
                currency_from=currency_from,
            )
            name = str(raw.get("name") or asset)
            items.append(
                {
                    "account_key": account_key,
                    "label": f"Wallet {asset}",
                    "subtitle": name,
                    "balance": bal_f,
                    "currency": asset,
                    "source_kind": "crypto",
                    "balance_display": _fmt_money(bal_f),
                    "deep_link": dl,
                    "disabled": False,
                }
            )

    title = "Compte d'approvisionnement"
    if tk == "bundle":
        title = "Depuis quel compte investir ?"
    elif tk == "crypto_buy":
        title = f"Source pour acheter {buy_symbol_upper or tid}"

    action_type = "bundle_invest" if tk == "bundle" else "crypto_buy"
    draft_payload: dict[str, Any] = {
        "target_kind": tk,
        "target_id": tid,
        "stage": "source_list",
        "accounts_count": len(items),
    }
    try:
        if amount_from is not None:
            af = float(amount_from)
            if af > 0:
                draft_payload["amount_from"] = af
                draft_payload["currency_from"] = (
                    _normalize_quote_currency(currency_from) or "EUR"
                )
    except (TypeError, ValueError):
        pass

    draft_id: Optional[str] = None
    try:
        conv_uid = UUID(str(ctx.conversation_id))
        draft = create_action_draft(
            ctx.db,
            conversation_id=conv_uid,
            client_id=cid,
            action_type=action_type,
            payload=draft_payload,
        )
        draft_id = str(draft.id)
        for it in items:
            dl = it.get("deep_link")
            if not isinstance(dl, str) or not dl.strip():
                continue
            sep = "&" if "?" in dl else "?"
            it["deep_link"] = f"{dl}{sep}action_draft_id={quote(draft_id, safe='')}"
    except Exception:  # noqa: BLE001
        logger.exception(
            "show_invest_source_accounts.action_draft_persist_failed conv=%s",
            ctx.conversation_id,
        )

    embed: dict[str, Any] = {
        "type": "invest_source_account_list",
        "title": title,
        "target_kind": tk,
        "target_id": tid,
        "items": items,
        "disclaimer": (
            "Soldes indicatifs issus de ton portefeuille — vérifie avant de confirmer "
            "dans le flux de paiement."
        ),
    }
    if draft_id:
        embed["action_draft_id"] = draft_id
    ctx.embeds_to_emit.append(embed)

    return {
        "ok": True,
        "accounts_count": len(items),
        "target_kind": tk,
        "target_id": tid,
        "action_draft_id": draft_id,
        "message": (
            f"{len(items)} compte(s) source listé(s) ; la carte interactive est affichée."
        ),
    }


def _build_deep_link(
    *,
    target_kind: str,
    target_id: str,
    account_key: str,
    amount_from: Optional[float] = None,
    currency_from: Optional[str] = None,
) -> str:
    """Construit un deep-link Flutter whitelisté (resolver `invest/*`)."""
    ak = quote(account_key, safe="")
    amt_q = _amount_ccy_query(amount=amount_from, currency=currency_from)
    if target_kind == "bundle":
        bid = quote(str(target_id).strip(), safe="")
        return (
            f"vancelian://app/invest/bundle_amount?bundle_id={bid}&account_key={ak}"
            f"{amt_q}"
        )
    # crypto_buy
    sym = quote(str(target_id).strip().upper(), safe="")
    return (
        f"vancelian://app/invest/crypto_buy_amount?symbol={sym}&account_key={ak}"
        f"{amt_q}"
    )


__all__ = ["SPEC", "execute"]
