# REGISTRATION_PHONE_VERIFICATION_E2E — Rapport

## Executive Summary

Mise en place d’un **parcours E2E backend** documenté et testé pour l’inscription avec écran **`phone_verification_sms`** : saisie téléphone, **prepare**, vérification **`/api/2fa/verify`** avec le code fixe **`111111`**, **completeInteraction**, **next**, puis **complete session** et contrôle de la **projection** (`compliance` + `collected`). Le transport SMS est **simulé** via **`FAKE_SMS_PROVIDER`** ; aucun mock sur la génération OTP dans ce test. Correction **critique** : le canal **SMS** dans `TwoFactorService.create_challenge` utilisait encore `_generate_numeric_code()` au lieu de **`_otp_plaintext_for_sms_email()`**, ce qui empêchait `TWO_FACTOR_DEV_FIXED_CODE` de s’appliquer aux flux registration SMS.

## Test Environment

Fichier : `api/tests/test_registration_phone_verification_e2e.py`

- `APP_ENV=development` (fixture + override de `test_app` pour qu’elle s’applique **avant** `create_app`, sinon `load_dotenv` peut réinjecter une prod depuis `.env`).
- `TWO_FACTOR_RELAXED=true`, `TWO_FACTOR_DEV_FIXED_CODE=111111`, `TWO_FACTOR_DEV_EXPOSE_CODE=true`, `FAKE_SMS_PROVIDER=true`, `TWO_FACTOR_REQUIRE_AUTH=false`.
- Flow seed dédié : juridiction **`E2E_SMS01`** (≤ 10 car.), écrans `phone_entry` → `phone_verification_sms` → `post_sms_done`.

Vérifications explicites : `reused is False`, hash OTP cohérent avec `111111`, `httpx.Client` (Twilio) **non** appelé, challenge **pending** puis **verified**, champs session et projection personne.

## Backend E2E Flow

1. `POST /api/registration/sessions/start`  
2. `POST .../submit` avec `phone_number` E.164  
3. `GET .../screen` → écran interaction  
4. `POST .../interaction/prepare` → `challenge_id`, `otp_token`, `dev_code`  
5. `POST /api/2fa/verify` avec Bearer = `otp_token`  
6. `POST .../interaction/complete`  
7. `POST .../next` → écran `post_sms_done`  
8. `POST .../complete` → projection  

Événements d’exécution attendus : `INTERACTION_PREPARED`, `INTERACTION_COMPLETED`, `NAVIGATION_NEXT`.

## Flutter Rendering

- **`RegistrationPhoneSmsOtpPanel`** : en **`kDebugMode`**, texte d’aide *Dev — test OTP 111111 when API uses TWO_FACTOR_DEV_FIXED_CODE=111111* (jamais en release).
- Test widget : `mobile/test/registration/registration_phone_sms_otp_panel_test.dart` vérifie la présence de **`111111`** une fois l’OTP affiché.

## Session / Person Verification

Après **completeInteraction** : `phone_verified`, `phone_verified_at`, `phone_verification_channel=sms` en session.  
Après **complete session** : `profile_json["compliance"]` et `collected.phone_number` conformes au runbook.

## Runbook

Voir **`REGISTRATION_PHONE_VERIFICATION_E2E_RUNBOOK.md`** (variables, commandes API/Flutter, scénario manuel, assertions DB/UI).

## Remaining Gaps / Next Steps

- **`dev_code`** sur **prepare** peut encore afficher le code fixe même si un challenge **réutilisé** avait été généré avec un autre OTP (voir discussion produit / durcissement éventuel).
- **Widget test** du **`RegistrationFlowScreen`** complet (téléphone → OTP → next) reste optionnel : plus lourd (navigation + API fake) ; le runbook couvre le smoke manuel.
- Aligner la doc **`TWO_FACTOR_DEV_FIXED_CODE_REPORT.md`** si besoin pour préciser explicitement que **SMS et email** passent par `_otp_plaintext_for_sms_email()`.
