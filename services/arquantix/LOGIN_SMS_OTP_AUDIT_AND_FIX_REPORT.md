# Audit et correctifs — Login mobile SMS OTP (alignement registration / 2FA)

## 1. Root cause (pourquoi « Impossible d’envoyer le code »)

Plusieurs causes possibles, souvent **cumulées** en local :

1. **`AUTH_MOBILE_OTP_LOGIN_ENABLED`** non activé → HTTP 503, message feature désactivée.
2. **Provider SMS « noop »** sans Twilio : l’ancien code refusait **tout** envoi si `get_sms_provider().is_noop`, **même en développement**, alors que la **registration** peut utiliser le mode **relaxed** + **`FAKE_SMS_PROVIDER`**.
3. **Aucun compte admin** avec **`admin_users.mobile_e164`** renseigné → le serveur répond « accepté » (anti-énumération) **sans** créer de challenge ni envoyer de SMS ; l’utilisateur ne reçoit jamais de code.
4. **Code OTP** : le login n’utilisait pas **`TWO_FACTOR_DEV_FIXED_CODE`** ; en dev, seul un code aléatoire (hashé) était valide, ce qui complique les tests manuels.

**Correctif principal** : même **génération / hachage** que la 2FA (`sms_otp_core`), **délai de renvoi** identique à la registration (`RESEND_SECONDS` = 30 s), **FakeSmsProvider** automatique quand l’environnement est **relaxed** (tests + dev non prod-like) et que Twilio n’est pas configuré, **sans** dupliquer la logique d’envoi (toujours `SmsProvider.send_otp`).

---

## 2. Endpoints avant / après

| Rôle | Avant | Après (canonique) | Alias conservé |
|------|--------|-------------------|----------------|
| Démarrer OTP SMS login | `POST /auth/login/start` | **`POST /auth/login/sms/start`** | `POST /auth/login/start` |
| Vérifier OTP + session | `POST /auth/login/verify` | **`POST /auth/login/sms/verify`** | `POST /auth/login/verify` |

**Flutter** : appelle désormais **`/auth/login/sms/start`** et **`/auth/login/sms/verify`**.

**Rate limit middleware** : les quatre chemins ci-dessus sont traités comme les autres logins (`check_login` par IP).

---

## 3. Ce qui n’est *pas* le même moteur que la registration (et pourquoi)

- **Registration SMS** : `Person` + table **`two_factor_challenges`** + JWT court **`otp_token`** + `POST /api/2fa/verify` avec en-tête Bearer registration. **Purpose** typique : **`verify_phone`** (allowlist dans `two_factor_purposes.py`).
- **Login mobile admin** : **`AdminUser`** (JWT final admin) + table **`auth_mobile_login_otp_challenges`** + pas de `person_id` sur le challenge.

Les **deux** flux ne peuvent pas partager la même ligne en base sans migration majeure (lier admin ↔ person ou généraliser `two_factor_challenges`). En revanche, ils partagent désormais :

- **`services/security/sms_otp_core.py`** : `new_plaintext_sms_otp()` (dont **`TWO_FACTOR_DEV_FIXED_CODE`**), `hash_sms_otp`, `verify_sms_otp` — **même logique** que l’ancien `TwoFactorService._otp_plaintext_for_sms_email` / bcrypt.
- **`get_sms_provider()`** + **`send_otp(..., challenge_id=...)`** — **même provider** que la 2FA (Twilio, noop, fake).
- **`RESEND_SECONDS`** (30 s) — **même fenêtre** que le start 2FA / registration (côté création de challenge).
- **`two_factor_dev_code_for_api_exposure()`** — champ optionnel **`dev_code`** sur la réponse **start** (si `TWO_FACTOR_DEV_EXPOSE_CODE`).

---

## 4. Payload téléphone (Flutter / backend)

- **Attendu** : E.164 avec **`+`**, ex. `+33651624864`.
- **Backend** : `_normalize_phone_e164` supprime les espaces, assure un préfixe `+`.
- **Flutter** : `LoginPhoneScreen` utilise **`normalizePhoneFieldToE164`** + indicatif pays — à garder aligné avec l’inscription (même principe E.164).

---

## 5. Correctifs backend (fichiers)

| Fichier | Changement |
|---------|------------|
| **`services/security/sms_otp_core.py`** | **Nouveau** — OTP SMS partagé (dev fixed + aléatoire, bcrypt). |
| **`services/security/two_factor_service.py`** | Délègue génération / hash / verify à **`sms_otp_core`**. |
| **`services/auth/mobile_otp_login_routes.py`** | Fake SMS si **noop + relaxed** ; **RESEND_SECONDS** ; anti-spam renvoi ; erreurs **`detail: { code, message }`** ; **`dev_code`** optionnel ; routes **`/login/sms/*`** + alias legacy. |
| **`services/auth/auth_rate_limit_middleware.py`** | Inscription des chemins **`/auth/login/sms/*`**. |
| **`tests/test_two_factor_api.py`**, **`test_fake_sms_provider.py`**, **`test_registration_interaction_sms.py`** | Patch **`new_plaintext_sms_otp`** au lieu de **`_generate_numeric_code`**. |
| **`tests/test_mobile_sms_login_otp.py`** | **Nouveau** — skip si migration **`mobile_e164`** absente. |

---

## 6. Correctifs Flutter

| Fichier | Changement |
|---------|------------|
| **`passkey_api.dart`** | URLs **`/auth/login/sms/start`** & **`/verify`** ; **`parseFastApiErrorMessage`** pour lire `detail.message`. |
| **`login_otp_screen.dart`** | Messages d’erreur depuis l’API ; compte à rebours défaut **30 s** ; resend / start / verify enrichis. |

**UI OTP** : inchangé fonctionnellement — toujours **`AppSmsOtpVerificationBlock`** (même **`AppOtpInput`** que l’inscription).

---

## 7. Erreurs HTTP / codes `detail.code`

| Code | HTTP | Message utilisateur (exemple) |
|------|------|-------------------------------|
| `feature_disabled` | 503 | Connexion par SMS désactivée sur ce serveur. |
| `sms_unavailable` | 503 | Envoi SMS indisponible (Twilio / FAKE_SMS_PROVIDER en dev). |
| `resend_rate_limited` | 429 | Patienter 30 s avant de redemander un code. |
| `invalid_or_expired_code` | 401 | Code incorrect ou expiré. |
| `too_many_attempts` | 401 | Trop de tentatives. |

---

## 8. Tests

- **Backend** : `tests/test_mobile_sms_login_otp.py` (skip automatique si **`admin_users.mobile_e164`** absent — exécuter **`alembic upgrade head`** pour les activer).
- **Flutter** : `test/features/security/login/login_otp_screen_test.dart` (inchangé côté chemins HTTP si les mocks pointent vers la même API ; les tests utilisent un **`PasskeyApi`** factice).

---

## 9. Checklist exploitation / QA locale

1. `AUTH_MOBILE_OTP_LOGIN_ENABLED=true`
2. Migration appliquée : **`admin_users.mobile_e164`** + **`auth_mobile_login_otp_challenges`**
3. Renseigner **`mobile_e164`** sur l’admin à tester
4. Dev : **`FAKE_SMS_PROVIDER=true`** *ou* laisser le **fallback relaxed** utiliser Fake sans Twilio
5. Optionnel : **`TWO_FACTOR_DEV_FIXED_CODE=123456`** (+ éventuellement **`TWO_FACTOR_DEV_EXPOSE_CODE=true`**) pour voir le code dans la réponse JSON **`dev_code`**

---

## 10. Purpose 2FA (réponse audit « login_sms »)

- Le **login SMS admin** **n’utilise pas** la table **`two_factor_challenges`** ni l’endpoint **`/api/2fa/start`** avec un purpose dédié.
- Les purposes SMS **autorisés** pour la 2FA classique restent dans **`ALLOWED_PURPOSES`** (`verify_phone`, `login`, etc.) ; un **`login_sms`** distinct **n’a pas été ajouté** car le flux admin est hors **Person** / **`two_factor_challenges`**.

Si à terme le produit unifie **identité client (Person)** et login app mobile sur le **même** modèle que la registration, il faudra une évolution schema (challenge lié à `person_id` + endpoint public contrôlé anti-enum).
