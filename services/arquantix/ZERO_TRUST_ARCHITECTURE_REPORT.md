# Zero Trust — Rapport d’architecture (API Arquantix)

## Executive Summary

Ce livrable introduit une **couche Zero Trust** unifiée sur l’API FastAPI : un **contexte de sécurité par requête**, un **moteur de politique** (RBAC + ABAC), la **journalisation des décisions** en base, l’intégration au **refresh** (changement IP / empreinte → step-up), des **endpoints admin** de lecture / évaluation, et un module de base **service-à-service** (JWT interne + documentation mTLS). Les briques existantes (**auth_sessions**, scores de risque globaux, réputation device, attestation, SIEM via le pipeline d’événements) sont réutilisées ; il n’y a pas de second stack parallèle.

**Activation production** : définir `ZERO_TRUST_ENFORCE_DEFAULT_ACCESS=true` pour appliquer `session.api_access` à chaque `get_current_user`. Les tests pytest positionnent `main.app.state.testing = True` pour ne pas exiger OTP/passkey sur les flux déjà couverts par des tests historiques.

## Request Security Context

- Fichier : `api/services/security/zero_trust/request_security_context.py`
- Type : `RequestSecurityContext` (user, session résolue, device, hash réputation, trust, risque global, score ML fraude optionnel, IP, pays optionnel via en-tête, step-up serveur, verrouillage compte, rôles, `auth_strength`, statut attestation).
- Builder unique : `build_request_security_context(db, request, user, access_token, device_header=..., jwt_payload=...)`.
- JWT : claims `auth_str`, `sid` (session), `dtrust` — alignés sur `create_access_token` et les sessions `auth_sessions.auth_strength`.

## Policy Engine

- Fichier : `api/services/security/zero_trust/security_policy_engine.py`
- Entrée : `evaluate_security_policy(context, action, resource)` → `allow`, `require_step_up`, `deny_reason`, `policy_id`, `action_taken`, etc.
- Cartes : `ROLE_POLICY_MAP`, `ACTION_POLICY_MAP` (seuils de risque effectif, sensibilité, force d’auth minimale).
- Seuils configurables : `ZERO_TRUST_DENY_ALL_RISK_THRESHOLD` (défaut 95), `ZERO_TRUST_STEP_UP_RISK_THRESHOLD` (défaut 70 via les entrées d’`ACTION_POLICY_MAP`), `ZERO_TRUST_STRICT_DEFAULT_ACCESS`.

## RBAC + ABAC Model

- **RBAC** : colonne `admin_users.zero_trust_role` (`admin` | `support` | `readonly` | extension `user`).
- **ABAC** : attributs du contexte (risque, device, `auth_strength`, attestation, flags session).
- `AuthContext` expose `zero_trust_role` pour les routes identity (`services/auth/models.py`, `dependencies.py`).

## Sensitive Action Gating

- Fichier : `api/services/security/zero_trust/security_guards.py`
- `enforce_zero_trust_or_raise`, `require_zero_trust_action`, `require_auth_strength`, `require_low_risk_or_step_up`.
- Intégrations : `POST /auth/revoke-all` (hors `app.state.testing`), `GET/PATCH` KYC persons (hors testing), liste contact admin avec contrôle de déchiffrement.

## Data Access Control

- Fichier : `api/services/security/zero_trust/data_access_control.py`
- `decryption_allowed(context, purpose, resource)` ; `admin_list_visibility_allowed`.
- `contact_row_to_admin_dict(..., security_context=...)` masque le contenu si la politique refuse le déchiffrement.

## Continuous Authentication

- Fichier : `api/services/security/zero_trust/continuous_auth.py`
- Sur refresh réussi : `maybe_require_step_up_after_refresh_signals` (IP ou empreinte différente → `step_up_otp_required` sur la session si `ZERO_TRUST_REFRESH_CONTEXT_CHANGE_STEP_UP=true`).
- Hook `reevaluate_security_on_critical_action` (journalisation debug / extension SIEM).

## Decision Logging

- Table : `public.auth_security_decisions` (migration Alembic **116**).
- Modèle : `AuthSecurityDecision` dans `database.py`.
- Persistance : `decision_logging.persist_security_decision` (flush sur la session requête ; commit avec le reste du flux métier).

## Service-to-Service Trust

- Fichier : `api/services/security/zero_trust/internal_service_auth.py`
- JWT interne optionnel (`INTERNAL_JWT_SECRET`, audience / issuer), scopes dans les claims.
- **mTLS** : décrit dans le module ; implémentation au niveau infra / mesh recommandée.

## Tests

- `api/tests/test_zero_trust_policy.py` : scénarios allow / step-up / deny / RBAC / déchiffrement KYC ; test de persistance **skip** si migration 116 non appliquée.
- `conftest` : `main.app.state.testing = True` en session pour les tests utilisant l’app globale.

## Remaining Gaps / Next Iteration

1. **Politique configurable** : externaliser `ACTION_POLICY_MAP` / `ROLE_POLICY_MAP` en YAML ou DB + endpoint `POST /policies/reload` fonctionnel.
2. **Ne pas relâcher le mode testing en prod** : ajouter des tests d’intégration `create_app(testing=False)` avec jetons OTP/passkey pour `revoke-all` et écriture KYC.
3. **Custody / transferts** : brancher `enforce_zero_trust_or_raise` sur les routes `ActorContext` lorsque les parcours admin le permettent.
4. **Révocation extrême** : si risque &gt; seuil critique, révoquer session côté serveur (au-delà du simple step-up).
5. **GeoIP** : alimenter `geo_country` sans dépendre uniquement d’un en-tête volontaire.
6. **Step-up horodaté** : claim JWT `zt_su` (dernier step-up fort) pour exiger un renouvellement récent sur actions admin critiques.
