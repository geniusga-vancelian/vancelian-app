# Passkey auto-trigger (login téléphone) — rapport

## Executive Summary

Ajout d’une **fast lane** : après `POST /auth/login/sms/start`, si le device est **jugé fiable** et l’utilisateur a une **passkey active**, l’API recommande **`recommended_auth_method: passkey`** et peut exposer **`passkey_login_email`**. L’app Flutter ouvre **`LoginAutoAuthScreen`**, lance **`PasskeyLoginCoordinator`** automatiquement, et bascule sur **OTP SMS** en cas d’annulation, d’erreur ou d’action utilisateur — **sans supprimer** le flux SMS ni forcer la passkey.

## Eligibility Logic

Fichier : `api/services/auth/passkey_login_eligibility.py`

- **`evaluate_passkey_login_eligibility(db, user, device_context, risk_context, step_up_required)`** → `eligible`, `recommended`, `reason_codes`.
- **Recommandation passkey auto** (toutes requises) :
  - `PASSKEY_AUTO_TRIGGER_ENABLED` (défaut `true`)
  - Passkeys activées (`AUTH_PASSKEYS_ENABLED`) et **au moins une** credential non révoquée
  - Contexte non `blocked`
  - **Pas** de `step_up_required` (stratégie login + réputation)
  - **`device_trust_level == HIGH`** (profil utilisateur-device / risque contextuel)
  - `login_risk_score` ≤ `PASSKEY_AUTO_MAX_LOGIN_RISK` (défaut **48**)
  - Risque global utilisateur **≠ CRITICAL**
  - Pas de signaux `fingerprint_changed_or_missing_vs_profile` ni `device_blacklisted`

## Backend Contract

`POST /auth/login/sms/start` — champs ajoutés sur réponse **200** (utilisateur connu, SMS envoyé) :

| Champ | Type | Description |
|--------|------|-------------|
| `recommended_auth_method` | `passkey` \| `otp` | Voie UX privilégiée (auto-trigger si `passkey` côté app). |
| `fallback_auth_method` | `otp` | Toujours OTP SMS disponible. |
| `step_up_required` | bool | Aligné stratégie session. |
| `device_trust_level` | string | HIGH / MEDIUM / LOW. |
| `passkey_auto_eligible` | bool | Passkey présente + feature on (sans garantir recommandation). |
| `passkey_login_email` | string?, optional | E-mail pour `/auth/passkeys/login/*` si `PASSKEY_AUTO_EXPOSE_LOGIN_EMAIL=true` (défaut `true`) et recommandation passkey. |

Variables d’environnement : `PASSKEY_AUTO_TRIGGER_ENABLED`, `PASSKEY_AUTO_EXPOSE_LOGIN_EMAIL`, `PASSKEY_AUTO_MAX_LOGIN_RISK`.

Les champs historiques `auth_strategy_hint`, `primary_auth_method`, `step_up_recommended` restent ; **`primary_auth_method`** est aligné sur **`recommended_auth_method`**.

## Flutter Flow

- **`login_phone_screen.dart`** : après `mobileLoginStart`, si `recommended_auth_method == passkey` **et** e-mail utilisable (`passkey_login_email` **ou** dernier e-mail mémorisé localement) → navigation vers **`LoginAutoAuthScreen`**, sinon **`LoginOtpScreen`** (inchangé).
- **`login_auto_auth_screen.dart`** : libellés premium, CTA **« Vous pouvez aussi recevoir un code par SMS »**, retour arrière → OTP.
- **`PasskeyLoginCoordinator`** : paramètre optionnel **`autoAnalytics`** pour les événements listés ci-dessous (envoyés via `PasskeyApi.reportPrompt` → `POST /auth/passkeys/prompt`).

## Fallback Strategy

| Cas | Comportement |
|-----|----------------|
| Passkey indisponible / non enrôlée côté OS | `onFallback` → écran OTP (SMS déjà déclenché). |
| Annulation utilisateur | Analytics `..._cancelled` + OTP. |
| Erreur authenticator / API | Analytics `..._failed` + OTP. |
| Bouton SMS / retour | Analytics + `pushReplacement` vers `LoginOtpScreen`. |
| Backend refuse plus tard | OTP reste utilisable ; pas d’impasse. |

## Events

Acceptés par **`POST /auth/passkeys/prompt`** (whitelist étendue dans `passkeys_service.py`) :

- `auth.login.passkey_auto_triggered`
- `auth.login.passkey_auto_trigger_cancelled`
- `auth.login.passkey_auto_trigger_failed`
- `auth.login.passkey_auto_trigger_fallback_otp`

Les événements existants `auth.passkey.prompt.*` sont inchangés.

## Tests

- **Backend** : `api/tests/test_passkey_auto_trigger_login.py` — trusted → `passkey`, untrusted → `otp`, sans passkey → `otp`, prompt accepte les nouveaux events, unité éligibilité.
- **Flutter** : `passkey_service_test`, `login_flow_navigation_test` — verts après extension du coordinateur.

## Remaining Gaps

- **Première connexion sur device** : sans e-mail API ni cache local, l’auto-trigger ne part pas (OTP direct) — acceptable ; possible évolution : endpoint dédié ou hint masqué.
- **Double événement** : annulation coordinateur peut émettre `..._cancelled` puis `..._fallback_otp` — utile pour entonnoir analytics ; à dédoublonner côté BI si besoin.
- **Tests widget** dédiés `LoginAutoAuthScreen` (navigation mock API) : non ajoutés (coût / valeur) ; à compléter si régression fréquente.
