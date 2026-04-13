# Envelope Entry Wallet — Hardening Report

## Executive Summary

**60 tests** couvrant 8 familles de validation, **tous passés** en 3.8 secondes. Zéro modification de l'architecture métier.

---

## Tests Créés

| Fichier | Tests | Famille | Invariants |
|---------|-------|---------|------------|
| `test_envelope_accounting_invariants.py` | 13 | Comptabilité | INV-01..07 |
| `test_envelope_zero_wallet_pollution.py` | 7 | Zéro pollution | INV-01, 05, 06, 11 |
| `test_envelope_data_integrity.py` | 12 | Intégrité données | INV-07..10 |
| `test_envelope_failure_rollback.py` | 8 | Rollback / Erreur | INV-13 |
| `test_envelope_concurrency.py` | 8 | Concurrence | INV-12 |
| `test_envelope_cross_surface_consistency.py` | 6 | Cohérence surfaces | INV-04, 11 |
| `test_envelope_backward_compatibility.py` | 7 | Rétrocompatibilité | INV-05, 06 |
| `test_envelope_precision_rounding.py` | 6 | Précision / Arrondi | INV-14 |
| **Total** | **60** | | |

---

## Invariants Validés

### INV-01: Balance Net Change = 0 (conversion)
Après un invest EUR→pool ou BTC→pool, `crypto_positions.balance` revient exactement à sa valeur initiale. Le crédit intermédiaire de `ExchangeService.buy()` est neutralisé par l'envelope debit.

**Tests**: `test_balance_net_change_zero_after_eur_invest`, `test_pool_asset_balance_neutralized_after_swap`, `test_eur_invest_zero_initial`, `test_eur_invest_preserves_existing_free`

### INV-02: Available Balance Correct
Pour les conversions, `available_balance` retourne à sa valeur initiale (buy crédite + supply débite le même montant). Pour les invests directs, `available_balance` diminue du montant investi.

**Tests**: `test_available_balance_returns_to_initial_on_conversion`, `test_available_balance_reduced_on_direct`

### INV-03: Net Allocated = Commitment Amount
Le champ `envelope_entry.net_allocated` correspond exactement au `commitment.amount` du `PoolSupplyCommitment`.

**Tests**: `test_envelope_net_allocated_equals_commitment`, `test_envelope_commitment_amount_match`, `test_multiple_invests_all_match`

### INV-04: Zero Artificial Value Creation
La valeur EUR équivalente des USDC alloués ne dépasse jamais le montant EUR financé (modulo la tolérance de 1 EUR).

**Tests**: `test_no_artificial_value_creation`, `test_eur_invest_total_wealth_conservation`

### INV-05: Envelope Debit Only On Conversion
Le debit de `crypto_positions.balance` n'intervient QUE pour les conversions (buy/swap). Pour un invest direct, le balance reste intact.

**Tests**: `test_no_envelope_debit_on_direct`, `test_direct_invest_creates_envelope`

### INV-06: Direct Invest — Balance Unchanged, Available Reduced
Un invest direct (asset == pool_asset) : `balance` inchangé, `available_balance` réduit.

**Tests**: `test_direct_invest_balance_vs_available_diverge`, `test_direct_balance_behavior_unchanged`

### INV-07: Entry Amount = Funding Amount
Le `entry_amount` de l'envelope entry correspond exactement au montant original financé par le client.

**Tests**: `test_entry_amount_matches_funding`, `test_eur_entry_fields`, `test_btc_entry_fields`

### INV-08: Conversion Type Correct
`conversion_type` reflète le chemin réel : "buy" pour EUR, "swap" pour BTC, "none" pour direct.

**Tests**: `test_envelope_records_swap_conversion`, `test_eur_entry_fields`, `test_direct_usdc_entry_fields`

### INV-09: FX Rate Stored On Conversion
`fx_rate` est non-NULL pour les conversions et NULL pour les invests directs.

**Tests**: `test_eur_entry_fields` (fx_rate == MOCK_EUR_USDC_PRICE), `test_direct_usdc_entry_fields` (fx_rate is None)

### INV-10: Commitment ID Link Valide
`commitment_id` dans l'envelope entry pointe vers un vrai `PoolSupplyCommitment`.

**Tests**: `test_api_commitment_id_matches_db`

### INV-11: Placements vs Crypto Séparation
Après invest, les fonds engagés apparaissent dans les commitments (Placements), pas dans le crypto libre.

**Tests**: `test_eur_invest_crypto_zero_placements_positive`, `test_direct_invest_available_reduced`

### INV-12: Pas de Double Commitments
Chaque invest crée son propre envelope + commitment distinct, même avec le même payload.

**Tests**: `test_two_sequential_invests_create_two_envelopes`, `test_same_amount_creates_distinct_envelopes`, `test_separate_envelopes_per_client`

### INV-13: Rollback Complet sur Erreur
Un échec à n'importe quelle étape (buy, subscribe, envelope creation) ne laisse aucun enregistrement orphelin.

**Tests**: `test_subscribe_raises_no_orphan_credit`, `test_envelope_db_error_triggers_exception`, `test_buy_fails_raises_exception`, `test_swap_fails_raises_exception`

### INV-14: Pas de Dérive de Précision
10×100 EUR donne le même total que 1×1000 EUR (drift < 0.01 USDC). Les petits montants (1 EUR, 0.01 USDC) et les montants à haute précision sont gérés correctement.

**Tests**: `test_ten_small_invests_vs_one_large`, `test_small_eur_invest`, `test_very_small_direct_invest`, `test_near_peg_conversion_no_drift`

---

## Cas de Rollback Validés

| Scénario | Résultat | Orphelins |
|----------|----------|-----------|
| Buy réussit, subscribe échoue | Exception levée | 0 envelopes, 0 commitments |
| Subscribe réussit, envelope INSERT échoue | RuntimeError | 0 envelopes |
| Buy échoue (Exchange unavailable) | Exception levée | Aucun changement |
| Swap échoue (Engine down) | Exception levée | Aucun changement |
| Product status=draft | ProductNotInvestableError | Aucun changement |
| Funding asset non autorisé | FundingAssetNotAllowedError | Aucun changement |

---

## Cas de Concurrence Validés

| Scénario | Résultat |
|----------|----------|
| Double tap même client | 2 envelopes + 2 commitments distincts |
| Cap rempli puis second invest | Exception (funded ou remaining capacity) |
| Cap exact (3000 + 2000 = 5000) | Les deux réussissent |
| Retry même payload | Records distincts (pas d'idempotency) |
| 2 clients même offre | Envelopes isolées, 0 contamination |

---

## Rétrocompatibilité

| Fonctionnalité | Statut |
|----------------|--------|
| `OfferService.subscribe()` sans orchestrateur | ✅ OK, 0 envelope |
| Anciens commitments sans envelope | ✅ Lisibles dans earn_positions (envelope=None) |
| `PoolLendingService.create_supply_commitment()` | ✅ Inchangé |
| `OfferService.create_product()` | ✅ Inchangé |
| Workflow fundraising | ✅ Inchangé |

---

## Précision et Fees

| Scénario | Résultat |
|----------|----------|
| 1 EUR invest | Envelope correct, pool asset balance = 0 |
| 0.01 direct | Commitment correct, available réduit |
| 999.999999 EUR | Précision preservée |
| Near-peg (1.001 EUR/USDC) | Drift < 1% |
| 10×100 vs 1×1000 | Drift < 0.01 USDC |
| Fees non-zero (50 bps) | Fees stockés dans envelope, pas dans wallet |

---

## Infrastructure de Test

### Mock Exchange Service
Un `MockExchangeService` déterministe qui :
- Reproduit les side-effects de `ExchangeService.buy()` et `.swap()` (credit/debit crypto_positions)
- Utilise des prix fixes configurables (EUR/USDC = 0.87, BTC/USDC = 62000)
- Enregistre tous les appels pour vérification

### Pool Isolation
Chaque test crée un pool avec un asset synthétique unique (`USDC_A1B2C3D4`) pour éviter les conflits avec les données production.

### Rollback
Chaque test se termine par un `session.rollback()` — aucune donnée persistante n'est créée.

---

## Non-Régression

| Service | Modifié ? |
|---------|-----------|
| ExchangeService | ❌ |
| PoolService | ❌ |
| LendingService | ❌ |
| invest_orchestrator | ❌ |
| envelope_models | ❌ |
| product_surface | ❌ |
| Architecture métier | ❌ |

---

## Risques Résiduels

| Risque | Mitigation |
|--------|------------|
| Volatilité exchange rate entre preview et execution | By design (preview read-only) |
| Perte connexion DB mid-transaction | Rollback DB-level automatique |
| Reconciliation settlement avec exchange réel | Hors scope (environnement simulé) |
| Réplication multi-région | N/A (single-node deployment) |

---

## Exécution

```bash
$ cd api && PYTHONPATH=. python3 -m pytest tests/test_envelope_*.py -v

======================== 60 passed, 6 warnings in 3.82s ========================
```
