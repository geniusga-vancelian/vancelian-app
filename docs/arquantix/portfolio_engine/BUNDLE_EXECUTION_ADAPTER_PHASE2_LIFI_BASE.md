# PRD Phase 2 — Bundle LI.FI Base

**Statut:** Implémenté (backend)  
**Chaîne:** Base uniquement (`chain_id` 8453)  
**Actifs:** USDC, EURC, ETH, cbBTC (CBBTC en interne)

---

## Principes non négociables

1. **Aucun crédit `pe_position_atoms`** sur quote, prepare-sign ou submit non confirmé.
2. **Settlement Privy** (`apply_swap_settlement`) uniquement quand `PersonWalletSwap.status == CONFIRMED`.
3. **Atoms PE** uniquement après settlement Privy (`bundle_pe_atoms_applied` dans audit).
4. **Invariant G** en `dry_run` après chaque batch invest/rebalance/finalize — ne bloque pas.

---

## Activation

```bash
BUNDLE_EXECUTION_PROVIDER=lifi_base   # ou lifi
LIFI_SWAPS_ENABLED=1
LIFI_SWAPS_MOCK=1                     # dev local
BUNDLE_LIFI_SYNC_MOCK=1               # auto-submit mock dans invest (tests)
```

Funding EUR en mode LI.FI : routé vers **Exchange** pour la seule leg `funding` (hybride).  
Investissement LI.FI complet : **entry asset direct** (USDC/EURC) sur Base.

---

## Flux investissement

```text
POST /bundle/invest  (funding USDC, provider=lifi_base)
  → quotes LI.FI par leg allocation
  → status: pending_signature + swap_id / prepare payload par leg
  → PAS de cash leg / spot atoms

POST /bundle/leg/{swap_id}/prepare-sign
  → transaction Privy à signer

POST /bundle/leg/{swap_id}/submit-tx  { tx_hash }
  → submit → CONFIRMED → settlement Privy → spot atom

POST /bundle/batch/finalize
  → crédit cash leg résiduel + invariant G
```

---

## Modules

| Module | Rôle |
|--------|------|
| `lifi_base_config.py` | Whitelist Base 4 actifs |
| `bundle_lifi_validation.py` | Validation montants / chaîne |
| `bundle_lifi_leg_service.py` | Quote, execute pending, submit, settlement |
| `lifi_provider.py` | `ExecutionProvider` |
| `pe_settlement.py` | Atoms après confirmation |
| `bundle_lifi_api.py` | Rebuild `ExecutionLeg` depuis swap audit |

---

## Rebalance

Même pattern : `execute_rebalance` peut retourner legs `pending` ; submit-tx par swap ; atoms via `pe_settlement` pour sell/buy.

---

## Limites Phase 2

- Pas de reserved balances (Phase 4).
- Finalize batch manuel (client doit appeler finalize).
- cbBTC : symbole PE `BTC` mappé → `CBBTC` pour LI.FI.
- Non-régression Docker / Flutter : à valider avec `LIFI_SWAPS_MOCK=1`.

---

## Prochaines étapes

- Phase 3 : job réconciliation invariant G + alertes.
- Phase 4 : reserved balances + mutex rebalance.
- Flutter : boucle prepare-sign / submit par leg pending.
