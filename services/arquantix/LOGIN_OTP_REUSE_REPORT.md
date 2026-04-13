# Rapport — Connexion OTP SMS et réutilisation du bloc OTP (inscription)

## Objectif

Remplacer l’étape principale « e-mail / passkey » après le mobile par un écran **OTP SMS** (`POST /auth/login/start` + `POST /auth/login/verify`), en **réutilisant le même composant OTP** que l’inscription (pas de second `AppOtpInput` dupliqué).

## Implémentation Flutter

### Bloc partagé (Design System)

- **`lib/design_system/components/app_sms_otp_verification_block.dart`** : ligne « Code envoyé à … » + **`AppOtpInput`** (6 cases) + renvoi avec compte à rebours + états `locked` / `wrongCode`.

### Écrans

| Fichier | Rôle |
|--------|------|
| **`login_phone_screen.dart`** | Après « Continuer », navigation vers **`LoginOtpScreen`** (plus vers l’e-mail). Sous-titres alignés sur le flux SMS. Feuille « Autres options » → **`LoginEmailFallbackScreen`**. |
| **`login_otp_screen.dart`** | Titre « Connexion », bloc SMS, loader pendant `start`, vérification auto à 6 chiffres, message d’erreur si code invalide, renvoi, lien « Autres options de connexion » → **`showLoginOtpFallbackSheet`** (e-mail / passkey). |
| **`login_email_fallback_screen.dart`** | Ancien contenu e-mail + passkey (titre e-mail, CTA code e-mail, passkey). Réutilisé uniquement en secours. |
| **`login_email_otp_screen.dart`** | OTP **e-mail** admin (inchangé fonctionnellement) via le **même** `AppSmsOtpVerificationBlock`. |
| **`login_method_sheet.dart`** | `showLoginOtpFallbackSheet` : titre « Autres options de connexion », « Continuer avec l’e-mail », « Utiliser une passkey ». |

### Inscription

- **`registration_phone_sms_otp_panel.dart`** : le panneau SMS utilise désormais **`AppSmsOtpVerificationBlock`** au lieu d’assembler manuellement description + `AppOtpInput` + renvoi — **une seule implémentation visuelle** avec la connexion.

### API

- **`PasskeyApi`** : `mobileLoginStart` / `mobileLoginVerify` (déjà câblés dans `login_otp_screen.dart`).

### Tests

- **`test/features/security/login/login_otp_screen_test.dart`** : succès OTP (avec `passkeyApi` factice + `FlutterSecureStorage.setMockInitialValues`), code invalide, second appel `start` au renvoi, bottom sheet fallback.
- **`login_flow_navigation_test.dart`** et **`registration_phone_sms_otp_panel_test.dart`** : régression.

**Note tests** : sans `setMockInitialValues`, `DeviceIdService` / `SessionService` peuvent bloquer sur le stockage sécurisé pendant `_verify` ; les tests OTP configurent explicitement le mock.

### Comportement timer (connexion)

- **`login_otp_screen.dart`** : si `resend_after_seconds <= 0`, aucun `Timer.periodic` n’est démarré ; le timer est annulé lorsque le compte à rebours atteint 0 (évite une boucle de `setState` inutile et stabilise les tests).

### Injection test

- **`LoginOtpScreen(passkeyApi: …)`** : optionnel pour les tests widget (défaut `PasskeyApi()` en prod).

## Backend (rappel)

- Endpoints : `POST /auth/login/start`, `POST /auth/login/verify`.
- Nécessite utilisateur admin avec `mobile_e164`, SMS configuré et feature flag côté API (voir docs / runbook existants).

## Fichiers supprimés / renommage conceptuel

- **`login_email_screen.dart`** supprimé → remplacé par **`login_email_fallback_screen.dart`** (même responsabilité, nom explicite).

## Vérifications manuelles recommandées

- Appareil réel : mobile valide → SMS → saisie 6 chiffres → session.
- Serveur sans SMS / flag off : message d’erreur fatal + « Autres options de connexion ».
- Renvoi de code et bascule e-mail / passkey depuis la feuille.
