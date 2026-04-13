# Crypto Custody Layer Report

## 1. Executive Summary

- **Couche custody créée** : oui. Tables `crypto_custody_accounts` et `crypto_custody_balances`, modèles SQLAlchemy, repository et intégration au settlement.
- **Backend branché** : oui. Bootstrap, GET list/detail, set-actual-balance, et `run_settlement()` utilisent la couche (DB en priorité, fallback in-memory si pas de comptes).
- **Admin branché** : oui. GET crypto-custody renvoie `actual_balance`, `expected_balance`, `mismatch` ; bouton Bootstrap et affichage écart dans l’onglet Crypto Custody.
- **Niveau de confiance** : bon. Pas de refonte du buy engine, tests existants passent (avec adaptation des 2 tests settlement pour piloter la DB). La source de vérité pour le settlement wallet devient la DB lorsque les comptes existent.

---

## 2. Files Modified

| Fichier | Rôle |
|--------|------|
| `alembic/versions/063_add_crypto_custody_tables.py` | Migration : création `crypto_custody_accounts` et `crypto_custody_balances`. |
| `services/exchange/custody_models.py` | **Créé** — Modèles `CryptoCustodyAccount`, `CryptoCustodyBalance`. |
| `services/exchange/custody_repository.py` | **Créé** — Repository (get_by_asset_and_type, get_or_create_account, get_or_create_balance, update_actual_balance, update_expected_balance, list_accounts, list_accounts_by_asset). |
| `services/exchange/service.py` | `_get_settlement_wallet_balance_for_settlement(db, asset)` : lecture DB puis fallback in-memory ; `run_settlement()` utilise cette fonction. |
| `services/exchange/admin_router.py` | GET crypto-custody enrichi (actual/expected/mismatch) ; GET by id ; POST bootstrap ; POST set-actual-balance ; history compatible UUID. |
| `tests/test_crypto_custody_layer.py` | **Créé** — Tests bootstrap, unicité, balances, admin payload, set-actual-balance, settlement avec DB. |
| `tests/test_exchange_engine.py` | Helpers `_ensure_crypto_custody_bootstrap`, `_set_settlement_wallet_actual_balance` ; tests settlement blocked/success pilotent la DB. |
| `web/src/app/admin/custody/page.tsx` | Onglet Crypto Custody : interface `CryptoAccount` étendue, cards avec actual/expected et badge écart, détail avec mismatch et « Mis à jour provider », bouton « Bootstrap comptes ». |
| `web/src/app/api/admin/exchange/crypto-custody/bootstrap/route.ts` | **Créé** — Proxy POST bootstrap vers le backend. |

---

## 3. Tables Created

### crypto_custody_accounts

- `id` (uuid, PK)
- `asset` (text, not null)
- `account_type` (text, not null) — `clients_pool` | `settlement_wallet`
- `provider` (text, not null)
- `provider_account_id` (text, nullable)
- `label` (text, not null)
- `status` (text, not null, default `active`)
- `metadata_` (jsonb, default `{}`)
- `created_at`, `updated_at`
- Contrainte : `unique(asset, account_type)`

### crypto_custody_balances

- `id` (uuid, PK)
- `account_id` (uuid, FK → crypto_custody_accounts.id, ON DELETE CASCADE, unique)
- `asset` (text, not null)
- `actual_balance` (numeric, not null, default 0)
- `expected_balance` (numeric, not null, default 0)
- `updated_from_provider_at` (timestamptz, nullable)
- `created_at`, `updated_at`
- Contrainte : `unique(account_id)`

---

## 4. Data Model Semantics

- **actual_balance** : solde technique côté provider (Fireblocks). En v1 sans Fireblocks, non alimenté automatiquement par le buy ; peut être renseigné via admin (set-actual-balance) ou seed. Utilisé par `run_settlement()` pour la liquidité du settlement wallet.
- **expected_balance** : ce que le système attend dans le wallet. Pour `clients_pool`, l’admin peut l’afficher dérivé de la somme des `crypto_positions` (override au read). Pour `settlement_wallet`, la valeur en base peut être mise à jour plus tard (sync Fireblocks, ou dérivée des deltas) ; en v1 elle reste souvent à 0 ou seed.
- **crypto_positions** : inchangé — balance économique client (entitlement). Le buy continue à écrire orders, positions, deltas ; pas de modification de sémantique.
- **crypto_settlement_deltas** : inchangé — obligation nette de règlement/livraison crypto. Le settlement lit la liquidité sur `crypto_custody_balances.actual_balance` (settlement_wallet) ou sur l’agrégat des positions (clients_pool) comme avant.

---

## 5. Exchange Integration

- **Buy** : inchangé. Continue à écrire order, positions, deltas ; ne touche pas `actual_balance` ; pas de mise à jour automatique de `expected_balance` dans ce patch (évite de prétendre qu’un wallet technique détient l’actif avant Fireblocks).
- **Settlement** : `run_settlement()` utilise `_get_settlement_wallet_balance_for_settlement(db, asset)` :
  1. Si un compte `crypto_custody_accounts` (asset, `settlement_wallet`) existe et a une ligne `crypto_custody_balances`, retourne `actual_balance`.
  2. Sinon, retourne `get_settlement_wallet_balance(asset)` (in-memory).
- **Transition** : le dict in-memory `_settlement_wallet_reserves` n’est pas supprimé ; il sert de fallback tant que les comptes n’existent pas ou ne sont pas seedés. Dès que bootstrap + (optionnel) set-actual-balance sont faits, la DB est la source de vérité pour le settlement.

---

## 6. Admin Integration

- **Cards** : en haut, une card par settlement wallet (par asset) ; affichage `actual_balance` (ou `balance` en legacy), `expected_balance` si présent, badge « Écart » si `mismatch` non nul.
- **Split view** : gauche = liste de tous les comptes crypto techniques ; droite = détail du compte sélectionné (actual, expected, mismatch, updated_from_provider_at).
- **Mismatch** : si `actual_balance !== expected_balance`, badge warning et montant d’écart affiché (actual − expected).
- **Bootstrap** : bouton « Bootstrap comptes » appelle `POST /api/admin/exchange/crypto-custody/bootstrap`, puis rafraîchit la liste.

---

## 7. Tests Added

| Test | Résultat |
|------|----------|
| `test_bootstrap_creates_two_accounts_per_asset` | PASS |
| `test_bootstrap_idempotent` | PASS |
| `test_custody_accounts_unique_asset_type` | PASS |
| `test_get_or_create_balance` | PASS |
| `test_update_actual_balance` | PASS |
| `test_update_expected_balance` | PASS |
| `test_admin_crypto_custody_includes_actual_expected_mismatch` | PASS |
| `test_admin_crypto_custody_detail_by_id` | PASS |
| `test_set_actual_balance_endpoint` | PASS |
| `test_settlement_uses_persisted_balance` | PASS |
| Tests exchange existants (dont `test_settlement_blocked_when_pool_insufficient`, `test_settlement_success_when_balance_ok`) | PASS (avec helpers pilotant la DB) |

---

## 8. Final Status

**Le système distingue-t-il désormais entitlement client, obligation de settlement et balance custody technique ?**

- **Oui, avec précisions** :
  - **Client entitlement** : `crypto_positions` (inchangé).
  - **Obligation de settlement** : `crypto_settlement_deltas` (inchangé).
  - **Balance custody technique** : `crypto_custody_balances.actual_balance` (et optionnellement `expected_balance`) pour les comptes techniques `clients_pool` et `settlement_wallet`. Sans Fireblocks, `actual_balance` est alimenté par seed/admin ; avec Fireblocks, il pourra être synchronisé depuis le provider.

---

## 9. Remaining TODOs

- **Fireblocks sync** : alimenter `actual_balance` et `updated_from_provider_at` à partir du provider (hors scope de ce patch).
- **crypto_custody_movements** : non implémenté ; l’historique reste dérivé (orders, deltas). À envisager si un journal par compte technique est requis.
- **SELL engine** : hors scope.
- **Full reconciliation** : comparaison systématique actual vs expected et alertes ; préparé par les champs et l’affichage mismatch, à automatiser plus tard.
