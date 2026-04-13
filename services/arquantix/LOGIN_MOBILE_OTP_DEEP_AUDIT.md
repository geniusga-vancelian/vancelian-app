# Audit profond — Login mobile + OTP 2FA (admin)

**Date (contexte repo)** : avril 2026  
**Auditeur** : revue statique du code + tests automatisés (pas d’audit infra prod).  
**Ton** : sévère, factuel ; distinction **confirmé** / **probable** / **à vérifier**.

---

## Executive Summary

Le flux **téléphone → `POST /auth/login/sms/start` → écran OTP 6 chiffres → `POST /auth/login/sms/verify` → `issue_fresh_auth_session`** est **fonctionnellement cohérent** et **réutilise** `sms_otp_core`, les providers SMS, `issue_fresh_auth_session`, le middleware de rate limit auth, et côté Flutter `AppPhoneInput`, `AppSmsOtpVerificationBlock` / `AppOtpInput` (aligné registration).

**Points critiques identifiés :**

1. **Confirmé** : avant correctif, la vérification SMS **ne vérifiait pas** `security_account_locked_until`, contrairement au login mot de passe (`perform_login` appelle `_assert_user_not_security_locked`). **Même écart** que le login admin **e-mail OTP** (`admin_email_otp_routes.py`).  
   → **Correctif appliqué** : assertion sur compte verrouillé **après** succès OTP, avant émission de session (voir section *Fixes Applied*).

2. **Confirmé** : le login SMS fixe `device_trust_level=DEVICE_TRUST_TRUSTED` et `auth_strength="otp"` **sans** parcours d’attestation WebAuthn — **moins fort** que passkey (`auth_strength="passkey"`), **équivalent** au login e-mail OTP admin. Ce n’est pas un « bypass » du pipeline session : `issue_fresh_auth_session` applique toujours réputation appareil, fingerprint, audit, etc.

3. **Probable** : **fuite timing** sur `start` : numéro connu déclenche envoi SMS (latence réseau) ; numéro inconnu répond vite sans SMS. L’API reste **uniforme en JSON** (200 + `masked_target`), mais le timing peut aider à inférer l’existence d’un compte.

4. **À vérifier** (hors scope code seul) : chargement réel des variables d’environnement par le **processus** uvicorn, politique réseau / pare-feu, et non-régression sur déploiements ECS.

**Verdict final** : architecture **globalement saine** (pas de stack OTP parallèle pour la génération/hachage SMS), sécurité **alignée OTP admin** avec **une lacune corrigée** sur le verrouillage compte ; niveau de confiance **élevé pour le dev/test**, **moyen-élevé pour prod** sous réserve de config stricte `APP_ENV`, désactivation des flags dev OTP, et SMS réel.

---

## Scope Audited

| Zone | Fichiers / zones principales |
|------|------------------------------|
| Backend SMS login | `api/services/auth/mobile_otp_login_routes.py` |
| OTP partagé | `api/services/security/sms_otp_core.py`, `two_factor_service.py`, `two_factor_env.py` |
| Session | `api/services/auth/refresh_session.py` (`issue_fresh_auth_session`, `_auth_audit`) |
| Rate limit | `api/services/auth/auth_rate_limit_middleware.py`, `auth_rate_limit.py` |
| Modèle | `api/database.py` (`AdminUser.mobile_e164`, `AuthMobileLoginOtpChallenge`) |
| Flutter | `login_phone_screen.dart`, `login_otp_screen.dart`, `passkey_api.dart`, `secure_api_config.dart`, DS OTP |
| Tests | `api/tests/test_mobile_sms_login_otp.py`, tests Flutter login OTP |

---

## Real Flow Observed

### Backend — routes et contrat

| Étape | Méthode | Route canonique | Alias legacy |
|-------|---------|-----------------|--------------|
| Start | `POST` | `/auth/login/sms/start` | `/auth/login/start` |
| Verify | `POST` | `/auth/login/sms/verify` | `/auth/login/verify` |

**Start — requête**

```json
{ "phone": "+33612345678" }
```

**Start — réponse 200 (connu ou inconnu)**

- `status`: `"accepted"`
- `masked_target`: string (masquage affichage ; inconnu = masque du numéro demandé)
- `resend_after_seconds`: entier (`RESEND_SECONDS`)
- `dev_code`: optionnel si `TWO_FACTOR_DEV_EXPOSE_CODE` + env non prod-like

**Comportement confirmé**

- Numéro **inconnu** : pas de ligne `AuthMobileLoginOtpChallenge`, pas d’envoi SMS, audit `auth.mobile_login.otp.start_unknown_phone`.
- Numéro **connu** : challenge unique par téléphone (delete ancien), OTP via `new_plaintext_sms_otp` + `hash_sms_otp`, TTL `SMS_CODE_TTL_MINUTES` (5), envoi `sms.send_otp`, audit `auth.mobile_login.otp.started`.

**Verify — requête**

```json
{ "phone": "+336...", "code": "123456" }
```

En-têtes : `X-Device-ID` (optionnel côté API → `legacy-unknown`), Flutter envoie aussi `X-Device-Fingerprint` JSON (consommé dans `issue_fresh_auth_session` si activé).

**Verify — réponse 200**

```json
{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }
```

(aligné autres logins via `_issue_pair_for_session_row`.)

**Erreurs typiques** : 401 `invalid_or_expired_code`, `too_many_attempts` ; 429 `resend_rate_limited` ; 503 feature off / SMS noop hors relaxed.

### Flutter — écrans et navigation

1. **`LoginPhoneScreen`** : `AppPhoneInput`, bouton Continuer avec chargement (`AppPrimaryButton.isLoading`), appel `PasskeyApi.mobileLoginStart`, puis push `LoginOtpScreen(phoneE164, smsStartResult: data)`.
2. **`LoginOtpScreen`** : si `smsStartResult` présent, pas de second `start` au montage ; `AppSmsOtpVerificationBlock` + `onCompleted` → `mobileLoginVerify` ; tokens → `SessionService.storeTokens` ; `pop(true)`.
3. Erreurs vérif : **SnackBar** flottante ; état `wrongCode` pour bordures rouges OTP.

**Confirmé** : pas d’étape e-mail obligatoire dans le fil principal mobile ; fallbacks via sheets.

---

## Backend Audit

### Validation & E.164

- **Confirmé** : normalisation `_normalize_phone_e164` — trim, espaces supprimés, préfixe `+` si absent.
- **À vérifier** : pas de validation stricte « vrai » E.164 (longueur/plan de numérotation) au-delà de `min_length` Pydantic côté login — **cohérent** avec beaucoup de flux téléphone existants.

### Lookup & anti-énumération

- **Confirmé** : réponse **200** + même forme pour connu/inconnu au `start` ; inconnu **ne crée pas** de challenge.
- **Probable** : timing (voir Executive Summary).

### Challenge

- **Confirmé** : table dédiée `auth_mobile_login_otp_challenges`, unique sur `phone_e164_normalized`.
- **Confirmé** : expiration, `attempt_count` max `SMS_MAX_VERIFY_ATTEMPTS`, suppression après succès ou échec fatal.
- **Confirmé** : renvoi : second `start` dans la fenêtre `RESEND_SECONDS` → **429** ; sinon delete + nouveau challenge.

### Session

- **Confirmé** : `issue_fresh_auth_session` avec `auth_strength="otp"`, `device_trust_level=DEVICE_TRUST_TRUSTED`, fingerprint/IP/UA, réputation appareil si activée, audit `auth.mobile_login.otp.succeeded`.

### Réutilisation moteur OTP / SMS

- **Confirmé** : `new_plaintext_sms_otp`, `hash_sms_otp`, `verify_sms_otp` depuis **`sms_otp_core`** (même module que `TwoFactorService` pour SMS).
- **Confirmé** : `TWO_FACTOR_DEV_FIXED_CODE` / `two_factor_dev_code_for_api_exposure` via `two_factor_env` — **désactivés** en env `production`/`prod`/`staging` (confirmé dans le code).

---

## Security Audit

### Anti-énumération

- **Confirmé** : JSON uniforme au start.
- **Probable** : timing + éventuellement 429 uniquement si challenge existant (comportement différent d’un numéro jamais sollicité — **mineur**).

### OTP

- **Confirmé** : 6 chiffres, bcrypt sur stockage, TTL 5 min, max tentatives, invalidation après succès.
- **Confirmé** : rate limit middleware sur `POST` login SMS (bucket IP partagé avec autres `/auth/login*`).

### Session & zero trust

- **Confirmé** : pas de court-circuit de `issue_fresh_auth_session` (réputation, fingerprint, audit).
- **Confirmé** : **pas** d’évaluation attestation sur ce flux (comme e-mail OTP) — **plus faible** que passkey+mot de passe+attestation, **documenté**.

### Dev / prod-like safety

- **Confirmé** : `two_factor_dev_fixed_code()` retourne `None` si `APP_ENV`/`ARQUANTIX_ENV` production-like.
- **Confirmé** : `FakeSmsProvider` seulement si `is_two_factor_relaxed` (test, non prod-like, `TWO_FACTOR_RELAXED`, `PYTEST_CURRENT_TEST`).
- **À vérifier** : équipes ne doivent **pas** laisser `APP_ENV=staging` avec `TWO_FACTOR_DEV_FIXED_CODE` pour des données réelles — le code **désactive** le fixed code en staging (**confirmé** dans `two_factor_env.py`).

### Admin surface

- **Confirmé** : login SMS lié à `AdminUser.mobile_e164` — comptes **admin** ; feature flag `AUTH_MOBILE_OTP_LOGIN_ENABLED`.

### Logging / SIEM

- **Confirmé** : `_auth_audit` → log structuré + `persist_auth_security_event` si activé ; métadonnées avec **téléphone masqué** (`mask_phone_e164`), pas de code OTP en clair dans les audits listés.

### Lacune corrigée (verrouillage compte)

- **Confirmé (avant fix)** : absence de `_assert_user_not_security_locked` avant session — **écart** vs `perform_login`.
- **Après fix** : assertion immédiatement avant `issue_fresh_auth_session` (détails en *Fixes Applied*).

---

## Flutter / UX / DS Audit

### Cohérence DS / registration

- **Confirmé** : `AppPhoneInput`, `AppSmsOtpVerificationBlock` → `AppOtpInput` (même bloc que registration, documenté dans le DS).
- **Confirmé** : `AppPageTitle`, `AppTopNavBar`, `AppPrimaryButton`, `AppSpacing` / `AppColors`.
- **Probable** : titre « Connexion » sur OTP vs textes registration — **acceptable** ; hiérarchie proche.

### Flow logique

- **Confirmé** : mobile → OTP direct après `start` réussi ; chargement sur bouton Continuer puis navigation.

### Erreurs UX

- **Confirmé** : erreurs vérif en SnackBar (moins intrusive que texte sous titre).
- **Probable** : messages backend parfois en anglais (rate limit) — **mineur** (`parseFastApiErrorMessage` améliore une partie).

### Niveau « Revolut-like »

- **Non conforme** (aspirationnel) : pas d’analyse biométrique / device binding obligatoire au-delà des en-têtes existants ; **hors scope** sans produit cible.

---

## Environment / Data Audit

**Méthode** : lecture code + migrations ; **pas** d’exécution sur la machine de l’utilisateur dans ce document.

- **Confirmé** : migration **117** (schéma `admin_users.mobile_e164`, table challenges) requise — tests skip si colonne absente.
- **À vérifier** : valeurs réelles en base (`mobile_e164` strictement E.164), et **process** uvicorn charge `.env` (reload-include dans scripts).
- **À vérifier** : `AUTH_MOBILE_OTP_LOGIN_ENABLED`, `APP_ENV`, `TWO_FACTOR_*` sur l’environnement cible.

---

## Tests Reviewed / Added

### Backend (`test_mobile_sms_login_otp.py`)

- **Confirmé** : start+verify succès, alias legacy, inconnu sans challenge, mauvais code, resend 429, challenge expiré, feature off 503, reset rate limiter entre tests.
- **Ajouté (avec fix)** : utilisateur avec `security_account_locked_until` futur → verify doit répondre **403** (voir implémentation).

### Flutter

- **Confirmé** : tests `login_otp_screen_test.dart` (OTP valide, invalide, renvoi, `smsStartResult`), navigation login phone.

---

## Red Flags

| ID | Sévérité | Description | Statut |
|----|----------|-------------|--------|
| R1 | Haute | Session OTP SMS sans contrôle verrouillage compte (vs password) | **Corrigé** (mobile SMS verify) |
| R2 | Moyenne | Timing start connu vs inconnu | **Ouvert** (mitigation complexe) |
| R3 | Info | `DEVICE_TRUST_TRUSTED` + pas d’attestation — surface plus large que passkey | **Accepté** (cohérent e-mail OTP) |
| R4 | Info | Alias legacy `/auth/login/start` | **Documenté** — préférer chemins `/sms/*` |
| R5 | Moyenne | **Même lacune verrou** sur `admin_email_otp_verify` | **Recommandation** — aligner dans un PR séparé |

---

## Fixes Applied

1. **`mobile_otp_login_routes.py`** : import et appel **`_assert_user_not_security_locked(user)`** après validation OTP et résolution `AdminUser`, **avant** `issue_fresh_auth_session`.
2. **`api/tests/test_mobile_sms_login_otp.py`** : test **`test_verify_forbidden_when_security_account_locked`** (403, code `security.account_locked`).

---

## Final Verdict

| Critère | Verdict |
|---------|---------|
| Architecture | **Saine** — réutilisation `sms_otp_core`, session unique, pas de duplicate logique OTP SMS côté hash/generate. |
| Sécurité | **Intacte avec réserve** — correctif verrou compte appliqué sur flux SMS ; attestation toujours absente (comme e-mail OTP) ; timing start à surveiller. |
| Confiance flux mobile | **Élevée** en dev/test avec tests ; **prod** dépend de config, SMS réel, et alignement ops. |

---

## Remaining Risks / Recommendations

1. Aligner **`admin_email_otp_verify`** sur la même assertion verrou compte (parité admin).
2. Envisager **mitigation timing** (délai minimum constant côté start) si menace énumération stricte.
3. Documenter opérationnellement : **désactiver** `AUTH_MOBILE_OTP_LOGIN_ENABLED` si le produit n’expose pas ce login.
4. Vérifier **SIEM** : que les `event_type` `auth.mobile_login.otp.*` sont bien ingérés et corrélés.
5. Flutter : tests d’intégration optionnels **phone → mock API → OTP** (au-delà des tests widget actuels).
