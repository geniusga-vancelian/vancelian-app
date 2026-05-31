# Internal Scope Movements — Phase 3A Vault Only

**Date :** 2026-05-31  
**Statut :** implémenté (code + tests) — **non branché prod, non déployé volontairement**  
**Prérequis :** [Phase 2 dry-run](./INTERNAL_SCOPE_MOVEMENTS_PHASE2_DRY_RUN.md) validé prod  
**Spec parente :** [INTERNAL_SCOPE_MOVEMENTS_ACCOUNTING_SPEC.md](./INTERNAL_SCOPE_MOVEMENTS_ACCOUNTING_SPEC.md)

---

## Objectif

Résoudre le **plus gros écart comptable visible** : les dépôts/retraits Vault Morpho/Ledgity sont exécutés on-chain et tracés (intents/attempts/OVT), mais le PE ne sait pas encore que des USDC ont quitté `trading_available` pour `vault_position`.

Phase 3A **uniquement Vault** — pas Lombard, pas Bundle wrapper, pas Cost Basis, pas Reconciliation Controller.

---

## Validation dry-run prod (rappel)

| Scope | Attendu legacy | PE actuel |
|-------|----------------|-----------|
| trading_available USDC | **-102** net | +182.11 |
| vault_position USDC | **+180** | 0 |
| liability / collateral | (Phase 3B) | 0 |

**Conclusion :** intents, attempts, traces et exécutions on-chain sont bons ; le patrimoine client est correctement **exécuté** mais pas encore **représenté** dans le PE.

---

## Architecture Phase 3A

```
OVT deposit/withdraw success (Morpho / Ledgity)
        │
        ▼  [futur — non branché prod]
vault_ovt_bridge.apply_vault_scope_movement_for_ovt()
        │
        ├── deposit  → fund_vault_from_self_trading()
        └── withdraw → release_vault_to_self_trading()
                │
                ▼
direct_portfolio SPOT (scope=trading_available)  −/+ amount
direct_portfolio SPOT (scope=vault_position)     +/− amount
pe_audit_events (idempotence linked_reference_id = OVT id)
Privy / person_wallet_balances                   = inchangé
```

### Parallèle Bundle (référence)

| Bundle | Vault Phase 3A |
|--------|----------------|
| `fund_bundle_cash_leg_from_self_trading` | `fund_vault_from_self_trading` |
| `release_bundle_cash_leg_to_self_trading` | `release_vault_to_self_trading` |
| `direct SPOT −` / `bundle CASH +` | `trading_available SPOT −` / `vault_position SPOT +` |
| `batch_id` idempotence | `linked_reference_id` = OVT id |
| `bundle.fund_cash_leg` audit | `vault.fund_from_self_trading` audit |

### Représentation PE

Contrainte DB : index unique `(portfolio_id, instrument_id)` pour les atoms `open` — **un seul atom ouvert par instrument et par portfolio**.

Comme le Bundle (`bundle_portfolio` + `direct_portfolio`), le Vault utilise un **`vault_portfolio`** dédié :

| Portfolio | PositionType | Scope logique |
|-----------|--------------|---------------|
| `direct_portfolio` | SPOT | `trading_available` |
| `vault_portfolio` | SPOT + metadata `vault_position` | `vault_position` |

Le lecteur Phase 2 (`pe_reader`) inclut désormais `vault_portfolio` dans `vault_position`.

### Idempotence

- Clé métier : `linked_reference_id` = `onchain_vault_transactions.id`
- Garde-fou : `pe_audit_events` avec `entity_type=onchain_vault_transactions`, `entity_id=ovt_id`, action `vault.fund_from_self_trading` ou `vault.release_to_self_trading`
- Rejeu safe : second appel → `{ skipped: true, reason: "already_applied" }`

### Cost basis

Transfert proportionnel trading → vault (PRU inchangé, doctrine Cost Basis V2) — même logique que `bundle_funding._cost_basis_for_direct_debit`.

---

## Fichiers impactés

| Fichier | Rôle |
|---------|------|
| `services/.../vault_execution/vault_funding.py` | **Cœur** — fund/release |
| `services/.../vault_execution/vault_ovt_bridge.py` | Bridge OVT → fund/release (non branché) |
| `services/.../vault_execution/__init__.py` | Exports publics |
| `scripts/vault_scope_backfill.py` | CLI migration dry-run / `--apply` local |
| `services/.../internal_scope_movements/pe_reader.py` | Lecture `vault_portfolio` → scope vault |

### Non modifiés (volontairement)

- `bundle_funding.py`, Lombard, Cost Basis, Reconciliation Controller
- `dual_write.py` / hooks OVT receipt (**intégration Phase 3A+1**)
- Projections UI Trading/Vault (**Phase 3A+2**)
- `sync_self_trading_atom_from_custody` / Invariant G (**Phase 3A+3** — soustraire vault du modèle custody)

---

## API

### `fund_vault_from_self_trading`

```python
fund_vault_from_self_trading(
    db,
    client_id=...,
    person_id=...,          # réservé hooks custody futurs
    asset="USDC",
    instrument_id=...,
    amount=Decimal("10"),
    linked_reference_id=ovt_id,   # idempotence
    integration_mode="direct_morpho",
    tx_hash="0x...",
)
```

Effet après dépôt 10 USDC :

- Trading : **-10 USDC** (transfert vers Vault)
- Vault : **+10 USDC** (réception depuis Trading)
- Patrimoine total USDC PE : **inchangé**

### `release_vault_to_self_trading`

Inverse pour OVT `withdraw` success.

---

## Tests

```bash
cd services/arquantix/api
python3 -m pytest tests/test_vault_scope_funding_phase3a.py -q
```

Couverture :

- fund 10 USDC → scopes trading/vault corrects
- release inverse
- patrimoine total USDC conservé
- idempotence OVT id
- insufficient trading → `VaultFundingError`

---

## Plan migration / backfill (dry-run)

### 1. Simulation person (read-only)

```bash
python3 -m scripts.vault_scope_backfill \
  --person-id 8b0e0044-f1ef-47a5-99d4-370598a77492
```

Liste les 15 OVT vault success prod et l'action `fund`/`release` qui serait appliquée.

### 2. Simulation OVT unique

```bash
python3 -m scripts.vault_scope_backfill \
  --person-id <uuid> \
  --ovt-id cmpl7qmrh0001ad014ro1niu3
```

### 3. Apply local uniquement (jamais prod sans feu vert)

```bash
python3 -m scripts.vault_scope_backfill \
  --person-id <uuid> \
  --ovt-id <ovt_id> \
  --apply
```

### 4. Séquence prod recommandée (future)

1. Déployer Phase 3A (code seul, hook désactivé)
2. Backfill historique OVT par person (--apply staging → prod contrôlé)
3. Brancher `vault_ovt_bridge` sur receipt OVT success (forward only)
4. Vérifier dry-run audit : gap vault_position → 0
5. Projections UI Trading (-10 Dépôt Morpho) + Savings (+10)

**Person prod Gael — backfill attendu :** net **+180 USDC** en `vault_position`, trading_available USDC **182.11 → ~2.11** (modèle interne cible ~-102 inclut aussi Lombard Phase 3B).

---

## Prochaines étapes (hors Phase 3A)

| Phase | Contenu |
|-------|---------|
| **3A+1** | Brancher hook OVT receipt (`dual_write_vault_step`) |
| **3A+2** | Projections historique Trading / Vault |
| **3A+3** | `expected_direct = privy − bundle_cash − vault_position` |
| **3B** | Lombard `trading_locked_collateral` + `liability` |

---

## Contraintes respectées

- Read-only prod : **aucun write prod lancé**
- Aucun déploiement Phase 3A dans cette livraison
- Lombard / Bundle / Cost Basis / Reconciliation : **non touchés**
