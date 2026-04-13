# Rapport d’implémentation — Registration EU + convergence login (Arquantix)

**Date :** 2026-04-03  
**Périmètre :** intégration inscription mobile (SMS signup) avec session existante, PIN, registration engine authentifié ; sans dupliquer OTP/passcode.

---

## 1. Executive summary

### Ce qui a été livré

- **API** : nouveaux endpoints `POST /auth/signup/sms/start` et `POST /auth/signup/sms/verify` créant une **Person** (juridiction `EU`) et un **AdminUser** avec e-mail placeholder `@signup.internal`, `mobile_e164` unique, et `admin_users.person_id` pointant vers la personne.
- **Anti-doublon** : si un compte existe déjà pour le mobile, `signup/sms/start` répond **403** avec `detail.code = signup_phone_unavailable` et un message **générique** (pas de formulation du type « ce numéro existe déjà »).
- **JWT** : claim optionnelle **`pid`** (UUID person) dans l’access token lorsque `admin_users.person_id` est défini (émission session via `_issue_pair_for_session_row`).
- **Registration** : `POST /api/registration/sessions/start` accepte un **Bearer optionnel** ; si présent, `person_id` est forcé depuis `admin_users.person_id` (le `person_id` du corps est ignoré pour éviter l’usurpation).
- **Flutter** : depuis **Login0**, « Créer un compte » ouvre **`LoginPhoneScreen(signUpMode: true)`** (même UX mobile que la connexion) → OTP réutilise **`LoginOtpScreen`** avec **`/auth/signup/sms/verify`** → **`PostLoginLocalSecurityFlow`** (PIN) → si flag secure storage, après création du PIN, **`RegistrationFlowScreen(jurisdiction: 'EU')`** au lieu du shell.
- **`RegistrationApi`** : envoie **`Authorization: Bearer`** via `SessionService.readAccessToken` pour lier la session d’inscription au **même** `Person` que le compte créé au signup.

### Ce qui reste en gap (hors ce lot)

- **Flow produit à 13 étapes** (DOB séparé, e-mail + OTP e-mail skippable, T&Cs seuls, etc.) : le **contenu** du flow EU en base (seed **085**) n’a pas été réécrit écran par écran dans cette itération ; le moteur existant continue de servir le flow configuré en DB.
- **OTP e-mail** optionnel / **skip** : non branché.
- **Progression canonique** détaillée (`mobile_collected`, …) : partiellement couverte par le produit (signup + flag `pending_eu_registration_after_passcode` + registration engine) ; pas d’endpoint dédié « registration_stage » côté API dans ce lot.

---

## 2. Flow final implémenté (utilisateur)

1. **Login0** → « **Créer un compte** » → **`LoginPhoneScreen(signUpMode: true)`** (même écran que connexion).
2. **SMS** : `POST /auth/signup/sms/start` → saisie code → `POST /auth/signup/sms/verify` → jetons stockés (`SessionService.storeTokens`).
3. **Flag** : `setPendingEuRegistrationAfterPasscode(true)` puis **`PostLoginLocalSecurityFlow`** → setup **PIN** (écran existant `PasscodeSetupScreen` via route nommée).
4. Après PIN : si le flag est consommé → **`RegistrationFlowScreen(jurisdiction: 'EU')`** avec appels registration **authentifiés** ; sinon comportement inchangé → **shell** via `AppEntryBootstrap`.

**Dev** : code SMS fixe inchangé côté login (`TWO_FACTOR_DEV_FIXED_CODE`, ex. `123456` en tests existants).

---

## 3. Choix d’architecture registration + login

| Sujet | Décision |
|--------|----------|
| OTP mobile inscription | **Même** primitive que login (`AuthMobileLoginOtpChallenge`, `sms_otp_core`) ; chemins d’API distincts `/auth/signup/sms/*` pour **créer** compte au lieu d’exiger un utilisateur existant. |
| Passcode / session | **Aucun** second système : réutilisation de **`PostLoginLocalSecurityFlow`** et **`PasscodeSetupScreen`**. |
| Lien User / Person | **`admin_users.person_id`** (FK vers `persons`, unique) — migration **120**. |
| Registration session | **`person_id`** aligné sur l’utilisateur connecté via JWT optionnel sur **`sessions/start`**. |
| Navigation post-PIN | **Secure storage** : clé `pendingEuRegistrationAfterPasscode` (consommée une fois dans `PasscodeSetupScreen`). |

---

## 4. Duplicate mobile sans fuite RGPD (arbitrage)

- **Start signup** : si `AdminUser.mobile_e164` existe déjà → **403** + `signup_phone_unavailable` + message générique imposant « Me connecter » ou autre numéro **sans** dire explicitement « compte existant ».
- **Limite** : l’existence d’un compte peut toujours être **inférée** par des canaux auxiliaires (ex. réception ou non de SMS selon scénario) ; un durcissement ultérieur peut passer par **timing constant** ou **captcha** (hors scope ici).

---

## 5. Réutilisations

- **`LoginPhoneScreen`**, **`LoginOtpScreen`**, **`PasskeyApi`**, **`SessionService`**, **`PostLoginLocalSecurityFlow`**, **`PasscodeSetupScreen`**, **`RegistrationFlowScreen`**, **`RegistrationFlowRenderer`**, moteur registration backend inchangé dans son principe.

---

## 6. Fichiers modifiés / ajoutés (principaux)

| Zone | Fichiers |
|------|----------|
| API | `services/auth/signup_mobile_routes.py` (**nouveau**), `main.py`, `auth_rate_limit_middleware.py`, `auth.py` (`get_optional_user_for_registration`), `services/registration/runtime_router.py`, `services/auth/refresh_session.py`, `database.py`, `alembic/versions/120_admin_users_person_id.py` |
| Tests API | `tests/test_signup_mobile_sms.py` (**nouveau** ; skip si schéma sans colonnes) |
| Flutter | `welcome_landing_screen.dart`, `login_phone_screen.dart`, `login_otp_screen.dart`, `passkey_api.dart`, `session_service.dart`, `passcode_storage_keys.dart`, `passcode_setup_screen.dart`, `registration_flow_screen.dart`, `registration_api.dart` |

---

## 7. Étapes de progression retenues (produit / tech)

| Étape logique | Réalisation |
|---------------|-------------|
| `mobile_collected` | Saisie + envoi SMS signup |
| `mobile_verified` | `signup/sms/verify` OK |
| `passcode_created` | PIN enregistré localement |
| `session_initialized` | Jetons + refresh comme login |
| `registration_in_progress` | `RegistrationFlowScreen` + session engine |
| `registration_completed` | `POST .../complete` (inchangé) |

---

## 8. Gaps restants & recommandations

1. **Réordonnancer / scinder** le flow EU en DB pour coller au cahier (nom+prénom, DOB, pays prérempli depuis indicatif mobile, adresse Places, e-mail, OTP e-mail skippable, CGU).
2. **Hook** post-`complete` : ex. `kyc_status = pending`, création **pe_client** si produit l’exige.
3. **Tests d’intégration Flutter** : navigation Login0 → signup → PIN → registration (golden / integration).
4. **JWT `pid`** : exploiter côté client pour affichage/debug si besoin ; l’autorité serveur reste `admin_users.person_id`.

---

## 9. Migration base

Appliquer **`alembic upgrade head`** pour **`120_admin_users_person_id`** avant déploiement.

---

*Fin du rapport.*
