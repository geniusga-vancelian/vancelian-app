#!/usr/bin/env bash
# Réparation compte prod gaelitier@gmail.com — swaps LI.FI puis phantoms ledger, puis ré-audit.
# Usage : ./scripts/arquantix-ecs-repair-gaelitier-account.sh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PERSON_ID="8b0e0044-f1ef-47a5-99d4-370598a77492"
EMAIL="gaelitier@gmail.com"

SWAP_IDS=(
  "b36d12dd-f94a-40cf-ae3f-54b4a5746acc"
  "2aba1f7e-bd6a-40dc-a6f9-fedfe7b79cbe"
  "da96fc53-1691-4abf-877d-24a70b899768"
  "78f04ce4-a607-4aaa-8f89-f5908ec243c3"
  "dffa9988-72a5-42af-88df-79ee9e00e003"
  "78866e37-a8f4-42f7-8619-7201810a7888"
  "17c057c7-51e1-4df7-a649-aea1adb74d68"
  "69f006cb-8666-4d34-8471-858177d3025e"
  "a98204ac-51bf-4d13-a3fa-765a0a8ee3dd"
)

SWAP_JSON=$(printf '%s\n' "${SWAP_IDS[@]}" | python3 -c 'import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))')

run_job() {
  local title="$1"
  local cmd="$2"
  echo ""
  echo "========== $title =========="
  "$ROOT_DIR/scripts/arquantix-ecs-run-job.sh" arquantix-api arquantix-api "$cmd"
}

# Phase 1 — réconciliation idempotente des swaps CONFIRMED incomplets
PHASE1_CMD=$(cat <<EOF
cd /app && python3 - <<'PYEOF'
import json
from uuid import UUID
import main  # noqa
from database import SessionLocal
from services.lifi.lifi_swap_reconciliation import settle_lifi_swap_idempotently

SWAP_IDS = ${SWAP_JSON}
PERSON_ID = UUID("${PERSON_ID}")

db = SessionLocal()
out = {"phase": "swap_settlement", "person_id": str(PERSON_ID), "results": []}
try:
    for sid in SWAP_IDS:
        swap = None
        try:
            from services.lifi.models import PersonWalletSwap
            swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == UUID(sid)).first()
            if swap and swap.person_id != PERSON_ID:
                out["results"].append({"swap_id": sid, "skipped": "wrong_person"})
                continue
            r = settle_lifi_swap_idempotently(db, UUID(sid), dry_run=False)
            out["results"].append({
                "swap_id": sid,
                "action": r.action,
                "debit_applied": r.debit_applied,
                "credit_applied": r.credit_applied,
                "cost_basis_applied": r.cost_basis_applied,
                "status_after": r.status_after,
            })
        except Exception as exc:
            out["results"].append({"swap_id": sid, "error": str(exc)[:800]})
    print(json.dumps(out, indent=2, default=str))
finally:
    db.close()
PYEOF
EOF
)
run_job "Phase 1 — swaps LI.FI (9)" "$PHASE1_CMD"

# Phase 2 — void phantoms sim/mock + replay webhooks (pas de correction bundle/collateral)
PHASE2_CMD=$(cat <<EOF
cd /app && python3 - <<'PYEOF'
import json
from uuid import UUID
import main  # noqa
from database import SessionLocal
from services.privy_wallet.ledger_phantom_repair import void_untrusted_ledger_entries, list_phantom_confirmed_deposits
from services.privy_wallet.reconciliation_service import run_person_wallet_reconciliation
from services.privy_wallet.repository import PersonWalletDepositRepository

PERSON_ID = UUID("${PERSON_ID}")

db = SessionLocal()
out = {"phase": "ledger_phantom_and_reconcile", "person_id": str(PERSON_ID)}
try:
    usdt_deps = []
    repo = PersonWalletDepositRepository()
    for row in repo.list_for_person(db, PERSON_ID, limit=5000):
        if str(row.asset or "").upper() != "USDT":
            continue
        if str(row.direction or "").lower() != "credit":
            continue
        if row.status != "confirmed":
            continue
        usdt_deps.append({
            "deposit_id": str(row.id),
            "amount": str(row.amount),
            "tx_hash": row.tx_hash,
            "idempotency_key": row.idempotency_key,
            "transaction_kind": row.transaction_kind,
        })
    out["usdt_credits"] = usdt_deps
    out["phantoms_detected"] = [
        {"deposit_id": str(p.deposit_id), "asset": p.asset, "amount": str(p.amount), "reason": p.reason, "tx_hash": p.tx_hash}
        for p in list_phantom_confirmed_deposits(db, person_id=PERSON_ID)
    ]
    void_actions = void_untrusted_ledger_entries(db, person_id=PERSON_ID, dry_run=False)
    out["void_actions"] = void_actions
    if void_actions:
        db.commit()
    summary = run_person_wallet_reconciliation(db, person_id=PERSON_ID, auto_heal=True)
    db.commit()
    out["reconciliation"] = {
        "status": summary.status,
        "matched": summary.matched_count,
        "healed": summary.healed_count,
        "ledger_ahead": summary.ledger_ahead_count,
        "mismatch": summary.mismatch_count,
        "unresolved": summary.unresolved_count,
        "message": summary.message,
    }
    print(json.dumps(out, indent=2, default=str))
finally:
    db.close()
PYEOF
EOF
)
run_job "Phase 2 — phantoms + réconciliation wallet" "$PHASE2_CMD"

# Phase 3 — ré-audit
"$ROOT_DIR/scripts/arquantix-ecs-audit-person-crypto.sh" "$EMAIL"

echo ""
echo "OK — réparation terminée. Voir logs CloudWatch /ecs/arquantix-api pour le JSON ré-audit."
