# ADR 007 — Swap Core + Settlement Router

| Champ | Valeur |
| --- | --- |
| **Statut** | **Accepté** |
| **Date** | 2026-06-10 |
| **Décideurs** | Équipe Arquantix / Vancelian |
| **Contexte** | Bundles V3 pilote · portefeuilles futurs (rebalance, dépôt, retrait, MiFID) |
| **Lié à** | ADR 004 (Ledger Authority) · ADR 001 (Intent) · [`BUNDLE_V3_TRADE_CHAIN_EXECUTION_ARCHITECTURE.md`](../BUNDLE_V3_TRADE_CHAIN_EXECUTION_ARCHITECTURE.md) |
| **Ne remplace pas** | ADR 004 — le Settlement Router **route** vers des handlers ; seuls les handlers Settlement Layer écrivent l’économique |

---

## 1. Problème

Aujourd’hui, le **rail LI.FI on-chain** est partiellement partagé (`PersonWalletSwap`, `LifiClient`, `LifiExecuteService`, `POST /swaps/confirm-execute`), mais le code expose **deux facades** :

| Couche | Standalone | Bundle (rebalance, allocation, retrait) |
| --- | --- | --- |
| Quote | `LifiQuoteService` | `BundleLifiQuoteService` |
| Exécution client | `confirmSwapWithRetry` | `executeBundleTrade` → **même** `confirmSwapWithRetry` |
| Settlement | `apply_swap_settlement` → ledger Privy (self-trading) | `try_settle_confirmed_bundle_swap` → `pe_settlement` (atoms bundle) |

**Risque** : renforcer le swap portail sans propager les correctifs au bundle (ou l’inverse). À mesure que les portefeuilles se diversifient, chaque produit risque de réimplémenter quote / poll / settle.

**Principe métier validé** : un swap est une **primitive unique** ; la seule variation légitime est **quel scope comptable** est impacté (self-trading, cash leg bundle, vault, etc.).

---

## 2. Décision

Introduire deux modules conceptuels — **obligatoires pour tout nouveau code swap** :

### 2.1 Swap Core (exécution LI.FI)

**Responsabilité** : tout ce qui est commun à un trade LI.FI, indépendamment du produit.

| In scope | Out of scope |
| --- | --- |
| Créer / mettre à jour `PersonWalletSwap` | Drift, plan rebalance, ordre sell/buy |
| Appeler `LifiClient.get_quote` | Écriture ledger / PE |
| Cycle `confirm-execute` → `prepare_execute` → submit → poll | Intent parent bundle |
| Expiration quote, slippage guard, audit swap | Choix du wallet comptable cible |

**Contrat cible** (API interne — nom indicatif) :

```python
SwapCore.quote(ctx: SwapContext) -> SwapQuoteResult
SwapCore.confirm_and_prepare(ctx, swap_id, review) -> SwapExecutePayload
SwapCore.submit(ctx, swap_id, signed_tx) -> None
SwapCore.poll_until_terminal(ctx, swap_id) -> SwapTerminalStatus
```

`SwapContext` porte au minimum : `person_id`, `from_asset`, `to_asset`, `amount`, `chain`, `signing_wallet`, **`settlement_scope`** (voir §2.2).

### 2.2 Settlement Router (écriture économique)

**Responsabilité** : après `PersonWalletSwap.status = CONFIRMED`, router vers le **handler Settlement Layer** selon le scope — seul point d’écriture économique (ADR 004).

| `settlement_scope` | Handler | Tables impactées |
| --- | --- | --- |
| `self_trading` | `LifiStandaloneSettlementHandler` (`settlement/lifi_ledger.py`, `lifi_swap_settlement.py`) | `person_wallet_deposits`, balances Privy |
| `bundle_portfolio` | `BundlePortfolioSettlementHandler` (`bundle_swap_pe_settlement.py`, `pe_settlement.py`) | `pe_position_atoms`, cash leg bundle |
| *futur* `vault`, `lombard`, … | Handler dédié | Scopes PE correspondants |

**Règle de routage** (aujourd’hui en prod) :

```text
is_bundle_internal_swap(swap) == True  → settlement_scope = bundle_portfolio
sinon                                  → settlement_scope = self_trading
```

Le tag audit `bundle_execution` + `bundle_action` (ex. `rebalance_buy`) **ne doit pas** être contourné — c’est le discriminant officiel.

---

## 3. Architecture cible

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ PRODUIT / PLANNER          │  rebalance · dépôt · swap portail · vault  │
│ (intelligence métier)      │  → produit des legs / intentions           │
└────────────────────────────┴────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ SWAP CORE                  │  1 PersonWalletSwap par trade atomique     │
│                            │  LI.FI quote · confirm · sign · poll       │
└────────────────────────────┴────────────────────────────────────────────┘
                                      │ CONFIRMED
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ SETTLEMENT ROUTER          │  settlement_scope → handler ADR 004      │
└────────────────────────────┴────────────────────────────────────────────┘
          │                                    │
          ▼                                    ▼
   self_trading ledger                  bundle PE atoms + cash leg
```

**Invariant I1** : N legs rebalance = N appels Swap Core — jamais un « mega-swap » bundle.

**Invariant I2** : Swap Core **ne touche jamais** `person_wallet_deposits` ni `pe_position_atoms`.

**Invariant I3** : Settlement Router **refuse** un swap `CONFIRMED` sans `settlement_scope` résolvable.

**Invariant I4** : Côté client web/mobile, **une seule primitive** `executeTrade` / `confirmSwapWithRetry` + `signAndSubmit` + `pollUntilTerminal` (aujourd’hui : `executeBundleTrade` = alias documenté).

---

## 4. État actuel vs cible (honest mapping)

| Brique | Aujourd’hui | Conforme ADR 007 ? |
| --- | --- | --- |
| Persistance swap | `PersonWalletSwap` unique | ✅ |
| LI.FI provider | `LifiClient` unique | ✅ |
| Execute / poll | `LifiExecuteService` | ✅ |
| Confirm client | `confirmSwapWithRetry` partagé | ✅ |
| Rebalance V3 legs | `BundleLifiLegService` → même swap row + `executeBundleTrade` | ✅ rail · ⚠️ quote via facade séparée |
| Routage settlement | `is_bundle_internal_swap` + fork handlers | ✅ principe · ⚠️ pas encore module `SettlementRouter` nommé |
| Quote unifiée | 2 services (`LifiQuoteService`, `BundleLifiQuoteService`) | ❌ à fusionner dans Swap Core |
| API Swap Core explicite | Absente (logique dispersée) | ❌ à extraire |

**Verdict** : la **doctrine** est déjà appliquée en prod V3 ; l’**encapsulation** (modules nommés, une entrée quote) reste à faire.

---

## 5. Modules code — référence

### Swap Core (à consolider)

| Rôle | Fichier actuel | Destination |
| --- | --- | --- |
| Quote standalone | `services/lifi/lifi_quote_service.py` | `services/swap_core/quote.py` |
| Quote bundle | `services/portfolio_engine/bundle_execution/bundle_lifi_quote_service.py` | délégué Swap Core + policy `BundleQuotePolicy` |
| Execute | `services/lifi/lifi_execute_service.py` | `services/swap_core/execute.py` |
| Confirm | `services/lifi/lifi_confirm_service.py` | `services/swap_core/confirm.py` |
| Repository | `services/lifi/swap_repository.py` | inchangé |
| Client web | `web/.../executeBundleTrade.ts`, `swapQuoteConfirm.ts` | alias `executeTrade` |

### Settlement Router (à formaliser)

| Rôle | Fichier actuel | Destination |
| --- | --- | --- |
| Route | logique dans `is_bundle_internal_swap` + appels dispersés | `services/settlement/router.py` |
| Handler self-trading | `settlement/lifi_ledger.py`, `lifi_swap_settlement.py` | `handlers/self_trading.py` |
| Handler bundle | `bundle_swap_pe_settlement.py`, `pe_settlement.py` | `handlers/bundle_portfolio.py` |
| Point d’appel unique | `try_settle_confirmed_bundle_swap`, `apply_swap_settlement` | `SettlementRouter.settle_confirmed_swap(swap)` |

### Planners (hors Swap Core — inchangés)

| Produit | Module |
| --- | --- |
| Rebalance V3 | `drift_engine.py`, `rebalance_planner.py`, `rebalance_executor.py` |
| Dépôt V3 | `deposit_service.py` → chaîne vers `execute_v3_bundle_rebalance` |
| Allocation legacy | `BundleOrchestrator` |

Les planners **produisent des `ExecutionLeg`** ; Swap Core **exécute** chaque leg.

---

## 6. Règles pour les PR (non négociables)

1. **Interdit** : nouveau chemin LI.FI hors `PersonWalletSwap` + Swap Core (pas de quote directe LI.FI dans un orchestrateur bundle).
2. **Interdit** : écriture PE ou ledger Privy dans `rebalance_executor`, `BundleLifiLegService.execute_leg`, ou routes HTTP — uniquement via Settlement Router après `CONFIRMED`.
3. **Interdit** : settlement standalone sur swap taggé `bundle_execution=true` (garde `validate_lifi_standalone_eligible`).
4. **Obligatoire** : tout nouveau type de portefeuille ajoute un **`settlement_scope`** + handler Settlement Layer — pas un 3ᵉ chemin ad hoc.
5. **Obligatoire** : tests d’idempotence settlement par scope (pattern `test_bundle_v3_swap_pe_settlement.py` + `test_lifi_swap_ledger_idempotency.py`).

---

## 7. Plan de migration (sans big-bang)

| Phase | Livrable | Régression |
| --- | --- | --- |
| **S0 (fait)** | V3 rebalance = chaîne de trades + `executeBundleTrade` + fork settlement bundle | Pilote Kings/Majors |
| **S1** | `SettlementRouter.settle_confirmed_swap(swap)` — wrapper autour des handlers existants | Aucun changement comportement |
| **S2** | `SwapCore.quote(ctx)` — `BundleLifiQuoteService` devient thin wrapper (policy Base/whitelist) | Tests parité quote bundle vs standalone |
| **S3** | Déplacer `LifiConfirmService` / poll dans Swap Core ; facades produit = appels uniquement | Flag OFF legacy inchangé |
| **S4** | Renommer web `executeBundleTrade` → `executeTrade` (alias déprécié) | UI seulement |
| **S5+** | Nouveaux scopes (`vault`, `lombard`) = nouveau handler router — **pas** nouveau rail LI.FI | Par produit |

**Pas de migration données** : `PersonWalletSwap` et tags audit restent la source de routage.

---

## 8. Relation avec les autres ADR

| ADR | Lien |
| --- | --- |
| **004** | Settlement Router **implémente** la règle « seul Settlement Layer écrit » |
| **001** | Intent pilote le cycle de vie produit ; Swap Core pilote l’exécution provider ; `linked_table=person_wallet_swaps` |
| **002** | Outbox pour transitions post-CONFIRMED (settle, reconcile) — pas pour chaque quote |
| **003** | Controller valide après settlement — quel que soit le scope |

---

## 9. Conséquences

### Positives

- Un correctif LI.FI (TTL, slippage, poll, Privy) profite à **tous** les produits.
- Nouveaux portefeuilles : planner + `settlement_scope` — pas réécrire LI.FI.
- Revue code simplifiée : « est-ce Swap Core ou Settlement Router ? »

### Négatives / coûts

- Refactor S1–S3 (~1–2 sprints) avant que la structure reflète pleinement l’ADR.
- `BundleLifiQuoteService` conserve des règles métier (whitelist Base) — à traiter comme **policy**, pas comme second moteur.

---

## 10. Critères de conformité (checklist reviewer)

- [ ] Le changement touche LI.FI → passe par Swap Core (ou issue de migration S1–S3 référencée)
- [ ] Écriture économique post-CONFIRMED → Settlement Router + handler scope explicite
- [ ] Pas de nouveau `apply_*_atoms` / `increment_balance` hors `services/settlement/`
- [ ] Swap bundle taggé `bundle_execution` dans audit
- [ ] Test idempotence settlement pour le scope concerné

---

*ADR 007 — verrouillage architecture swap plateforme · commit pilote `b9a26c28` (file globale user + V3 trade chain).*
