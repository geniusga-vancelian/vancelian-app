# Financial Test State Reset Report

## 1. Executive Summary

- **Reset implémenté** : oui, via un **script backend dédié** et un **endpoint admin** protégé.
- **Mode d'exécution** :
  - **Script CLI** : depuis la **racine du projet** (arquantix) : `python3 -m api.scripts.reset_financial_test_state` (option `--dry-run` pour simulation sans modification). Alternative : `python3 api/scripts/reset_financial_test_state.py` (ajoute automatiquement le path api).
  - **Endpoint admin** : `POST /api/admin/custody/reset-financial-test-state?dry_run=false` (protégé admin/ops, retourne le rapport en JSON).
- **Niveau de confiance** : élevé — ordre des opérations respecte les FKs ; seules les données opérationnelles sont touchées ; référentiel (comptes, clients, providers, produits/templates) conservé.

## 2. Files Modified / Created

| Fichier | Rôle |
|--------|------|
| `api/services/financial_reset/__init__.py` | Export du module (TABLES_DELETE_ORDER, run_reset). |
| `api/services/financial_reset/reset.py` | Logique de reset : ordre des suppressions, UPDATE des balances, rapport avant/après, comptage par type de compte. |
| `api/scripts/reset_financial_test_state.py` | CLI : setup path/env, appelle `run_reset` et affiche le rapport (sans effet de bord à l’import). |
| `api/services/custody/router.py` | Ajout de `POST /reset-financial-test-state` (admin/ops), appelle `run_reset`. |
| `api/docs/FINANCIAL_RESET_REPORT.md` | Ce rapport : périmètre, ordre, vérifications, statut, TODOs. |
| `api/tests/test_reset_financial_test_state.py` | Tests : structure du rapport dry-run, TABLES_DELETE_ORDER n’inclut pas les tables référentielles. |

## 3. Reset Scope

### Tables remises à zéro (données supprimées ou mises à 0)

| Table | Action |
|-------|--------|
| `custody_webhook_events` | DELETE toutes les lignes |
| `custody_transactions` | DELETE toutes les lignes |
| `pe_ledger_entries` | DELETE toutes les lignes |
| `exchange_orders` | DELETE toutes les lignes |
| `crypto_positions` | DELETE toutes les lignes (choix propre : pas de lignes résiduelles à balance 0) |
| `crypto_settlement_deltas` | DELETE toutes les lignes |
| `custody_account_balances` | UPDATE : `available_balance = 0`, `pending_balance = 0`, `version = version + 1`, `last_updated_at = now()` — **toutes les lignes conservées**, tous types de comptes couverts |

### Types de comptes couverts (aucun oubli)

Le reset s’applique à **tous** les `custody_account_balances`, donc à tous les types de comptes :

- `client_deposit_account` (EUR clients)
- `company_settlement_account` (EUR entreprise / settlement)
- `crypto_clients_pool`
- `crypto_settlement_wallet`

### Tables / entités conservées (jamais supprimées)

- `pe_clients`
- `app_runtime_settings`
- `custody_providers`
- `custody_accounts` (tous types ci-dessus)
- `pe_ledger_accounts`
- `pe_product_definitions`, `pe_portfolio_templates`, `pe_template_allocations`, et reste du référentiel portfolio engine
- Produits, bundles, templates, configurations

### Non modifié (volontairement)

- **pe_audit_events** : non vidé (éviter toute perte d’audit ; purge ciblée éventuelle dans un script dédié).
- Schéma, contraintes, index : inchangés.

## 4. Execution Flow

Ordre d’exécution (respect des clés étrangères) :

1. **custody_webhook_events** — FK `linked_transaction_id` → `custody_transactions` (ondelete=SET NULL). Suppression en premier pour éviter des orphelins.
2. **custody_transactions** — Référence `custody_accounts` et `custody_providers` ; self-FK `reversal_of_transaction_id` (SET NULL). Suppression en un bloc.
3. **pe_ledger_entries** — Référence `pe_ledger_accounts` (conservés). Aucune table ne référence les entries ; suppression en un bloc.
4. **exchange_orders** — FK `pe_clients` (conservés). Suppression en un bloc.
5. **crypto_positions** — FK `pe_clients` (conservés). Suppression en un bloc (positions recréées lors des prochains flux).
6. **crypto_settlement_deltas** — Aucune FK entrante. Suppression en un bloc.
7. **custody_account_balances** — UPDATE uniquement (pas de DELETE) pour **tous** les comptes (clients, settlement EUR, crypto pools, settlement crypto).

Pourquoi cet ordre : éviter toute violation de FK (aucune table « enfant » restante ne pointe vers une ligne supprimée). Les comptes, clients, providers et ledger_accounts ne sont jamais supprimés.

## 5. Post-Reset Verification

Le script et l’endpoint affichent / retournent après exécution :

- **Row counts** : avant et après pour chaque table concernée.
- **custody_accounts** : count identique avant/après ; détail par `account_type` (optionnel).
- **custody_account_balances** : count identique avant/après ; toutes les balances à 0.
- **custody_total_eur** : somme (available + pending) EUR sur les comptes custody → **0** après reset.
- **Tables runtime** : `custody_transactions` = 0, `custody_webhook_events` = 0, `pe_ledger_entries` = 0, `exchange_orders` = 0, `crypto_positions` = 0, `crypto_settlement_deltas` = 0.

Vérifications attendues :

- Comptes conservés (count + types).
- Balances remises à zéro (count conservé, sommes à 0).
- Transactions, webhooks, ledger entries, orders, positions, deltas à 0.

## 6. Final Status

- **Peut-on repartir sur des tests end-to-end fiat/crypto propres ?** **Oui**, sous réserve que l’environnement (providers, comptes, clients, produits) soit déjà correctement seedé. Le reset ne fait que remettre à zéro les mouvements et soldes opérationnels.

## 7. Remaining TODOs

- **Bouton admin** : fait. Bouton « Reset financial test state » sur la page admin/custody (header), avec dialogue de confirmation et affichage du rapport dans une modale après exécution.
- **Snapshot / backup** : optionnel ; documenter une procédure de dump préalable (ex. `pg_dump` des tables concernées) si besoin de rollback manuel.
