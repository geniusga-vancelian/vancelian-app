# Phase 2 — Retraits / bénéficiaires : rapport d’intégration (auth continue)

## Executive Summary

L’audit FastAPI a identifié **peu de routes « withdrawal / beneficiary » nommées explicitement** en dehors du module **custody admin**. Le périmètre **money-out** pertinent et implémenté côté API est surtout :

- **Simulation de retrait** (débit client → settlement) : `POST /api/admin/custody/simulate-withdrawal`
- **Création de compte client avec IBAN** (destination de sortie de fonds) : `POST /api/admin/custody/accounts/client`
- **Rejeu d’événement webhook** pouvant matérialiser des dépôts/retraits côté ledger : `POST /api/admin/custody/webhook-events/{event_id}/replay`

Ces endpoints sont protégés par **`Depends(require_continuous_auth_for_action(...))`** (clés **`withdrawal`** et **`beneficiary_add`**) en complément du garde-fou existant **`require_admin_or_ops()`** (contexte acteur `ActorContext`). Les hooks **`record_sensitive_action_completed` / `record_sensitive_action_failed`** complètent l’audit métier contrôlé.

Les routes **read-only** (listes, soldes, transactions, webhooks en lecture) restent sans auth continue obligatoire. Les simulations de **dépôt** et les comptes **settlement** entreprise ne sont pas traités comme « beneficiary add » au sens produit (Phase 2 cible les destinations **client**).

**Transferts internes** (`POST /api/internal-transfer`) : laissés pour la **Phase 3 (Transfers / PE)** comme prévu.

---

## Inventaire (table demandée)

| Méthode | Chemin | Fichier router | Effet métier | Protéger ? | `action_key` | Raison |
|--------|--------|----------------|--------------|------------|--------------|--------|
| POST | `/api/admin/custody/accounts/client` | `api/services/custody/router.py` | Crée un compte dépôt client + IBAN (destination sortie) | Oui | `beneficiary_add` | Enregistre une destination de paiement réelle |
| POST | `/api/admin/custody/simulate-withdrawal` | idem | Débite le client, crédite le settlement (retrait simulé) | Oui | `withdrawal` | Mouvement de fonds sortant |
| POST | `/api/admin/custody/webhook-events/{event_id}/replay` | idem | Rejoue un webhook (peut compléter retrait / dépôt) | Oui | `withdrawal` | Action d’exécution sensible sur le pipeline de fonds |
| GET | `/api/admin/custody/*` (providers, accounts, balances, transactions, webhook-events) | idem | Lecture | Non | — | Pas d’effet irréversible ; RBAC acteur suffisant |
| POST | `/api/admin/custody/simulate-deposit` | idem | Crédit client (entrée) | Non | — | Hors périmètre « sortie » Phase 2 |
| POST | `/api/admin/custody/accounts/settlement` | idem | Compte entreprise | Non | — | Pas une destination client ; pas mappé `beneficiary_add` |
| POST | `/api/admin/custody/reset-financial-test-state` | idem | Reset données de test | Non | — | Outil interne ; RBAC admin/ops |
| POST | `/api/internal-transfer` | `api/services/custody/router.py` (`transfer_router`) | Transfert interne | Non (Phase 3) | — | Dédié phase Transfers / PE |

*Aucune autre route « crypto withdrawal », « fiat withdrawal » ou « bénéficiaire » dédiée n’a été trouvée dans l’API Arquantix auditée ; les flux mobile/app éventuels passent par d’autres services ou ne sont pas exposés sous ces noms.*

---

## Fichiers modifiés

- `api/services/custody/router.py` — `Depends(require_continuous_auth_for_action)`, hooks SIEM, `Request` / `AdminUser` où nécessaire
- `api/tests/test_custody.py` — en-têtes JWT + `make_linked_client` pour isolation transactionnelle des tests
- `api/tests/test_custody_hardening.py` — idem
- `api/tests/test_custody_sensitive_auth.py` — **nouveau** : 401/403 structurés (mock `evaluate_request_security_context`), 401 sans Bearer, hooks withdrawal
- `PHASE_FINAL_WITHDRAWALS_BENEFICIARIES_INTEGRATION_REPORT.md` — ce document

---

## Endpoints protégés (par `action_key`)

### `withdrawal`

- `POST /api/admin/custody/simulate-withdrawal`
- `POST /api/admin/custody/webhook-events/{event_id}/replay`

### `beneficiary_add`

- `POST /api/admin/custody/accounts/client`

---

## Endpoints volontairement non protégés (résumé)

- **Lecture** custody admin : pas de friction auth continue ; données déjà derrière `require_admin_or_ops()`.
- **Dépôt simulé**, **compte settlement**, **reset financier test** : pas classés comme ajout de bénéficiaire ou retrait utilisateur dans cette phase.
- **`/api/internal-transfer`** : report Phase 3.

---

## Couverture de tests ajoutée / ajustée

- **`tests/test_custody_sensitive_auth.py`** : réponses structurées `session.reauth_required` (401) et `session.step_up_required` (403) avec mock de `evaluate_request_security_context` ; 401 sans `Authorization` sur retrait ; hooks `withdrawal` completed/failed (filtrage des appels par `action_key`) ; 403 `beneficiary_add` sur création compte client.
- **`tests/test_custody.py`** / **`tests/test_custody_hardening.py`** : JWT fusionné avec en-têtes acteur pour les POST sensibles ; création de client PE via **`make_linked_client`** avant les routes qui `commit`, pour éviter la corruption de session de test documentée (nested transaction / `db.commit()`).

---

## Ambiguïtés restantes

- **Rejeu webhook** partage la clé `withdrawal` avec la simulation de retrait : sémantique large (« mouvement de fonds / exécution »). Une clé dédiée (`webhook_replay`) pourrait être introduite plus tard si l’audit produit le exige.
- **`except Exception`** sur le rejeu : large ; conservé pour tracer les échecs ; à resserrer si des exceptions HTTP doivent remonter sans hook « failed » générique.
- **Environnements sans table `auth_session_intelligence`** : les tests d’auth continue moquent `get_intelligence_for_session` ; en prod, la table et les migrations doivent être alignées pour une évaluation réelle.

---

## Prochaine phase recommandée : Transfers / PE

- Protéger **`POST /api/internal-transfer`** avec une clé du type `wallet_transfer` (déjà présente dans `sensitive_action_map.py`) et les mêmes hooks SIEM.
- Réauditer les routes **exchange / crypto custody** pour adresses de retrait ou bénéficiaires si exposées en API.

---

## Synthèse finale (livraison)

| Élément | Détail |
|--------|--------|
| **Fichiers changés** | `router.py` custody, `test_custody.py`, `test_custody_hardening.py`, `test_custody_sensitive_auth.py` (nouveau), ce rapport |
| **Routes protégées** | **`withdrawal`** : simulate-withdrawal, webhook replay ; **`beneficiary_add`** : accounts/client |
| **Tests** | 30 tests custody / hardening / sensitive_auth verts ; scénarios 401/403 + hooks withdrawal |
| **Risques résiduels** | Isolation DB des tests fragilisée par tout `db.commit()` dans les routes (warnings SQLAlchemy) ; clé `withdrawal` utilisée aussi pour replay webhook ; dépendance aux feature flags `CONTINUOUS_AUTH_ENABLED` / `SESSION_INTELLIGENCE_ENABLED` |
