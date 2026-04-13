# Executive Summary

Clôture du durcissement **login mobile OTP** (admin) : parité avec les autres flux d’authentification sur le **verrouillage sécurité**, mitigation **timing** configurable sur `POST /auth/login/sms/start`, conservation du **challenge OTP** en cas de refus pour compte verrouillé (SMS + email admin), messages **Flutter** alignés (403 / 429), tests backend et widget étendus. **Verdict : prêt à clôturer** le chantier au niveau objectifs fixés, avec confiance **élevée** sur la cohérence sécurité ; résidu mineur : pas d’événement SIEM dédié « resend » (choix volontaire : pas de duplication avec un second `started`).

# Scope

- Backend : `mobile_otp_login_routes`, `admin_email_otp_routes`, helper `_apply_auth_mobile_otp_start_min_latency`, `refresh_session._assert_user_not_security_locked`.
- Flutter : `passkey_api.dart` (messages start / verify), `LoginOtpScreen`, tests widget.
- Hors scope : nouvelle stack OTP, refonte UX, changement des providers SMS/email.

# Fixes Applied

1. **Admin email OTP** : après OTP valide et résolution utilisateur, appel à `_assert_user_not_security_locked(user)` **avant** suppression du challenge et `issue_fresh_auth_session` (`admin_email_otp_routes.py`).
2. **SMS login verify** : `_assert_user_not_security_locked(user)` est appelé **avant** `db.delete(row)` / `commit`, pour ne pas consommer le challenge si le compte est verrouillé (`mobile_otp_login_routes.py`).
3. **Timing start** : fonction `_apply_auth_mobile_otp_start_min_latency(t0)` ; variable d’environnement `AUTH_MOBILE_OTP_START_MIN_LATENCY_MS` (entier, ms) ; appliquée **uniquement** aux réponses **200** `MobileLoginStartResponse` (numéro connu et inconnu), pas aux 429/503.
4. **Flutter** : `loginSmsVerifyFailureUserMessage` pour le verify ; `loginSmsStartFailureUserMessage` enrichi pour **429** (resend / rate limit).

# Security Parity With Other Login Flows

| Flux | Compte verrouillé (`security_account_locked_until`) |
|------|-----------------------------------------------------|
| Login mot de passe | Déjà couvert via `_assert_user_not_security_locked` |
| Login SMS OTP | Verify : **403** `security.account_locked`, challenge **non consommé** |
| Admin email OTP verify | **403** `security.account_locked`, challenge **non consommé** (aligné) |

# Timing Mitigation

- **Variable** : `AUTH_MOBILE_OTP_START_MIN_LATENCY_MS` (ex. `400`). Absente, vide ou `0` → aucun sleep.
- **Comportement** : `t0 = time.perf_counter()` après normalisation du numéro ; avant chaque `return MobileLoginStartResponse` réussi, sleep du delta pour atteindre la durée minimale.
- **Non appliqué** aux erreurs (429 resend, 503 SMS / feature off) pour ne pas allonger artificiellement les chemins d’échec.
- **Tests** : unitaires sur `_apply_auth_mobile_otp_start_min_latency` (sleep attendu, no-op si désactivé ou déjà assez lent).

# SIEM / Audit Validation

Événements émis via `_auth_audit` → log structuré + `persist_auth_security_event` si `SECURITY_EVENTS` activé (comportement existant).

| `event_type` | Cas | Métadonnées sensibles |
|--------------|-----|------------------------|
| `auth.mobile_login.otp.start_unknown_phone` | Numéro sans utilisateur | `masked` (téléphone masqué), pas de numéro complet |
| `auth.mobile_login.otp.started` | Envoi SMS / challenge créé | `masked` |
| `auth.mobile_login.otp.verify_failed` | Code incorrect | `masked`, pas d’OTP en clair |
| `auth.mobile_login.otp.succeeded` | Session émise via `issue_fresh_auth_session` | Pipeline session / device existant |

**Resend** : pas d’événement `auth.mobile_login.otp.resend` distinct ; un second `POST .../start` après la fenêtre émet à nouveau `auth.mobile_login.otp.started` (évite la double comptabilisation « start + resend » pour le même envoi).

**Note** : la liste demandée incluait `auth.mobile_login.otp.failed` ; le code utilise **`verify_failed`** pour les échecs de vérification de code — même intention opérationnelle pour le SIEM (échec OTP login).

# Flutter / DS Final Review

- **Flux principal** : `LoginPhoneScreen` → `mobileLoginStart` → `LoginOtpScreen` (avec `smsStartResult`) → `mobileLoginVerify` → session ; pas d’étape email/passkey **dans** ce fil direct.
- **Secours** : bottom sheet « Autres options » → email ou passkey via `LoginEmailFallbackScreen` (hors fil principal mobile).
- **DS** : réutilisation de `AppSmsOtpVerificationBlock` / OTP comme l’inscription ; états loading / erreur cohérents ; pas de redesign.
- **403 verify** : message API prioritaire via `parseFastApiErrorMessage`, sinon formulation dédiée compte indisponible.

# Tests Added / Updated

**Backend** (`tests/test_mobile_sms_login_otp.py`)

- Compte verrouillé : vérifie que la ligne `AuthMobileLoginOtpChallenge` **reste** après 403.
- `_apply_auth_mobile_otp_start_min_latency` : sleep, no-op, déjà au-dessus du minimum.
- Resend / supersession : `RESEND_SECONDS=0`, codes OTP mockés distincts → premier code **401**, second **200**.

**Backend** (`tests/test_webauthn_phase34.py`)

- Admin email OTP + compte verrouillé → **403** `security.account_locked`, challenge conservé.

**Flutter** (`login_otp_screen_test.dart`)

- Scénario verify **403** → UI affiche un texte contenant « verrouillé ».

# Final Red Flags

- **Duplication logique OTP** : non — cœur commun `sms_otp_core` + providers.
- **Bypass session security** : non — `issue_fresh_auth_session` inchangé ; verrouillage asserté avant session / avant consommation challenge (SMS + email admin).
- **Bypass risk / response / zero trust** : aucun changement sur ces moteurs dans ce patch ; flux OTP admin reste sur la même chaîne que précédemment auditée.
- **Fuite timing** : atténuée sur le **start 200** ; chemins d’erreur ou autres endpoints non uniformisés (acceptable, documenté).
- **Events SIEM** : pas de `*.failed` nommé ainsi — utiliser `verify_failed` ; pas d’event `resend` dédié.
- **Messages bavards** : JSON d’erreur structuré `code` + `message` ; pas d’OTP ni de numéro complet dans les audits mobile listés.

# Final Verdict

- **Prêt à clôturer le chantier** : oui, pour les objectifs « hardening ciblé » décrits.
- **Niveau de confiance sécurité** : **élevé** sur la parité verrouillage, la non-consommation OTP sous lock, la mitigation timing configurable, et la cohérence des tests.
- **Écarts résiduels mineurs** : nom d’événement `verify_failed` vs `failed` attendu dans la spec rédactionnelle ; absence d’événement `resend` (compensé par un second `started`).

# Remaining Minor Improvements

- Documenter `AUTH_MOBILE_OTP_START_MIN_LATENCY_MS` dans le fichier d’exemple d’environnement ops (`.env` / runbook déploiement) si ce n’est pas déjà fait côté infra.
- Optionnel : alias SIEM ou règle de corrélation mappant `verify_failed` → catégorie « failed » pour les tableaux de bord existants.
- Optionnel : harmoniser les `detail` string vs dict sur d’autres branches historiques de l’OTP email admin (hors périmètre login mobile).
