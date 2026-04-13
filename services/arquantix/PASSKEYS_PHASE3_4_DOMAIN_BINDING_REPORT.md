# Passkeys Phase 3.4 — Binding domaine / plateforme (rapport)

## Executive Summary

Cette phase **centralise et valide** la configuration WebAuthn (`WEBAUTHN_RP_ID`, `WEBAUTHN_ORIGINS`, `WEBAUTHN_RP_NAME`), applique une **validation stricte au démarrage** en environnement **production ou staging** (tant que `AUTH_PASSKEYS_ENABLED` est actif), expose les fichiers **`.well-known`** (AASA + `assetlinks.json`), ajoute un **diagnostic admin** `GET /admin/security/passkeys/config`, et aligne le **fallback OTP** sur la **même API auth** que les passkeys via **`/auth/login/email-otp/*`** (sessions `AdminUser` / JWT identiques au login mot de passe).

## RP ID / Origins Strategy

| Élément | Rôle |
|--------|------|
| `WEBAUTHN_RP_ID` | Identifiant du relying party (hôte ou suffixe de domaine cohérent avec les origines). |
| `WEBAUTHN_ORIGINS` | Liste séparée par virgules des origines exactes (`https://…`) utilisées pour `verify_registration_response` / `verify_authentication_response`. |
| `WEBAUTHN_RP_NAME` | Nom affiché côté authenticator. |

**Règles strictes** (`ENVIRONMENT` / `ENV` ∈ `production`, `prod`, `live`, `staging`, `stage`, ou `WEBAUTHN_STRICT_CONFIG=true`) :

- `WEBAUTHN_RP_ID` non vide.
- `WEBAUTHN_ORIGINS` non vide.
- Chaque origine en **`https://`**, sauf `localhost` / `127.0.0.1` (dev local uniquement).
- Pour chaque origine, le **hostname** doit être **égal** à `rp_id` ou être un **sous-domaine** de `rp_id` (`host == rp_id` ou `host.endswith("." + rp_id)`).

Implémentation : `api/services/auth/webauthn_config.py` — appelée depuis `enforce_auth_infrastructure_bootstrap` (non exécuté en `testing=True`).

## iOS Associated Domains

**Côté infra / Apple / Xcode (hors dépôt)** :

1. Activer la capability **Associated Domains** pour l’app iOS.
2. Ajouter une entrée **`webcredentials:<WEBAUTHN_RP_ID>`** (ex. `webcredentials:auth.vancelian.com`).
3. Le **RP ID** WebAuthn doit correspondre au domaine pour lequel le fichier AASA est servi publiquement.

**Côté API (code)** : génération JSON via `build_apple_app_site_association()` à partir de :

- `WEBAUTHN_AASA_APP_IDS` (liste `TEAMID.bundleid`, séparateur virgule), **ou**
- `APPLE_TEAM_ID` + `IOS_BUNDLE_ID` → `TEAMID.IOS_BUNDLE_ID`.

Fichiers servis :

- `GET /.well-known/apple-app-site-association`
- `GET /apple-app-site-association` (compatibilité)

`Content-Type: application/json`.

## Android Asset Links

**Côté Play / app (hors dépôt)** : associer le **package name** et l’empreinte **SHA-256** du certificat de signature (play signing / upload key selon le cas).

**Côté API (code)** : `GET /.well-known/assetlinks.json` à partir de :

- `ANDROID_PACKAGE_NAME`
- `ANDROID_SHA256_CERT_FINGERPRINTS` (séparateur virgule, espaces supprimés en sortie).

Relations incluses : `delegate_permission/common.get_login_creds` et `delegate_permission/common.handle_all_urls` (usage courant passkeys / liens).

## Well-Known Endpoints

| Route | Contenu |
|-------|---------|
| `/.well-known/apple-app-site-association` | JSON AASA + `webcredentials` |
| `/apple-app-site-association` | Identique |
| `/.well-known/assetlinks.json` | Tableau Digital Asset Links |

Contraintes déploiement : **pas de redirection** HTTP→HTTPS cassant le chemin, **pas d’auth**, **CDN** doit servir le corps JSON tel quel. Le **même hôte** que celui attendu pour le RP ID en production.

**Sonde optionnelle** : définir `WEBAUTHN_PUBLIC_BASE_URL=https://<rp-host>` et appeler `GET /admin/security/passkeys/config?probe=true` (admin JWT) pour tenter des GET sur les trois chemins.

## OTP Fallback Validation

| Ancien comportement | Nouveau |
|---------------------|---------|
| Écran mobile ouvrait `/api/2fa/start` avec `purpose=login` **sans** JWT admin → inadapté à la connexion **AdminUser**. | **Use verification code** ouvre `AdminEmailOtpLoginScreen` → `POST /auth/login/email-otp/start` puis `POST /auth/login/email-otp/verify` sur **la même base URL** que les passkeys (`AUTH_API_BASE_URL`). |

Activation serveur : `AUTH_ADMIN_EMAIL_OTP_ENABLED=true` + fournisseur e-mail réel (ex. SES) en prod-like ; sinon **503** avec message explicite côté app.

**2FA Person** (`/api/2fa`) : le purpose `login` reste **allowlisté** ; la politique cible exige désormais que pour `login` **et** `verify_email`, si un e-mail cible est fourni et qu’un client lié existe, il **corresponde** à l’e-mail du profil (`two_factor_target_policy.py`).

## Prod Validation Checklist

Voir **`PASSKEYS_DEPLOYMENT_CHECKLIST.md`** (liste opérationnelle).

## Tests Added

Fichier `api/tests/test_webauthn_phase34.py` :

- Validation stricte : origine `http` rejetée ; host ≠ rp_id rejeté.
- `.well-known` : statut 200, `Content-Type` JSON, structure AASA / assetlinks.
- `GET /admin/security/passkeys/config` : 401 sans JWT, 200 avec JWT test.
- OTP admin : 503 si désactivé ; flux complet avec provider e-mail factice.
- `validate_purpose("login")` en mode non-relaxed.

## Remaining Gaps

- **Next.js / autre front** : si le domaine public RP est servi par un autre service, **dupliquer** ou **proxy** les routes `.well-known` vers ce service ou héberger les JSON au bon host (une seule source de vérité côté DNS).
- **Apple / Google** : délais de propagation AASA / asset links ; tests **obligatoires** sur appareils réels après publication.
- **RP ID vs multi-sous-domaines** : si plusieurs apps ou origines distinctes, valider le modèle **eTLD+1** vs **host exact** avec la doc WebAuthn et votre hébergeur.
- **OTP admin** : migration DB `111` à appliquer en prod ; table nettoyée aussi par le thread périodique (challenges expirés).
