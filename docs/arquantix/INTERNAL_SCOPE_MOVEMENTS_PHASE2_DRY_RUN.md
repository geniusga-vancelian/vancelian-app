# Internal Scope Movements — Phase 2 dry-run

**Date :** 2026-05-30  
**Statut :** implémenté (read-only) — **aucune mutation PE / soldes**  
**Spec parente :** [INTERNAL_SCOPE_MOVEMENTS_ACCOUNTING_SPEC.md](./INTERNAL_SCOPE_MOVEMENTS_ACCOUNTING_SPEC.md)

---

## Objectif

Préparer le moteur `internal_scope_movements` en **calcul théorique** :

- lire le legacy (OVT, audit bundle, UVP)
- dériver les mouvements de scope attendus
- comparer au PE actuel
- détecter gaps et risques de double comptage

**Aucune écriture** sur `pe_position_atoms`, `pe_ledger_entries`, Privy, bundle funding.

---

## Module

```
services/arquantix/api/services/portfolio_engine/internal_scope_movements/
├── __init__.py
├── enums.py          # InternalScope, InternalMovementType
├── types.py          # ScopeMovement, snapshots, gaps
├── utils.py          # parsing OVT, metadata Lombard
├── vault.py          # compute_expected_vault_scope_movements
├── lombard.py        # compute_expected_lombard_scope_movements
├── bundle.py         # compute_expected_bundle_scope_movements
├── pe_reader.py      # read_current_pe_scope_snapshot
├── compare.py        # compare_expected_scopes_vs_current_pe
└── audit.py          # build_internal_scope_audit_report
```

---

## CLI

Depuis `services/arquantix/api` :

```bash
python3 -m scripts.internal_scope_movements_audit \
  --dry-run \
  --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492
```

Exit code :

- `0` — aucun gap bloquant détecté
- `1` — au moins un gap scope PE vs legacy attendu

---

## Exemple de rapport (structure)

```json
{
  "ready": true,
  "mode": "dry_run_read_only",
  "legacy_source_of_truth": true,
  "pe_atoms_mutated": false,
  "person_id": "8b0e0044-f1ef-47a5-99d4-370598a77492",
  "current_pe": {
    "trading_available": { "USDC": "90.0", "CBBTC": "0.5" },
    "trading_locked_collateral": {},
    "bundle_cash": { "USDC": "0" },
    "bundle_position": { "BTC": "0.001" },
    "vault_position": {},
    "liability": {}
  },
  "expected_from_legacy": {
    "vault_position": { "USDC": "20.0" },
    "trading_locked_collateral": { "CBBTC": "0.1" },
    "liability": { "USDC": "500.0" },
    "trading_available_net_from_legacy": {
      "USDC": "-20.0",
      "CBBTC": "-0.1"
    }
  },
  "legacy_user_vault_positions": { "USDC": "20.0" },
  "vault_movements": {
    "movement_count": 2,
    "movements": [
      {
        "movement_type": "fund",
        "source_scope": "trading_available",
        "destination_scope": "vault_position",
        "asset": "USDC",
        "quantity": "10",
        "reference_id": "cmpsucc910007ad015lhto6ye",
        "source_system": "onchain_vault_transactions"
      }
    ]
  },
  "lombard_movements": { "movement_count": 2 },
  "bundle_movements": { "movement_count": 3 },
  "gaps": [
    {
      "gap_type": "vault_position_not_in_pe",
      "asset": "USDC",
      "expected_scope": "vault_position",
      "expected_quantity": "20",
      "current_quantity": "0",
      "metadata": { "user_vault_positions": "20" }
    }
  ],
  "double_counting_risks": [
    {
      "risk_type": "vault_legacy_without_pe_scope",
      "asset": "USDC",
      "message": "OVT/UVP indique 20 USDC en vault mais aucun atom PE vault_position; trading_available PE peut surévaluer la liquidité."
    }
  ],
  "summary": {
    "gap_count": 3,
    "double_counting_risk_count": 1,
    "vault_movement_count": 2,
    "lombard_movement_count": 2,
    "bundle_movement_count": 3
  }
}
```

---

## Interprétation

| Section | Signification |
|---------|---------------|
| `current_pe.trading_available` | Atoms SPOT `direct_portfolio` aujourd’hui |
| `expected_from_legacy.vault_position` | Net OVT Morpho/Ledgity deposit − withdraw |
| `expected_from_legacy.trading_locked_collateral` | Net collateral Lombard open_loan |
| `gaps` | Ce que le moteur **aurait dû** écrire en PE mais n’existe pas |
| `double_counting_risks` | Patrimoine Trading potentiellement gonflé (UVP vault sans débit PE) |

---

## Tests

```bash
cd services/arquantix/api
python3 -m pytest tests/test_internal_scope_movements_dry_run.py -q
```

Couverture :

- Vault deposit → `trading_available −10` / `vault_position +10`
- Vault withdraw → net inverse
- Lombard lock → `available −` / `locked +`
- Lombard borrow → `USDC available +` / `liability +`
- Bundle fund → lecture audit sans `db.add` / `db.commit` du module
- Compare → gap vault quand PE n’a pas de scope vault

---

## Prochaine phase (hors scope Phase 2)

Phase 3 — implémentation PE atoms via `internal_scope_movements` writer (idempotent, wrapper bundle, hooks OVT confirm) — **uniquement après validation des rapports dry-run prod.**

---

*Aucune migration. Aucun repair. Legacy reste source of truth.*
