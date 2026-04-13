# Registration — vérification mobile SMS (écran interaction)

## Executive Summary

Le moteur d’inscription dynamique supporte désormais des écrans de type **`interaction`** en plus des écrans **`form`**. La première interaction livrée est **`phone_verification_sms`** : le numéro est lu depuis les données de session (`source_field_slug`), un challenge SMS est créé ou réutilisé via le **module 2FA existant**, le client Flutter appelle **`/api/2fa/verify`** avec un **JWT court** (`otp_token`) renvoyé par **`POST .../interaction/prepare`**, puis **`POST .../interaction/complete`** enregistre les drapeaux sur la session et autorise **`next`**. La projection vers `Person` place `phone_verified`, `phone_verified_at` et `phone_verification_channel` sous **`profile_json["compliance"]`**.

**Migration DB requise** : `098` — colonnes `screen_type`, `interaction_type`, `interaction_config_json` sur `registration_step_screens`. Commande : `cd services/arquantix/api && alembic upgrade head`.

## Interaction Screen Model

- **`screen_type`** : `form` (défaut) ou `interaction`.
- **`interaction_type`** : pour cette phase, `phone_verification_sms`.
- **`interaction_config_json`** : JSON avec au minimum `source_field_slug`, `verified_flag_slug`, `purpose` (ex. `verify_phone`, aligné sur les purposes 2FA allowlist).

Helpers et validation : `api/services/registration/interaction_helpers.py` (E.164, réutilisation de challenge pending non expiré, payload lecture seule pour `GET screen`).

## Admin Builder Changes

- API admin : `ScreenCreate` / `ScreenUpdate` + `_ser_screen` exposent `screen_type`, `interaction_type`, `interaction_config_json`.
- UI : `web/src/app/admin/registration/flows/[id]/edit/page.tsx` — choix du type d’écran, bloc violet pour la config SMS (slugs + purpose).

## Runtime Backend Changes

- **`GET .../screen`** : pour un écran interaction SMS, réponse enrichie avec `screen_type`, `interaction_type`, `interaction_config`, `interaction_payload` (lecture seule ; pas d’envoi SMS).
- **`POST .../interaction/prepare`** : assure une `Person` pour la session, réutilise un challenge pending même numéro/purpose ou crée + envoie ; retourne `otp_token`, `challenge_id`, `target_masked`, `reused`, etc.
- **`POST .../interaction/complete`** : vérifie que le challenge est **`verified`**, même personne, même cible / purpose que la config ; écrit en session `verified_flag_slug`, `phone_verified_at`, `phone_verification_channel`.
- **`POST .../submit`** : refus explicite sur écran `interaction`.
- **`POST .../next`** : tant que le flag configuré n’est pas présent / vrai sur l’écran SMS → `409` (interaction incomplète).
- **`_are_step_required_fields_present`** : prend en compte les écrans interaction SMS (flag vérifié).

Fichiers principaux : `api/services/registration/service.py`, `api/services/registration/runtime_router.py`.

## 2FA Integration

- Pas de duplication de la logique OTP : **`TwoFactorService.create_challenge` / `send_code`** et **`POST /api/2fa/verify`** inchangés dans leur rôle.
- JWT registration : `api/auth.py` — `create_registration_otp_token(person_id)` (claim `person_id`, `sub`: `registration:2fa`) ; `resolve_person_id` existant lit déjà `person_id` dans le JWT.

## Flutter Integration

- Modèles : `RegistrationScreen` parse `screen_type`, `interaction_type`, `interaction_config`, `interaction_payload`.
- API : `prepareInteraction`, `completeInteraction`.
- `RegistrationFlowScreen` : bloc « Confirmer mon numéro » → `prepare` → `TwoFactorScreen` avec `skipAutoStart`, jeton Bearer, `registrationResendPrepare`, `onVerified(challengeId)` → `completeInteraction` → rafraîchissement + `next`.
- `TwoFactorScreen` : démarrage différé / renvoi via prepare registration ; `onVerified` reçoit le `challengeId` vérifié ; pop systématique après succès.

## Data Projection

- `RegistrationSessionService._project_to_person` : les slugs détectés comme conformité (`phone_verified_at`, `phone_verification_channel`, `phone_verified`, ou `*_verified`) vont dans **`profile_json["compliance"]`** ; le reste reste dans **`collected`**.

## Tests Added

- Backend : `api/tests/test_registration_interaction_sms.py` (payload sans téléphone, prepare refusé, submit refusé, réutilisation challenge, next bloqué, complete sans verify, flux complet + projection, événement `registration.interaction.prepared`). **Nécessite la migration 098 appliquée sur la base utilisée par les tests.**
- Flutter : `mobile/test/registration/registration_models_test.dart` — parsing écran interaction.

## Remaining Gaps / Next Steps

- **Renvoi SMS** : `prepare` réutilise un challenge pending sans renvoyer de SMS ; le bouton « Renvoyer » côté Flutter rappelle `prepare` (même comportement). Pour un vrai resend avec nouveau code, prévoir un flag `force_new` ou expiration ciblée côté backend.
- **Autres `interaction_type`** : même pattern (`interaction_config` + prepare/complete dédiés ou génériques).
- **Tests E2E Flutter** : non ajoutés (pas de `dart` dans l’environnement CI local vérifié ici) ; à lancer dans le pipeline mobile.
- **i18n admin** : les libellés du builder interaction sont en anglais technique ; possibilité d’harmoniser avec le reste de l’éditeur.
