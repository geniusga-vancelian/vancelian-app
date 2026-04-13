# Executive Summary

Le durcissement des **actions sensibles** s’appuie sur la stack existante (**session intelligence**, **continuous auth engine**, **device trust** via `AuthSessionIntelligence`, **sensitive_action_map**) sans nouveau parallèle. La **carte des politiques** (`SensitiveActionPolicy`) centralise niveaux LOW/MEDIUM/HIGH, step-up obligatoire, fenêtre **recent auth** (`last_step_up_at`), biométrie et **device trusted only**. Les routes FastAPI utilisent **`Depends(require_continuous_auth_for_action("…"))`** ; les réponses sont **structurées** (`code`, `message`, `action_key`, `next_step`, `policy`, `reason_codes`). Les événements SIEM **`sensitive_action.*`** complètent les hooks `auth.session.*`. Le client Flutter dispose d’un **parseur minimal** (`sensitive_action_http.dart`) aligné sur le backend.

# Sensitive Actions Inventory

| action_key | Endpoint / zone (cible d’intégration) | Criticité | Description |
|------------|----------------------------------------|-----------|-------------|
| `withdrawal` | Retraits custody / exchange | HIGH | Retrait crypto / fiat |
| `wallet_transfer` | Transferts internes | HIGH | Transfert interne / entre comptes |
| `beneficiary_add` | Bénéficiaires | HIGH | Ajout bénéficiaire |
| `api_key_create` | Clés API | HIGH | Création / rotation |
| `security_settings_change` | Paramètres sécurité | HIGH | 2FA, limites, etc. |
| `contact_change` | Profil / identité | HIGH | Changement e-mail / mobile |
| `passcode_reset` | Recovery | HIGH | Reset passcode sensible |
| `biometric_disable` | App mobile | HIGH | Désactivation biométrie |
| `data_export` | RGPD | HIGH | Export données |
| `session_revoke_all` | **`POST /auth/revoke-all`** (branché) | HIGH | Révocation globale sessions |
| `change_password` | Auth | MEDIUM | Changement mot de passe |
| `view_sensitive_data` | Admin / KYC | MEDIUM | Données sensibles |
| `view_portfolio` | PE | MEDIUM | Consultation portefeuille |
| `internal_transfer_low` | PE | MEDIUM | Transfert faible montant (policy métier) |
| `view_balances_summary` | API | LOW | Soldes synthétiques |
| `preferences_update` | Préférences | LOW | Non financier |

*Les routes métier non encore décorées doivent référencer une clé de cette table.*

# Policy Model

- **`AuthLevel`** : `LOW` | `MEDIUM` | `HIGH` (mapping interne vers `low` / `medium` / `high` pour `should_force_reauth` / `should_require_step_up`).
- **`SensitiveActionPolicy`** : `requires_step_up`, `requires_recent_auth_seconds`, `requires_biometric`, `allowed_if_device_trusted_only`, `description`.
- Fichier : `api/services/security/sensitive_action_map.py` (`ACTION_POLICIES`, `policy_for_action`, `tier_for_action`).

# Backend Enforcement

- **`continuous_auth_engine.evaluate_request_security_context`** : agrège politique + `session_intelligence_service` (risque, step-up, reauth, relock, `device_trust_level`).
- **`session_intelligence_dependencies.require_continuous_auth_for_action`** : dépendance FastAPI ; **401** `session.reauth_required`, **403** `session.step_up_required` ou `session.continuous_auth_denied` ; `detail` enrichi.
- **`POST /auth/revoke-all`** : `Depends(require_continuous_auth_for_action("session_revoke_all"))` (remplace seul `get_current_user` pour cette route — le `Depends` inclut déjà l’utilisateur courant).
- Probe admin : `GET .../probe-continuous-auth` — inchangé (`view_sensitive_data`).

# Frontend UX

- **Source de vérité** : JSON `detail` du backend (pas de re-calcul du risque côté client).
- **`mobile/lib/core/sensitive_action_http.dart`** : `parseSensitiveActionError`, codes `SensitiveActionHttpCodes`, `SensitiveActionNextStep`.
- Enchaînement recommandé : erreur → `next_step` → route OTP / passkey / biométrie / login (réutiliser `SessionSecuritySnapshot`, `PostLoginLocalSecurityFlow`, orchestrateur existant).

# Device Trust Integration

- `allowed_if_device_trusted_only` : si `device_trust_level` ∉ {`HIGH`, `TRUSTED`} → **step-up** (`reason_codes` contient `device_not_trusted`).
- Scores / raisons : inchangés (`session_intelligence_service.evaluate_session_risk`, etc.).

# Session Intelligence Integration

- `strust` / risque / `relock` : via `AuthSessionIntelligence` et fonctions existantes `should_force_reauth`, `should_require_step_up`, `should_relock_local`.
- **Recent auth** : `requires_recent_auth_seconds` compare `last_step_up_at` à TTL ; sinon **step-up** (`recent_auth_required`).

# Events

| Événement | Déclencheur |
|-----------|-------------|
| `sensitive_action.requested` | Entrée dans `require_continuous_auth_for_action` |
| `sensitive_action.step_up_required` | 403 step-up |
| `sensitive_action.reauth_required` | 401 reauth |
| `sensitive_action.blocked` | 403 refus générique |
| `auth.session.*` | Conservés (audit historique) |
| `sensitive_action.completed` / `sensitive_action.failed` | Helpers `sensitive_action_events.py` (à appeler depuis les handlers métier) |

# Tests

- `api/tests/test_session_intelligence.py` : politique `withdrawal`, `next_step_hint`, recent auth, device non trusted.
- Suites `test_zero_trust_policy.py` : régression OK.

# Final Verdict

Objectif atteint : **une seule source de politique** (`sensitive_action_map`), **un seul moteur de décision** (`continuous_auth_engine`), **une dépendance FastAPI** réutilisable, **réponses structurées** pour le client. Aucune stack parallèle.

# Remaining Gaps

- Brancher **`Depends(require_continuous_auth_for_action(...))`** sur chaque route métier critique (retrait, ordre, PE, etc.) — inventaire ci-dessus.
- Appeler **`record_sensitive_action_completed` / `record_sensitive_action_failed`** dans les handlers après succès / échec métier.
- **Flutter** : brancher un point central (ex. intercepteur HTTP) vers `parseSensitiveActionError` + navigation.
- **Montants** : `internal_transfer_low` nécessite une règle métier (seuil) côté route ou policy dynamique.
