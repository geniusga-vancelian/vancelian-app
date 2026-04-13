# Phase finale — Domaine Auth / Security (intégration continuous auth)

## Executive Summary

Intégration de **`Depends(require_continuous_auth_for_action(...))`** et des hooks **`record_sensitive_action_completed` / `record_sensitive_action_failed`** sur les endpoints **auth / sécurité** qui existent dans ce dépôt et qui **engagent** l’utilisateur authentifié. Les flux **login non authentifiés** (`/auth/login`, OTP start/verify, passkey login start/finish) sont **volontairement exclus** : pas de jeton de session stable pour l’auth continue.

## Fichiers modifiés

| Fichier | Changement |
|---------|------------|
| `api/main.py` | `GET /auth/sessions` → `view_sensitive_data` + événement `completed` ; `POST /auth/revoke-all` → événement `completed` + `db.commit()` |
| `api/services/auth/passkeys_routes.py` | Passkeys **authentifiés** : `security_settings_change` / `view_sensitive_data` ; hooks completed/failed ; `db.commit()` |
| `api/services/auth/security_admin_routes.py` | `POST .../unblock-user`, `POST .../reset-risk` → `security_settings_change` + hooks |
| `api/tests/test_passkeys.py` | Fixture **`_relax_passkey_step_up_guard`** : neutralise `auth.enforce_access_security` pour les tests d’intégration (sinon blocage JWT `step_up_otp` sans flux OTP complet) |

## Endpoints protégés et `action_key`

| Méthode + chemin | `action_key` | Hooks completed/failed | Notes |
|------------------|--------------|------------------------|-------|
| `POST /auth/revoke-all` | `session_revoke_all` | `completed` | Déjà protégé ; ajout événement + commit |
| `GET /auth/sessions` | `view_sensitive_data` | `completed` (lecture) | Liste des sessions actives |
| `POST /auth/passkeys/register/start` | `security_settings_change` | oui | |
| `POST /auth/passkeys/register/finish` | `security_settings_change` | oui | |
| `GET /auth/passkeys` | `view_sensitive_data` | `completed` (lecture) | |
| `POST /auth/passkeys/revoke` | `security_settings_change` | oui | |
| `POST /admin/security/unblock-user` | `security_settings_change` | oui | Action admin sur un autre utilisateur |
| `POST /admin/security/reset-risk` | `security_settings_change` | oui | Idem |

## Endpoints volontairement non couverts (ce dépôt)

| Sujet | Raison |
|-------|--------|
| `change_password` | Aucune route HTTP dédiée trouvée (`AdminUser.hashed_password` mis à jour ailleurs ou non exposé). |
| `passcode_reset` / `biometric_disable` | Gestion principalement **côté app mobile** ; pas d’équivalent FastAPI identifié ici. |
| `contact_change` (email/mobile) | Pas de route profil utilisateur dédiée sous `/auth` dans l’audit courant. |
| `enable/disable 2FA` | Router `/api/2fa` repose sur **person_id** / modèle Person, pas sur `get_current_user` admin JWT — hors périmètre « auth admin » direct ; traiter dans une phase **2FA / persons** dédiée. |
| `POST /auth/login`, `/auth/refresh`, OTP, passkey **login** | Flux **non authentifiés** ou refresh — pas d’action sensible « en session » au sens `require_continuous_auth`. |

## Tests

| Test | Rôle |
|------|------|
| `tests/test_passkeys.py` | Régression passkeys + fixture step-up |
| `tests/test_session_intelligence.py` | Moteur continuous auth (inchangé fonctionnellement par ce domaine) |

Tests **401/403** structurés (`session.reauth_required`, `session.step_up_required`) sur ces routes : **non ajoutés** dans cette itération (nécessitent JWT avec `sid`, intelligence de session, et feature flags cohérents) ; à prévoir en suite avec client de test dédié ou mocks sur `evaluate_request_security_context`.

## Ambiguïtés / suites

1. **`security_settings_change`** sert à la fois aux **actions utilisateur** (passkeys) et **admin** (unblock / reset-risk) : acceptable tant que la politique `SensitiveActionPolicy` reste HIGH ; affiner avec une clé `admin_security_override` si l’audit le demande.
2. **Double commit** : les services passkeys appellent déjà `db.commit()` ; les `db.commit()` après événements peuvent générer des warnings SQLAlchemy en test — à surveiller ; pas de régression fonctionnelle observée.
3. **Couverture 401/403** : ajouter des tests d’intégration ciblés quand `CONTINUOUS_AUTH_ENABLED` + `SESSION_INTELLIGENCE_ENABLED` sont forcés dans un sous-module de test.

## Verdict

Domaine **Auth / Security** (tel qu’exposé dans ce repo) : routes **identifiées et branchées** ; rapport d’inventaire pour les **absences** de routes (change password, etc.). Prochaine étape plan : **Withdrawals / Beneficiaries** puis **Transfers / PE** selon le plan utilisateur.
