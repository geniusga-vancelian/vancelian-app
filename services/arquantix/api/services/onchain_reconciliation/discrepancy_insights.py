"""Insights ops — provenance probable, preuve on-chain, risque auto-fix (Phase 5A+)."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from services.onchain_indexer.models import RawOnChainEvent

CHAIN_EXPLORER_TX: dict[int, str] = {
    8453: "https://basescan.org/tx/{tx_hash}",
    1: "https://etherscan.io/tx/{tx_hash}",
}

# Seuils indicatifs (unités lisibles, pas atomiques).
_DUST_ETH = Decimal("0.05")
_SMALL_EURC = Decimal("5")


def _meta(row: Any) -> dict[str, Any]:
    m = getattr(row, "metadata_json", None)
    return m if isinstance(m, dict) else {}


def _dec(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def infer_likely_sources(
    *,
    discrepancy_type: str,
    layer: str,
    asset: str | None = None,
    db_amount: Any = None,
    onchain_amount: Any = None,
    metadata_json: dict[str, Any] | None = None,
) -> list[str]:
    dtype = (discrepancy_type or "").strip().lower()
    meta = metadata_json or {}
    asset_u = (asset or "").upper()
    db = _dec(db_amount)
    oc = _dec(onchain_amount)

    sources: list[str] = []

    if dtype == "admin_sim_deposit":
        sources.append("Mock / crédit admin_sim (simulate_deposit)")
        sources.append("Crédit ledger sans preuve on-chain attendue")
    elif dtype == "lombard_mock_privy_ledger_credit":
        sources.append("Crédit mock Lombard historique (metadata mock)")
    elif dtype == "swap_confirmed_without_settlement":
        sources.append("Swap LI.FI confirmé sans amount_actual / settlement bloqué")
    elif dtype == "onchain_event_without_db_ledger":
        sources.append("Transfert ERC20 indexé (raw_onchain_events) sans deposit ledger")
        sources.append("Webhook Privy manquant ou backfill deposit non fait")
    elif dtype == "db_ledger_without_onchain_proof":
        if meta.get("reason") == "simulated_or_admin_credit":
            sources.append("Dépôt DB sans receipt / preuve on-chain")
        else:
            sources.append("Entrée ledger (deposit) sans raw_onchain_event associé")
            sources.append("Webhook Privy manquant ou tx non encore indexée")
    elif dtype == "balance_ledger_vs_onchain":
        if db is not None and db == 0 and oc is not None and oc > 0:
            if asset_u == "ETH" and oc <= _DUST_ETH:
                sources.append("Dust / gas résiduel ou petit dépôt natif non crédité ledger")
            elif asset_u == "EURC":
                sources.append("Transfert on-chain direct (EURC) hors flux applicatif")
                sources.append("Funding externe ou bridge non réconcilié")
            elif asset_u == "USDC":
                sources.append("Swap / test wallet direct ou crédit on-chain non passé par deposit")
                sources.append("LI.FI settlement ou transfert ERC20 non backfillé")
            else:
                sources.append("Solde on-chain > ledger — funding ou indexation incomplète")
            sources.append("Missing Privy webhook / backfill deposit")
            sources.append("External funding possible")
        else:
            sources.append("Écart agrégé ledger table vs solde RPC (multi-causes possibles)")
    elif dtype == "pending_stale":
        sources.append("Opération en pending au-delà du seuil SLA")
    else:
        sources.append(f"Type {dtype} — revue manuelle")

    if layer == "lifi":
        sources.append("Couche swap LI.FI")
    elif layer == "lombard":
        sources.append("Couche vault Lombard")
    elif layer == "morpho":
        sources.append("Couche vault Morpho")

    # Dédupliquer en gardant l'ordre.
    seen: set[str] = set()
    out: list[str] = []
    for s in sources:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def infer_auto_fix_risk(
    *,
    discrepancy_type: str,
    severity: str = "P2",
    metadata_json: dict[str, Any] | None = None,
) -> dict[str, str]:
    dtype = (discrepancy_type or "").strip().lower()
    sev = (severity or "P2").upper()

    if dtype in ("admin_sim_deposit", "lombard_mock_privy_ledger_credit"):
        return {
            "level": "potential_double_credit_risk",
            "label": "Potential double credit risk",
            "detail": "Toute correction crédit doit être validée — risque de double comptabilisation.",
        }
    if dtype == "swap_confirmed_without_settlement":
        return {
            "level": "manual_review_required",
            "label": "Manual review required",
            "detail": "Settlement LI.FI exige amount_actual on-chain — pas d'apply automatique.",
        }
    if dtype == "onchain_event_without_db_ledger":
        return {
            "level": "manual_review_required",
            "label": "Manual review required",
            "detail": "Création deposit depuis raw event possible en 5B — vérifier idempotence tx/log.",
        }
    if dtype in ("db_ledger_without_onchain_proof", "no_matching_raw_onchain_event"):
        return {
            "level": "manual_review_required",
            "label": "Manual review required",
            "detail": "Lien deposit ↔ preuve on-chain à valider avant tout void.",
        }
    if dtype == "balance_ledger_vs_onchain":
        if sev == "P0":
            return {
                "level": "potential_double_credit_risk",
                "label": "Potential double credit risk",
                "detail": "Écart balance majeur — rebuild ou crédit auto interdits sans revue.",
            }
        return {
            "level": "safe_auto_link_possible",
            "label": "Safe auto-link possible",
            "detail": "Après preuve tx (raw event / Basescan) — lien deposit possible en 5B ; pas de crédit auto.",
        }
    return {
        "level": "manual_review_required",
        "label": "Manual review required",
        "detail": "Pas d'apply silencieux en Phase 5A.",
    }


def build_explorer_links(
    *,
    chain_id: int,
    tx_hash: str | None,
) -> dict[str, str | None]:
    if not tx_hash or not str(tx_hash).startswith("0x"):
        return {"tx_hash": None, "explorer_tx_url": None, "explorer_label": None}
    normalized = str(tx_hash).strip().lower()
    template = CHAIN_EXPLORER_TX.get(chain_id)
    url = template.format(tx_hash=normalized) if template else None
    label = "Basescan" if chain_id == 8453 else "Etherscan" if chain_id == 1 else "Explorer"
    return {
        "tx_hash": normalized,
        "explorer_tx_url": url,
        "explorer_label": label if url else None,
    }


def build_onchain_proof(
    db: Session,
    row: Any,
    *,
    raw_event: dict[str, Any] | None = None,
    chain_id_default: int = 8453,
) -> dict[str, Any]:
    meta = _meta(row)
    proof: dict[str, Any] = {
        "chain_id": meta.get("chain_id") or chain_id_default,
        "tx_hash": meta.get("tx_hash"),
        "log_index": meta.get("log_index"),
        "block_number": meta.get("block_number"),
        "candidate_events": [],
    }

    if raw_event:
        proof["chain_id"] = raw_event.get("chain_id") or proof["chain_id"]
        proof["tx_hash"] = raw_event.get("tx_hash") or proof["tx_hash"]
        proof["log_index"] = raw_event.get("log_index")
        proof["block_number"] = raw_event.get("block_number")
        proof["raw_onchain_event_id"] = raw_event.get("id")

    if not proof["tx_hash"] and getattr(row, "wallet_address", None) and getattr(row, "asset", None):
        candidates = (
            db.query(RawOnChainEvent)
            .filter(
                RawOnChainEvent.wallet_address == str(row.wallet_address).lower(),
                RawOnChainEvent.asset == str(row.asset).upper(),
                RawOnChainEvent.chain_id == int(proof["chain_id"]),
            )
            .order_by(RawOnChainEvent.parsed_at.desc())
            .limit(5)
            .all()
        )
        for ev in candidates:
            proof["candidate_events"].append(
                {
                    "id": str(ev.id),
                    "tx_hash": ev.tx_hash,
                    "log_index": ev.log_index,
                    "block_number": int(ev.block_number) if ev.block_number is not None else None,
                    "amount_raw": str(ev.amount_raw),
                }
            )
        if candidates and not proof["tx_hash"]:
            top = candidates[0]
            proof["tx_hash"] = top.tx_hash
            proof["log_index"] = top.log_index
            proof["block_number"] = int(top.block_number) if top.block_number is not None else None
            proof["inferred_from_latest_raw_event"] = True

    links = build_explorer_links(
        chain_id=int(proof["chain_id"]),
        tx_hash=proof.get("tx_hash"),
    )
    proof.update(links)
    return proof


def enrich_discrepancy_dict(
    db: Session,
    data: dict[str, Any],
    *,
    row: Any | None = None,
    raw_event: dict[str, Any] | None = None,
    include_proof: bool = False,
) -> dict[str, Any]:
    """Ajoute insights ops à un dict discrepancy (liste ou détail)."""
    likely = infer_likely_sources(
        discrepancy_type=data.get("discrepancy_type", ""),
        layer=data.get("layer", ""),
        asset=data.get("asset"),
        db_amount=data.get("db_amount"),
        onchain_amount=data.get("onchain_amount"),
        metadata_json=data.get("metadata_json"),
    )
    risk = infer_auto_fix_risk(
        discrepancy_type=data.get("discrepancy_type", ""),
        severity=data.get("severity", "P2"),
        metadata_json=data.get("metadata_json"),
    )
    out = {
        **data,
        "likely_sources": likely,
        "likely_source_summary": likely[0] if likely else None,
        "auto_fix_risk": risk,
    }
    if include_proof and row is not None:
        out["onchain_proof"] = build_onchain_proof(db, row, raw_event=raw_event)
    return out
