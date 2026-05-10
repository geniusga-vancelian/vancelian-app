"""Tool ``crypto_buy_start`` — liste des comptes source CAL + intake déterministe."""

from __future__ import annotations

import logging
from typing import Any, Optional

from uuid import UUID

from services.assistance.action_drafts_repo import (
    cancel_active_action_drafts,
    create_action_draft,
)
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.product import show_invest_source_accounts
from services.assistance.agents.tools.product.invest_confirmation_emit import (
    append_invest_confirmation_embed,
)
from services.assistance.agents.tools.shared.deterministic_intake import (
    extract_intake_signals,
    merge_crypto_buy_intake,
)

logger = logging.getLogger(__name__)

# IDs d’option QCM (= ``agent_hint`` renvoyé par Flutter au tap).
CRYPTO_BUY_LAUNCH_CONFIRM_HINTS: frozenset[str] = frozenset({"crypto_buy_confirm_launch"})
CRYPTO_BUY_LAUNCH_ABORT_HINTS: frozenset[str] = frozenset(
    {"crypto_buy_abort", "crypto_buy_cancel"}
)

# Compte fiat par défaut — aligné avec show_invest_source_accounts (cash EUR).
DEFAULT_SOURCE_ACCOUNT_KEY = "fiat"
DEFAULT_SOURCE_LABEL = "Compte Euro"

_CRYPTO_DISPLAY: dict[str, str] = {
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "XRP": "XRP",
    "DOGE": "Dogecoin",
    "USDC": "USDC",
    "EURC": "EURC",
    "USDT": "USDT",
}


def crypto_buy_destination_human(sym_u: str) -> str:
    return _CRYPTO_DISPLAY.get(str(sym_u or "").strip().upper(), sym_u)


def _norm_money_str(v: Optional[float]) -> str:
    if v is None:
        return ""
    try:
        return f"{float(v):,.2f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(v)


def _amounts_equivalent(a: Any, b: Any, *, tol: float = 0.01) -> bool:
    try:
        fa = float(a)
        fb = float(b)
    except (TypeError, ValueError):
        return False
    return abs(fa - fb) <= tol


def format_crypto_buy_launch_prompt(
    *,
    sym_u: str,
    amt: float,
    ccy_u: str,
    dest_human: str,
) -> str:
    """Résumé très court (< 240) pour la question « passer le trade »."""
    amt_s = _norm_money_str(amt)
    ccy_l = str(ccy_u or "EUR").upper()
    return (
        f"Récap : acheter environ {amt_s} {ccy_l} en {dest_human} ({sym_u}), "
        f"avec le « {DEFAULT_SOURCE_LABEL} ». Souhaites-tu lancer ce trade dans l’app "
        f"pour obtenir l’écran récap définitif (tu pourras encore valider ou "
        f"refuser ensuite) ?"
    )[:240]


def build_launch_trade_confirmation_interrupt_payload(
    ctx: ToolContext,
    *,
    sym_u: str,
    amt: float,
    ccy_norm: str,
    dest_human: str,
) -> Optional[dict[str, Any]]:
    """Crée le brouillon ``awaiting_launch_confirm`` + interrupt QCM suivant."""

    tk = ctx.client_id and ctx.conversation_id
    if not tk:
        return None

    try:
        conv_uid = UUID(str(ctx.conversation_id))
        client_uid = UUID(str(ctx.client_id))
    except (ValueError, AttributeError):
        logger.info("crypto_buy_start.launch_gate.bad_uuid conv=%s", ctx.conversation_id)
        return None

    try:
        create_action_draft(
            ctx.db,
            conversation_id=conv_uid,
            client_id=client_uid,
            action_type="crypto_buy",
            payload={
                "target_kind": "crypto_buy",
                "target_id": sym_u.upper().strip(),
                "amount_from": float(amt),
                "currency_from": str(ccy_norm or "EUR").strip().upper()[:16],
                "stage": "awaiting_launch_confirm",
                "account_key": DEFAULT_SOURCE_ACCOUNT_KEY,
                "source_label": DEFAULT_SOURCE_LABEL,
            },
        )
    except Exception:
        logger.exception(
            "crypto_buy_start.launch_gate.draft_failed conv=%s",
            ctx.conversation_id,
        )
        return None

    prompt = format_crypto_buy_launch_prompt(
        sym_u=sym_u,
        amt=amt,
        ccy_u=str(ccy_norm or "EUR").upper(),
        dest_human=dest_human,
    )
    out: dict[str, Any] = {
        "ok": True,
        "interrupt_with_question": True,
        "prompt": prompt.strip(),
        "options": [
            {
                "id": "crypto_buy_confirm_launch",
                "label": "Confirmer",
            },
            {
                "id": "crypto_buy_abort",
                "label": "Abandonner",
            },
        ],
        # Deux décisions fermées uniquement pour ce blocage précis CAL.
        "allow_freeform": False,
        "flow": "crypto_buy",
        "mode": "awaiting_launch_confirm",
        "message": (
            "QCM Récap envoyé au client avant l’affichage du widget investissement."
        ),
    }
    return out


def _snapshot_matches_merged_trade(
    pend: dict[str, Any],
    *,
    sym_u: str,
    amt: float,
    ccy_norm: Optional[str],
) -> bool:
    if str(pend.get("target_kind") or "").strip().lower() != "crypto_buy":
        return False
    pend_sym = str(pend.get("target_id") or "").strip().upper()
    if not pend_sym or pend_sym != sym_u.strip().upper():
        return False
    if not _amounts_equivalent(pend.get("amount_from"), amt):
        return False
    pc = pend.get("currency_from")
    pccy = str(pc).strip().upper() if isinstance(pc, str) and str(pc).strip() else None
    ccy_cmp = str(ccy_norm or "EUR").strip().upper()
    if pccy and pccy != ccy_cmp:
        return False
    return True


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "crypto_buy_start",
        "description": (
            "Démarre un achat spot crypto depuis l'assistant (**aucune exécution "
            "d'ordre** côté chat). "
            "Étapes côté serveur :\n\n"
            "• Quand montant **et** symbole sont disponibles après fusion — **d'abord** "
            "un récap courte question à boutons (« Confirmer » / « Abandonner ») ; "
            "au tap Confirmer, le **widget récap investing** apparait pour une "
            "validation finale dans l’app.\n\n"
            "• Si des infos manquent → liste des **comptes source** CAL."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": (
                        "Actif cible (BTC, ETH, …). Tu peux **l'omettre** si le "
                        "client vient de répondre seulement avec un montant mais que "
                        "**l'assistant précédent** cite déjà l'actif (Bitcoin, ETH…). "
                        "Le serveur peut fusionner l'historique."
                    ),
                },
                "amount_from": {
                    "type": "number",
                    "description": (
                        "Montant indiqué par le client lorsque présent dans l'appel."
                    ),
                },
                "currency_from": {
                    "type": "string",
                    "description": "Devise du montant (EUR, USD, …).",
                },
            },
            "required": [],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "action",
}


def execute(
    ctx: ToolContext,
    *,
    symbol: Optional[str] = None,
    amount_from: Optional[float] = None,
    currency_from: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    text_src = getattr(ctx, "intake_user_text", None) or ""
    signals = extract_intake_signals("crypto_buy", text_src)

    tool_amt = amount_from if amount_from is not None else _kwargs.get("amount_from")

    merged = merge_crypto_buy_intake(
        tool_symbol=symbol,
        tool_amount_from=tool_amt,
        tool_currency_from=currency_from,
        signals=signals,
        pending_action=getattr(ctx, "pending_action_snapshot", None),
        current_topic=getattr(ctx, "current_topic", None),
        recent_turns=getattr(ctx, "recent_turns_snapshot", None),
    )

    sym_u = (merged.get("symbol") or "").strip().upper()
    if not sym_u:
        logger.info(
            "crypto_buy_start missing_symbol conv=%s merge=%s",
            ctx.conversation_id,
            merged.get("merge_sources"),
        )
        return {
            "ok": False,
            "error": "symbol_required",
            "message": "Symbole crypto manquant après fusion intake.",
            "flow": "crypto_buy",
        }

    amt = merged.get("amount_from")
    if amt is not None:
        try:
            amt_f = float(amt)
            amt = amt_f
        except (TypeError, ValueError):
            amt = None

    ccy = merged.get("currency_from")
    ccy_norm = (
        str(ccy).strip().upper()[:16]
        if isinstance(ccy, str) and str(ccy).strip()
        else None
    )
    if amt is not None and not ccy_norm:
        ccy_norm = "EUR"

    pend_raw = getattr(ctx, "pending_action_snapshot", None)
    pend = pend_raw if isinstance(pend_raw, dict) else {}
    pend_stage = str(pend.get("stage") or "").strip().lower()
    uch = getattr(ctx, "user_choice_hint", None)
    hint_l = str(uch).strip().lower() if isinstance(uch, str) else ""

    dest_name = crypto_buy_destination_human(sym_u)

    snapshot_match = isinstance(pend, dict) and _snapshot_matches_merged_trade(
        pend, sym_u=sym_u, amt=float(amt or 0.0), ccy_norm=ccy_norm
    )
    amt_nonnull = amt is not None
    hints_union = CRYPTO_BUY_LAUNCH_CONFIRM_HINTS | CRYPTO_BUY_LAUNCH_ABORT_HINTS

    # ── Étapes « double validation » après fusion complète ─────────────
    if amt_nonnull and snapshot_match:
        if pend_stage == "awaiting_launch_confirm":
            if hint_l in CRYPTO_BUY_LAUNCH_ABORT_HINTS:
                try:
                    cancel_active_action_drafts(
                        ctx.db, conversation_id=UUID(str(ctx.conversation_id))
                    )
                except Exception:
                    logger.exception(
                        "crypto_buy_start.abort_supersede_failed conv=%s",
                        ctx.conversation_id,
                    )
                return {
                    "ok": True,
                    "flow": "crypto_buy",
                    "mode": "launch_trade_aborted",
                    "message": "D’accord — on n’ouvre pas l’écran d’investissement.",
                }

            # Tap « Confirmer » sur le premier QCM → encart CAL final compact.
            if hint_l in CRYPTO_BUY_LAUNCH_CONFIRM_HINTS:
                cf_res = append_invest_confirmation_embed(
                    ctx,
                    target_kind="crypto_buy",
                    target_id=sym_u,
                    amount=float(amt),
                    amount_currency=ccy_norm or "EUR",
                    account_key=DEFAULT_SOURCE_ACCOUNT_KEY,
                    source_label=DEFAULT_SOURCE_LABEL,
                    destination_label=f"Achat · {dest_name} ({sym_u})",
                    headline="Récapitulatif avant validation",
                    confirm_label="Continuer dans l'app",
                    intent_kind="crypto_buy",
                    compact=True,
                )
                logger.info(
                    "crypto_buy_start.confirm_compact_post_launch_qcm conv=%s "
                    "symbol=%s amount=%s ok=%s",
                    ctx.conversation_id,
                    sym_u,
                    amt,
                    bool(cf_res.get("ok")),
                )
                if not cf_res.get("ok"):
                    return {
                        "ok": False,
                        "error": cf_res.get("error", "confirmation_failed"),
                        "message": cf_res.get("error", ""),
                        "flow": "crypto_buy",
                    }
                draft_id = cf_res.get("action_draft_id")
                return {
                    "ok": True,
                    "flow": "crypto_buy",
                    "mode": "investment_confirmation_compact",
                    "target_kind": "crypto_buy",
                    "target_id": sym_u,
                    "accounts_count": 1,
                    "action_draft_id": draft_id,
                    "message": (
                        "Encart définitif affiché — le client poursuit dans l'écran "
                        "natif pour valider ou annuler encore une fois au besoin."
                    ),
                }

            # Brouillon d’intent en attente, pas de clic connu encore : évite
            # d’ignorer une question fermée précédente.
            if not hint_l or hint_l not in hints_union:
                return {
                    "ok": False,
                    "error": "awaiting_launch_confirm_prompt",
                    "flow": "crypto_buy",
                    "message": (
                        "Le dernier récap demandait encore un choix (« Confirmer » "
                        "ou « Abandonner ») avant l’affichage du widget d’investissement."
                    ),
                }

    # Brouillon d’investissement définitif (widget compact) déjà actif —
    # évite de recycler la QCM préalable.
    if amt_nonnull and pend_stage == "confirmation" and snapshot_match:
        return {
            "ok": False,
            "error": "invest_confirmation_widget_already_shown",
            "flow": "crypto_buy",
            "message": (
                "Le récap d’investissement est déjà prêt sous forme d’encart : "
                "le client poursuit depuis ce widget sans dupliquer l’intent."
            ),
        }

    # Pas encore montant ⇒ sélection sources.
    if not amt_nonnull:
        out = show_invest_source_accounts.execute(
            ctx,
            target_kind="crypto_buy",
            target_id=sym_u,
            amount_from=amt,
            currency_from=ccy_norm,
        )
        logger.info(
            "crypto_buy_start conv=%s symbol=%s amount=%s ccy=%s "
            "merge=%s signals=%s ok=%s mode=source_account_list",
            ctx.conversation_id,
            sym_u,
            amt,
            ccy_norm,
            merged.get("merge_sources"),
            signals.get("_signals"),
            bool(out.get("ok")),
        )
        return {**out, "flow": "crypto_buy", "mode": "source_account_list"}

    # Montant présent ⇒ premier palier CAL : QCM Récap puis widget au confirm.
    launch_payload = build_launch_trade_confirmation_interrupt_payload(
        ctx,
        sym_u=sym_u,
        amt=float(amt),
        ccy_norm=ccy_norm or "EUR",
        dest_human=dest_name,
    )
    if not launch_payload:
        return {
            "ok": False,
            "error": "launch_prompt_failed",
            "flow": "crypto_buy",
        }
    logger.info(
        "crypto_buy_start.awaiting_launch_qcm conv=%s symbol=%s amount=%s",
        ctx.conversation_id,
        sym_u,
        amt,
    )
    return launch_payload


__all__ = [
    "SPEC",
    "execute",
    "CRYPTO_BUY_LAUNCH_CONFIRM_HINTS",
    "CRYPTO_BUY_LAUNCH_ABORT_HINTS",
    "crypto_buy_destination_human",
    "format_crypto_buy_launch_prompt",
    "build_launch_trade_confirmation_interrupt_payload",
]
