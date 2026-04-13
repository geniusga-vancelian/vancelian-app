# Registration — vérification SMS mobile (prepare / resend / UX)

## Executive Summary

Le flux d’inscription avec écran `screen_type=interaction` et `interaction_type=phone_verification_sms` distingue désormais clairement **préparation** (réutilisation possible d’un challenge `pending` sans renvoyer de SMS) et **renvoi explicite** (`POST .../interaction/resend`), qui **supersede** les OTP en attente pour la même personne / purpose / cible, **crée un nouveau challenge**, envoie un **nouveau SMS**, et expose des champs **`reused` / `sent` / `resend_after_seconds`** côté prepare. Un **cooldown de renvoi** aligné sur `RESEND_SECONDS` (30 s) est appliqué **entre deux appels resend** via un horodatage interne de session (`__reg_internal_sms_last_resend_at`), sans exposer cette clé dans `collected_data` ni la projeter vers le profil. Le module 2FA transverse reste la source des challenges, du rate limiting global (fenêtre courte sur challenges **pending**, quotas longues, IP, cible) et des audits. Flutter peut auto-ouvrir `TwoFactorScreen` une seule fois par écran et appeler `resend` pour un vrai renvoi.

## Backend Resend Strategy

- **Stratégie retenue** : chaque **resend** crée un **nouveau** challenge SMS via `TwoFactorService.create_challenge` + `send_code`, après `supersede_pending_sms_challenges_for_target` (statut **`superseded`** sur les anciens `pending` pour la même combinaison personne / purpose / cible).
- **Ancien challenge** : `status = superseded` ; `enforce_challenge_verifiable` / état 2FA refuse la vérification avec l’erreur **`challenge_superseded`** (HTTP **410** sur `/api/2fa/verify` selon le routeur).
- **Si le dernier challenge pour la cible est déjà `verified`** : `resend` renvoie une erreur métier (**422**) — pas de renvoi après succès de vérification.

## Prepare vs Resend Responsibilities

| Action | Rôle |
|--------|------|
| **`POST .../interaction/prepare`** | S’il existe un challenge SMS `pending` non expiré pour personne / purpose / cible : **réutilisation** sans envoi ; `reused: true`, `sent: false`. Sinon : création + envoi SMS ; `reused: false`, `sent: true`. Toujours `resend_after_seconds` (30). Lors d’une **nouvelle** création depuis prepare, le timestamp interne de dernier resend est **supprimé** pour ne pas pénaliser un premier envoi « form » après un parcours sans resend. |
| **`POST .../interaction/resend`** | Intention utilisateur explicite : cooldown session **entre deux resends** ; puis supersede des `pending` ; nouveau challenge ; envoi SMS ; mise à jour du timestamp interne ; réponse avec `sent: true`, `challenge_id`, `otp_token`, `resend_after_seconds`, etc. |
| **`POST .../interaction/complete`** | Après `/api/2fa/verify` réussi sur le **challenge courant** : mise à jour session (`verified_flag_slug`, `phone_verified_at`, `phone_verification_channel`) ; suppression du timestamp interne resend. |

## 2FA Challenge Lifecycle Changes

- Statut **`superseded`** : challenge remplacé par un renvoi registration (ou logique équivalente côté service) ; **non vérifiable**.
- **`check_start_rate_limits` (fenêtre courte)** : ne compte que les lignes **`status == "pending"`** dans la fenêtre de `RESEND_SECONDS`, afin qu’un challenge tout juste passé en `superseded` ne bloque pas la création immédiate du **premier** resend après prepare (tout en continuant à bloquer un second `/api/2fa/start` tant qu’un `pending` existe dans la fenêtre).

## Flutter UX Improvements

- **Garde-fou auto-open** : dans `RegistrationFlowScreen`, une seule ouverture automatique de `TwoFactorScreen` par identifiant d’écran (ex. `_interactionAutoOpenedForScreenId`), résistant aux rebuilds.
- **`TwoFactorScreen`** : callback **`onResendRequested`** branché sur l’API **`resendInteraction`** ; en succès : nouveau `challengeId`, reset OTP / erreur, timer basé sur `resend_after_seconds` renvoyé par le backend, feedback type « Nouveau code envoyé ».
- **Contrat prepare/resend** : champs `reused`, `sent`, `resend_after_seconds` ; parsing côté modèles / API clients.

## Auto-Open Guard

- **Comportement** : au premier affichage d’un écran interaction `phone_verification_sms`, ouverture automatique du flux 2FA **une fois** par `screen.id` (pas de réouverture systématique après rebuild ni après retour succès/échec sauf logique produit explicite).
- **Resend** : ne passe **pas** par prepare pour forcer un SMS ; utilise **`/interaction/resend`**.

## Tests Added

**Backend** (`api/tests/test_registration_interaction_sms.py`) :

- Prepare : `sent` / `reused` / `resend_after_seconds` cohérents ; réutilisation sans second envoi.
- Resend : nouveau `challenge_id`, ancien en `superseded`, `sent: true`.
- Verify : ancien challenge `superseded` → **410** ; nouveau challenge accepté.
- Deuxième resend immédiat → **429** (cooldown session + message « Wait … before requesting »).
- Resend refusé si numéro déjà vérifié (**422**).
- Événement d’exécution **`INTERACTION_RESEND_REQUESTED`** présent.
- Prepare sans numéro collecté → **422** (conversion `RegistrationInteractionError` → `ValidationError`).

**Flutter** : test de parsing `resend_after_seconds` dans `interaction_payload` (`mobile/test/registration/registration_models_test.dart`).

## Remaining Gaps / Next Steps

- **Tests widget Flutter** : couverture fine (timer après resend, pas de double ouverture) peut compléter les tests de modèles si le pipeline le permet.
- **Observabilité** : vérifier en production la corrélation des audits `two_factor.challenge.*` avec `registration.interaction.*` (déjà logués côté registration ; supersede côté 2FA).
- **Harmonisation** : si d’autres flows réutilisent le même pattern « supersede puis create », documenter que le **cooldown entre resends** registration est **session-scopé** en complément des quotas 2FA globaux.
