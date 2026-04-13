# Rapport d’achèvement — sécurité Tier-1

## Synthèse

La plateforme API Arquantix intègre désormais un **score de risque global persisté**, un **moteur de réponse automatique** branché sur le pipeline SIEM, un **renforcement des contrôles sur les jetons d’accès et le refresh**, un **durcissement de l’attestation** (Apple / Google), des **événements d’audit dédiés**, des **endpoints admin** de réinitialisation, et une **suite de tests** ciblés.

## Partie 1 — Score global (`auth_global_risk_score`)

- **Table** : `auth_global_risk_score` (`user_id` PK, `score`, `level`, `updated_at`), migration Alembic `114`.
- **Modèle ORM** : `AuthGlobalRiskScore` dans `database.py`.
- **Calcul** (`compute_global_risk_score`) : agrégation du moteur `assess_user_risk` (événements SIEM / sessions), **majorations** heuristiques via `SecuritySignalService.detect_anomalies` et sessions actives en `device_trust_level` `SUSPICIOUS` / `BLOCKED`.

## Partie 2 — Moteur de réponse (`security_response_engine.py`)

- **Seuil ≥ 70** : `step_up_otp_required` sur toutes les sessions actives ; événement `auth.security.action.step_up` (`action_taken`: `require_otp_step_up`).
- **Seuil ≥ 90** : révocation des sessions (`revoke_reason=security_risk_score`), `security_refresh_blocked`, `security_flagged` ; événement `auth.security.action.revoked`.
- **Seuil ≥ 95** : verrouillage temporaire (`security_account_locked_until`, durée `SECURITY_ACCOUNT_LOCK_HOURS`, défaut 24 h), blocage refresh et flag ; événement `auth.security.action.blocked` (`action_taken`: `temporary_account_lock`).
- **Flags** : `SECURITY_RESPONSE_ENGINE_ENABLED` (défaut actif), `SECURITY_RESPONSE_ENGINE_ON_EMIT` (déclenchement après persistance d’événements, défaut actif).

## Partie 3 — Enforcement session / middleware

- **`enforce_access_security`** (appelé depuis `get_current_user`) : compte verrouillé → 403 `security.account_locked` ; session en attente de step-up sans claim JWT adapté → 403 `security.step_up_refresh_required` ; JWT avec `step_up_otp` → 403 `security.step_up_otp_required`.
- **`perform_login`** : refus si compte verrouillé.
- **`perform_refresh`** : contrôle utilisateur **avant** consommation du jti ; refus si verrouillé ou `security_refresh_blocked`.

## Partie 4 — Attestation

- **Apple** : contrôle **challenge** dans `clientDataJSON` aligné sur le **nonce** serveur ; en `DEVICE_ATTESTATION_STRICT`, exigence d’`attestation_object_b64`, chaîne **x5c** vérifiée jusqu’à une ancre PEM (`APPLE_APP_ATTEST_ROOT_PEM_PATH`), puis **ECDSA** sur `authenticatorData || SHA256(clientDataJSON)` avec la clé feuille du certificat.
- **Google** : hors mode dev (`core.env.is_dev_mode`), **interdiction du mode lenient** sans API : `PLAY_INTEGRITY_REQUIRE_API_OUTSIDE_DEV` (défaut `true`) impose `PLAY_INTEGRITY_USE_GOOGLE_API` pour accepter un jeton Play Integrity.

## Partie 5 — SIEM

- Chaque payload sink (`build_sink_payload`) inclut désormais **`global_risk_score`** et **`action_taken`** (niveau racine, issus des métadonnées normalisées).

## Partie 6 — Journalisation des actions

- Événements persistés (métadonnées avec `skip_security_response_engine` pour éviter la récursion) :
  - `auth.security.action.blocked`
  - `auth.security.action.step_up`
  - `auth.security.action.revoked`

## Partie 7 — Admin

- `POST /admin/security/unblock-user` — corps JSON `{ "user_id": <int> }` : lève verrou, blocage refresh, flag, step-up sur sessions actives.
- `POST /admin/security/reset-risk` — même corps : remet le score à 0 / niveau `LOW` et applique le même déblocage opérationnel.

## Partie 8 — Tests

- Fichier `api/tests/test_tier1_security_response.py` : step-up à score élevé, révocation + blocage refresh, verrouillage extrême, enforcement JWT, Play Integrity prod sans API, rejet Apple sur challenge incohérent.

## Fichiers principaux touchés

- `api/alembic/versions/114_tier1_global_risk_security_response.py`
- `api/database.py`
- `api/services/security/security_response_engine.py`
- `api/services/security/security_event_pipeline.py`
- `api/auth.py`
- `api/services/auth/refresh_session.py`
- `api/services/auth/device_attestation_service.py`
- `api/services/auth/security_admin_routes.py`
- `api/schemas.py`
- `api/tests/test_tier1_security_response.py`

## Déploiement

1. `alembic upgrade head` (révision **114**).
2. Configurer en production : `APPLE_APP_ATTEST_ROOT_PEM_PATH` (strict Apple), compte de service + `PLAY_INTEGRITY_USE_GOOGLE_API=true` pour Android hors dev.
