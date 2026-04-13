# Executive Summary

Audit **statique du dépôt** (API FastAPI + app Flutter `services/arquantix/mobile`) sur le **login e-mail OTP** et les **passkeys** en environnement de développement.

**Confirmé :**

- Le flux e-mail OTP **n’utilise pas** `TWO_FACTOR_DEV_FIXED_CODE` ni le moteur SMS (`sms_otp_core` / `two_factor_dev_fixed_code`). Le code e-mail admin est généré par `secrets` dans `admin_email_otp_routes.py` et vérifié par hachage bcrypt — **logique séparée** du SMS OTP.
- Sans **fournisseur e-mail réel** (`SES_FROM_EMAIL` / `AWS_SES_FROM`), `get_email_provider()` retourne un **NoopEmailProvider** ; `POST /auth/login/email-otp/start` répond **503** (« Email delivery is not configured ») — **cause directe probable** des échecs d’envoi en dev si seules les variables SMS/2FA sont renseignées.
- Le flag **`AUTH_MOBILE_OTP_LOGIN_ENABLED`** contrôle le **login SMS mobile**, pas l’e-mail OTP. L’e-mail OTP dépend de **`AUTH_ADMIN_EMAIL_OTP_ENABLED`** (`webauthn_config.is_admin_email_otp_enabled` / lecture brute `AUTH_ADMIN_EMAIL_OTP_ENABLED`).
- **`TWO_FACTOR_DEV_EXPOSE_CODE`** alimente l’exposition JSON du code **côté API 2FA générique** (`two_factor_env.two_factor_dev_code_for_api_exposure`) — **sans lien** avec `admin_email_otp_routes.py`.
- Les passkeys côté Flutter échouent avec **`PasskeyUnavailableException`** si `PasskeyPlatformProvider.isAvailable` est faux (simulateur, plateforme sans support, stub desktop/web) ou si le plugin lève `DeviceNotSupportedException` / équivalent — **comportement attendu** dans plusieurs contextes dev, **sans** preuve d’un bug unique « dev » sans analyse runtime.

**Non vérifié dans cet audit :** exécution sur un device/simulateur précis, logs réseau réels, contenu exact du `.env` local (hors références code).

---

# Email OTP Flow Audit

## Endpoints (backend)

| Méthode | Chemin | Rôle |
|---------|--------|------|
| `POST` | `/auth/login/email-otp/start` | Utilisateur connu (`AdminUser.email`), stratégie login, création challenge `AuthAdminEmailOtpChallenge`, envoi e-mail |
| `POST` | `/auth/login/email-otp/verify` | Vérifie code bcrypt, supprime challenge, **`issue_fresh_auth_session`** (JWT access/refresh) |

**Confirmé :** pas d’endpoint **`resend`** dédié. Le **renvoi** côté Flutter = **rappeler `start`** (`LoginEmailOtpScreen._onResend` → `_sendCode` → `adminEmailOtpStart`).

## Endpoints (Flutter)

| Appel | Méthode API |
|-------|-------------|
| `PasskeyApi.adminEmailOtpStart` | `POST` `/auth/login/email-otp/start`, JSON `{"email":...}` |
| `PasskeyApi.adminEmailOtpVerify` | `POST` `/auth/login/email-otp/verify`, JSON `email` + `code`, en-têtes `X-Device-ID` / fingerprint |

**Fichiers :** `mobile/lib/features/security/passkeys/data/passkey_api.dart`, `mobile/lib/features/security/login/presentation/login_email_otp_screen.dart`.

## Finalisation backend

| Aspect | Statut | Détail |
|--------|--------|--------|
| Routes enregistrées | **Confirmé** | `api/main.py` inclut `admin_email_otp_router` |
| Persistance challenge | **Confirmé** | table `auth_admin_email_otp_challenges` (migration Alembic référencée) |
| Session après verify | **Confirmé** | `issue_fresh_auth_session` dans `admin_email_otp_verify` |
| « Admin » dans le nom | **Confirmé** | modèle **`AdminUser`** ; pas de route distincte « mobile user » pour ce flux — **même table** que le reste du back-office auth audité |

## Moteur OTP

| Question | Réponse |
|----------|---------|
| Réutilise-t-il `TwoFactorService` / SMS ? | **Non** — génération `_generate_code()` + bcrypt dans `admin_email_otp_routes.py` |
| Réutilise-t-il `sms_otp_core.new_plaintext_sms_otp` ? | **Non** |

---

# Email OTP Dev Mode Audit

## `TWO_FACTOR_DEV_FIXED_CODE=111111`

| Question | Réponse factuelle |
|----------|-------------------|
| S’applique-t-il à l’e-mail OTP admin ? | **Non** — le code e-mail est tiré par `_generate_code()` (aléatoire 6 chiffres), pas par `two_factor_dev_fixed_code()`. |
| Pourquoi ? | **Confirmé** : aucune lecture de `TWO_FACTOR_DEV_FIXED_CODE` dans `admin_email_otp_routes.py`. |

## `TWO_FACTOR_DEV_EXPOSE_CODE=true`

| Question | Réponse |
|----------|---------|
| Expose-t-il le code e-mail admin dans une réponse JSON ? | **Non** — `AdminEmailOtpStartResponse` ne contient pas de champ `dev_code` ; l’exposition documentée est dans `two_factor_env.py` pour le **canal 2FA générique**. |

## Fournisseur e-mail

| Condition | Comportement |
|-----------|----------------|
| Ni `SES_FROM_EMAIL` ni `AWS_SES_FROM` | `get_email_provider()` → **`NoopEmailProvider`** (`email_provider.py`) |
| `prov.is_noop` sur `start` | **503** avant création challenge utile — message « Email delivery is not configured » |

## Alignement dev « comme le mobile »

Pour **aligner** l’e-mail OTP sur le mobile en dev **sans dupliquer tout le moteur**, il faudrait **un mécanisme explicite** (ex. branche dev dans `admin_email_otp_start` : code fixe + skip SES, ou injection du même `two_factor_dev_fixed_code()` dans la génération **et** la persistance bcrypt). **Aujourd’hui ce mécanisme n’existe pas** dans le fichier audité.

---

# Passkey Dev Readiness Audit

## Pourquoi « passkey indisponible » (UI)

**Confirmé (Flutter) :** le texte **« Passkey indisponible. Utilisez le code reçu par e-mail. »** est affiché dans le **`onFallback`** de `PasskeyLoginCoordinator.signInWithPasskey` (`login_email_fallback_screen.dart`), appelé pour :

- `PasskeyUnavailableException` (plateforme / `isAvailable` faux / device non supporté),
- annulation utilisateur,
- échec authentificateur / API,
- etc.

Ce n’est **pas** un libellé spécifique « dev » ; c’est le **repli générique** vers OTP e-mail.

## Chaîne technique passkey

1. **`PasskeyService.loginWithPasskey`** : si `!await _provider.isAvailable` → **`PasskeyUnavailableException`** (`passkey_service.dart`).
2. **iOS / Android** : `passkey_platform_provider_factory_io.dart` — **stub** sur web / desktop non iOS-Android.
3. **Disponibilité** : `IOSPasskeyProvider` / `AndroidPasskeyProvider` interrogent `PasskeyAuthenticator.getAvailability()` — **peut être faux** sur simulateur ou appareil sans support (`passkey_native_provider.dart`).

## Backend

- **`AUTH_PASSKEYS_ENABLED`** (défaut traité comme activé sauf `false` explicite) — `webauthn_config.is_passkeys_enabled`.
- Éligibilité auto-trigger : `passkey_login_eligibility.py`, orchestrateur `adaptive_auth_orchestrator.py` — **hors scope détail** de cet audit ; pas d’assertion « trop strict » sans scénario reproduit.

## Normal vs bug

| Situation | Verdict |
|-----------|---------|
| Simulateur iOS sans passkey | **Probable** : `isAvailable` → false — **normal** pour le support plateforme. |
| Desktop Flutter / web build | **Confirmé** : stub → **indisponible** — **attendu**. |
| RP ID / Associated Domains incorrects | **Probable** : erreurs type `DomainNotAssociatedException` mappées vers **`PasskeyAuthenticatorFailureException`** (pas toujours « Unavailable ») — **à vérifier** avec logs runtime. |

---

# Flutter / UX Audit

| Écran | Cohérence |
|-------|-----------|
| `LoginEmailFallbackScreen` | DS (AppPageTitle, AppTextInput, AppPrimaryButton) ; passkey + navigation OTP |
| `LoginEmailOtpScreen` | `AppSmsOtpVerificationBlock` réutilisé (OTP 6 chiffres) ; post-login **`PostLoginLocalSecurityFlow.navigateReplacingLoginStack`** — **aligné** secure gate |
| Erreur 503 start | Message inline : connexion e-mail indisponible sur ce serveur — **cohérent** avec 503 noop email |

**Incohérence mineure (UX) :** le snackbar « Passkey indisponible » s’affiche pour **tout** fallback (y compris annulation API), pas seulement indisponibilité plateforme — **probable** confusion utilisateur ; **non** traité ici (audit seulement).

---

# Config Audit

## API (variables pertinentes observées dans le code)

| Variable | Rôle |
|----------|------|
| `AUTH_ADMIN_EMAIL_OTP_ENABLED` | Active les routes e-mail OTP (`is_admin_email_otp_enabled`) |
| `SES_FROM_EMAIL` ou `AWS_SES_FROM` | Sélectionne **SES** ; sinon **noop** |
| `AUTH_MOBILE_OTP_LOGIN_ENABLED` | **Login SMS** (`is_mobile_otp_login_enabled`), **pas** e-mail |
| `TWO_FACTOR_DEV_FIXED_CODE` | SMS / 2FA générique via `sms_otp_core` / `TwoFactorService` — **pas** admin e-mail |
| `TWO_FACTOR_DEV_EXPOSE_CODE` | JSON `dev_code` côté flux 2FA exposé — **pas** admin e-mail |
| `APP_ENV` / `ARQUANTIX_ENV` | `two_factor_env.is_production_like_env` — conditionne **fixed code** SMS, **pas** e-mail admin |
| `AUTH_PASSKEYS_ENABLED` | Passkeys backend |

## Mobile

| Mécanisme | Rôle |
|-----------|------|
| `AUTH_API_BASE_URL` / `SecureApiConfig.resolvedAuthApiBaseUrl` | Base URL FastAPI ; si vide, **pas** d’appels auth |
| `PasskeyApi._hasBase` | Bloque les appels si pas de base URL |

## Manque typique `.env` dev pour e-mail OTP

Pour que **`start`** ne renvoie pas 503 noop, il faut au minimum **soit** :

- **`AUTH_ADMIN_EMAIL_OTP_ENABLED=true`** **et** **`SES_FROM_EMAIL`** (ou AWS_SES_FROM) avec credentials SES utilisables, **soit**
- une **évolution code** (faux provider dev / code fixe) — **absente** aujourd’hui.

**Seul** `TWO_FACTOR_DEV_FIXED_CODE=111111` **ne suffit pas** pour l’e-mail OTP (confirmé).

## Passkey dev

- Variables RP / bundle : `webauthn_config.py`, AASA / assetlinks — **strict** selon `WEBAUTHN_STRICT_CONFIG` / env.
- Sur **device réel** avec passkeys et backend OK : **probable** succès ; simulateur : **probable** échec `isAvailable`.

---

# Existing Tests

## Backend

| Fichier | Couverture |
|---------|------------|
| `api/tests/test_webauthn_phase34.py` | `test_admin_email_otp_disabled_returns_503`, `test_admin_email_otp_happy_path` (fake provider), verrouillage sécurité |
| `api/tests/test_mobile_sms_login_otp.py` | SMS OTP, **fixed code** SMS — **pas** e-mail admin |

**Manque confirmé :** test **aucun** scénario « dev fixed code **e-mail** » (n’existe pas côté impl).

## Flutter

| Fichier | Couverture |
|---------|------------|
| `test/features/security/passkeys/passkey_service_test.dart` | PasskeyService / coordinator avec mocks — **pas** `adminEmailOtpStart` |

**Manque :** tests widget/intégration pour `LoginEmailOtpScreen` (start/verify/resend), indisponibilité passkey vs API.

---

# Findings

1. **E-mail OTP** : backend **implémenté et testé** avec faux provider ; en dev réel, **échec d’envoi** très probable si **SES non configuré** et **`AUTH_ADMIN_EMAIL_OTP_ENABLED`** non aligné avec l’attente produit.
2. **Code fixe 111111** : **ne couvre pas** l’e-mail OTP — **confirmé**.
3. **Passkey « indisponible »** : souvent **normal** (simulateur / stub / support) ou **repli** générique ; distinguer nécessite **logs** (`PasskeyLoginCoordinator`, statut API).
4. **Pas de second moteur OTP** côté e-mail : c’est un **troisième** chemin (admin routes) parallèle au SMS — **risque de divergence** maintenue.

---

# Recommended Plan

1. **Décision produit** : l’e-mail OTP en dev doit-il **exiger SES** (comme startup strict `validate_admin_email_otp_at_startup` en env strict) ou accepter un **mode dev** (code fixe + log ou faux send) — **sans** dupliquer tout `TwoFactorService` : factoriser **uniquement** la génération/lecture du code (ex. fonction partagée `dev_fixed_otp_plaintext_if_allowed()`) **ou** appeler `new_plaintext_sms_otp` pour le **plaintext** puis réutiliser le même hachage que l’admin — **à trancher** par équipe.
2. **Config** : documenter explicitement **`AUTH_ADMIN_EMAIL_OTP_ENABLED`** + **`SES_FROM_EMAIL`** pour l’e-mail ; ne pas confondre avec **`AUTH_MOBILE_OTP_LOGIN_ENABLED`**.
3. **Passkey** : valider sur **appareil physique** ; vérifier **RP ID** / domaines si échec `DomainNotAssociatedException` ; ne pas traiter le snackbar comme « bug dev » sans catégorie d’erreur.
4. **Tests** : ajouter test API « noop → 503 » déjà partiellement couvert ; ajouter test Flutter mock **adminEmailOtp** si CI le permet.

---

# Final Verdict

| Question | Réponse |
|----------|---------|
| Login e-mail OTP — état | **Partiellement prêt** : code **finalisé** côté API + Flutter, **cassé en dev typique** si email outbound absent (503). |
| `111111` couvre l’e-mail OTP ? | **Non** — **confirmé**. |
| Passkey indisponible en dev | **Souvent normal** (plateforme / simulateur) ; **config RP** — **à vérifier** si échec sur device réel. |
| Assez prêt pour corriger directement ? | **OUI** pour **config** (flags + SES ou mode dev explicite) ; **NON** sans clarifier le **mode dev e-mail** (pas de code fixe actuel). |
| Audit préalable nécessaire ? | **Non** pour la cause racine noop/flags — **déjà** identifiable dans le code ; **Oui** pour **runtime** passkey sur un device donné. |
| Chantier e-mail séparé ? | **OUI** (alignement dev + éventuelle mutualisation génération OTP) — **recommandé**. |
| Chantier passkey séparé ? | **OUI** (plateforme + WebAuthn + UX messages) — **recommandé**. |

---

*Audit basé sur le code du dépôt ; aucune exécution d’API ou d’app dans cet exercice.*
