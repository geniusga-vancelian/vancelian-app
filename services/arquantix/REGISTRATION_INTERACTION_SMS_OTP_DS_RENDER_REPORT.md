# Registration — rendu SMS OTP avec le Design System (`AppOtpInput`)

## Executive Summary

Les écrans **`screen_type=interaction`** / **`phone_verification_sms`** n’utilisaient plus le composant DS **`AppOtpInput`** : le flux ouvrait un **`TwoFactorScreen`** pleine page avec ses propres champs, tandis que le corps du **`RegistrationFlowScreen`** affichait un texte explicatif + bouton « Confirmer mon numéro » (placeholder). Le correctif introduit **`RegistrationPhoneSmsOtpPanel`**, rendu **inline** sous le titre / sous-titre du screen, qui enchaîne **`prepareInteraction` → saisie 6 chiffres (`AppOtpInput`) → verify 2FA → `completeInteraction` → refresh + `next`**. Le **resend** réel (`/interaction/resend`) remet à jour challenge / jeton, incrémente une **clé** sur **`AppOtpInput`** pour réinitialiser la saisie, relance le **timer** et affiche un **SnackBar** discret. Le panneau debug du flow est **désactivé par défaut** ; le **launcher de test** le réactive en **`kDebugMode`**.

## Root Cause of Missing OTP Input

- **`RegistrationFlowScreen`** déclenchait **`_runPhoneSmsInteraction`**, qui poussait **`TwoFactorScreen`** via **`Navigator.push`**.
- **`TwoFactorScreen`** n’utilise **pas** **`AppOtpInput`** : il compose une **rangée de 6 `TextField`** maison.
- Le **scroll principal** du flow affichait un **message d’attente** + CTA pour relancer la préparation, **sans** les 6 cases DS — d’où l’impression d’écran « vide » / debug comme contenu principal.

## DS Component Reuse Strategy

- **`AppOtpInput`** (`lib/design_system/components/app_otp_input.dart`) est utilisé **tel quel** dans **`RegistrationPhoneSmsOtpPanel`**.
- Réinitialisation après erreur ou **resend** : **`ValueKey(_otpGeneration)`** sur **`AppOtpInput`** pour recréer l’état interne (pas de duplication de logique clavier / cases).
- Conflit de nom **`Config`** (Google Fonts vs `core/config.dart`) : import **`as app_cfg`** dans le panel.

## Flutter Rendering Changes

| Fichier | Rôle |
|---------|------|
| **`registration_phone_sms_otp_panel.dart`** | Widget dédié : prepare, **`AppOtpInput`**, verify, complete, resend, erreurs inline. |
| **`registration_flow_screen.dart`** | Suppression de **`TwoFactorScreen`**, **`_runPhoneSmsInteraction`**, garde-fou **`_interactionAutoOpenedForScreenId`**. Insertion du **panel** dans le **`CustomScrollView`** après titre / sous-titre. |
| **`registration_test_launcher_screen.dart`** | **`showDebugPanel: kDebugMode`** pour conserver le debug en dev. |

**Stratégie OTP** : **soumission automatique** à **6 chiffres** via **`onCompleted`** de **`AppOtpInput`** (pas de second bouton Continue sur cet écran — le CTA fixe du bas reste masqué pour l’interaction SMS, comme avant).

## Resend UX Wiring

- **`registrationApi.resendInteraction`** (route backend déjà livrée).
- Succès : nouveau **`otp_token`** → nouveau **`TwoFactorApi`**, nouveau **`challenge_id`**, **`_otpGeneration++`**, **`_startResendCountdown(resend_after_seconds)`**, SnackBar **« Nouveau code envoyé »**.
- Échec / 429 : message dans **`_otpError`** (affiché par **`AppOtpInput`** ou logique resend).

## Debug Panel Behavior

- **`RegistrationFlowScreen.showDebugPanel`** : défaut **`false`** (UX prod / démo).
- Panneau toujours **replié** par défaut (`_debugExpanded == false`) quand affiché.
- **Launcher interne** : **`showDebugPanel: kDebugMode`** pour les équipes qui en ont besoin.

## Tests Added

- **`test/registration/registration_phone_sms_otp_panel_test.dart`**  
  - Faux **`RegistrationApi`** + **`twoFactorApiBuilder`** avec verify toujours OK.  
  - Vérifie présence de **`AppOtpInput`**, texte de **resend / compte à rebours**, **`onCompleted`** + **`completeInteraction`** après saisie de 6 chiffres.  
  - Cas **payload `error_code`** : message affiché, **pas** d’OTP.

## Remaining Gaps / Next Steps

- **`TwoFactorScreen`** pourrait être refactoré pour utiliser **`AppOtpInput`** aussi (hors scope registration, évite deux UX OTP différentes).
- Test widget **resend** (timer → tap → nouvelle clé) possible avec **`fake_async`** ou avance du temps.
- **`RegistrationFlowScreen`** : test d’intégration bout-en-bout avec HTTP mocké reste optionnel.
