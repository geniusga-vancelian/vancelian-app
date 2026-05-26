# Bundle Execution Adapter — Phase 1 Report

**Date:** 2026-05-26  
**Statut:** Implémenté (exchange actif, LI.FI squelette désactivé)

---

## Objectif

Introduire une couche d’exécution unique entre les orchestrateurs bundle et les moteurs réels, **sans modifier** `crypto_positions`, le WAC global, ni les invariants Exchange A/B/C.

---

## Emplacement du module

Le PRD ciblait `portfolio_engine/execution/`, mais ce chemin héberge déjà le module **ExecutionInstruction** (couche ordres PE).

Pour éviter toute collision :

```text
services/arquantix/api/services/portfolio_engine/bundle_execution/
```

---

## Fichiers créés

| Fichier | Rôle |
|---------|------|
| `bundle_execution/__init__.py` | Exports publics |
| `bundle_execution/types.py` | `ExecutionLeg`, `ExecutionQuote`, `ExecutionResult` |
| `bundle_execution/config.py` | `BUNDLE_EXECUTION_PROVIDER` (défaut: `exchange`) |
| `bundle_execution/providers.py` | `ExecutionProvider` protocol + factory |
| `bundle_execution/exchange_provider.py` | Encapsule `ExchangeService.buy/swap` |
| `bundle_execution/lifi_provider.py` | Squelette — `NotImplementedError` |
| `bundle_execution/bundle_execution_adapter.py` | Point d’entrée orchestrateurs |
| `bundle_execution/order_tagging.py` | Metadata ordres enrichie |
| `invariants/invariant_g.py` | Invariant G dry-run |
| `docs/.../RESERVED_BALANCES_POLICY.md` | Cadrage Phase 4 |
| `tests/test_bundle_execution_adapter_phase1.py` | Tests Phase 1 |

## Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `bundles/orchestrator.py` | `BundleExecutionAdapter` pour funding + allocation |
| `bundles/rebalance.py` | Adapter pour legs rebalance sell/buy |

---

## Interface finale

```text
BundleOrchestrator / BundleRebalanceOrchestrator
        ↓
BundleExecutionAdapter.execute_leg(leg, actor)
        ↓
get_execution_provider()  # BUNDLE_EXECUTION_PROVIDER
        ├── ExchangeExecutionProvider  (actif)
        └── LifiExecutionProvider      (désactivé)
```

### Metadata ordres (enrichie)

Chaque ordre bundle taggé avec :

```json
{
  "portfolio_scope": "bundle",
  "portfolio_id": "<uuid>",
  "bundle_action": "funding|allocation|rebalance",
  "execution_provider": "exchange",
  "batch_id": "<uuid>",
  "leg_id": "<external_reference>",
  "bundle_id": "<portfolio_id>",
  "bundle_batch_id": "<batch_id>"
}
```

### Feature flag

| Variable | Valeurs | Défaut |
|----------|---------|--------|
| `BUNDLE_EXECUTION_PROVIDER` | `exchange`, `lifi_base` | `exchange` |

`lifi_base` lève `LifiExecutionProviderNotEnabledError` jusqu’à Phase 2.

---

## Comportement préservé

- Preview invest / rebalance : inchangé (toujours `ExchangeService.preview_*` dans orchestrateurs)
- Exécution : même backend Exchange, même flux cash leg, mêmes atoms
- APIs Flutter/Web : aucun changement de contrat HTTP

---

## Invariant G (squelette)

`check_invariant_g(db, client_id, dry_run=True)` :

- Compare `Σ pe_position_atoms` (direct + bundle spot) vs soldes Privy
- **Vaults non inclus** (pas encore modélisés en atoms)
- **reserved_pending** : Phase 4
- Ne bloque jamais les opérations en Phase 1

---

## Tests

```bash
cd services/arquantix/api
pytest tests/test_bundle_execution_adapter_phase1.py -q
pytest tests/test_bundle_orchestrator.py -q   # non-régression recommandée
```

Couverture Phase 1 :

- Provider par défaut = exchange
- LI.FI désactivé
- Délégation orchestrateur → adapter
- Tagging metadata
- Invariant G dry_run sans person_id

---

## Limites connues

1. Preview n’utilise pas encore `adapter.quote_leg` (parité stricte avec ancien preview Exchange).
2. Funding **direct entry asset** (sans appel Exchange) reste hors adapter — comportement identique.
3. LI.FI non branché ; pas de `pending` legs on-chain.
4. Invariant G ne inclut pas vaults ni `crypto_positions` legacy.
5. `locked_quantity` non exploité (voir `RESERVED_BALANCES_POLICY.md`).

---

## Prochaines étapes — Phase 2 (LI.FI Base)

1. Implémenter `LifiExecutionProvider.execute_leg` (quote → sign → submit → settle).
2. Settlement via `lifi_swap_settlement` **avant** crédit `pe_position_atoms`.
3. Activer pilote `BUNDLE_EXECUTION_PROVIDER=lifi_base` par feature flag client/environnement.
4. Étendre whitelist (`EURC`, wrapped BTC) + mapping instruments PE.
5. Brancher invariant G en monitoring (alertes, pas blocage) puis reserved balances.

---

## Principe respecté

> Phase 1 ne rend pas LI.FI live ; elle permet de remplacer Exchange par LI.FI **sans retoucher** les orchestrateurs.
