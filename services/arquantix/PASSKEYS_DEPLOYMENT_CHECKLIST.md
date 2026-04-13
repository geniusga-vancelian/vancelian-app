# Checklist déploiement Passkeys + domain binding

## 1. Variables d’environnement (API)

### WebAuthn (obligatoire en staging / production si passkeys actives)

| Variable | Exemple | Notes |
|----------|---------|--------|
| `ENVIRONMENT` ou `ENV` | `staging` / `production` | Déclenche la validation stricte WebAuthn au boot. |
| `WEBAUTHN_RP_ID` | `auth.vancelian.com` | Non vide ; cohérent avec les hôtes des origines. |
| `WEBAUTHN_ORIGINS` | `https://auth.vancelian.com,https://app.vancelian.com` | **https** uniquement (sauf localhost). Hosts = `rp_id` ou sous-domaines. |
| `WEBAUTHN_RP_NAME` | `Vancelian` | Nom affiché. |
| `WEBAUTHN_PUBLIC_BASE_URL` | `https://auth.vancelian.com` | Optionnel : sonde admin `?probe=true`. |
| `WEBAUTHN_STRICT_CONFIG` | `true` | Option : forcer la validation stricte même hors staging/prod. |

### Fichiers well-known (templates)

| Variable | Rôle |
|----------|------|
| `WEBAUTHN_AASA_APP_IDS` | Liste `TEAMID.bundleid` (iOS), séparateur virgule. |
| `APPLE_TEAM_ID` + `IOS_BUNDLE_ID` | Alternative à la ligne du dessus (un seul bundle). |
| `ANDROID_PACKAGE_NAME` | Package Android. |
| `ANDROID_SHA256_CERT_FINGERPRINTS` | Empreintes SHA-256, séparateur virgule. |

### OTP e-mail admin (fallback mobile)

| Variable | Valeur |
|----------|--------|
| `AUTH_ADMIN_EMAIL_OTP_ENABLED` | `true` pour activer |
| `SES_FROM_EMAIL` ou `AWS_SES_FROM` | Expéditeur SES (prod-like exige un vrai envoi) |

### Déjà requis ailleurs

- `AUTH_PASSKEYS_ENABLED` (défaut actif)
- Redis / rate limit en production (`AUTH_RL_BACKEND`, `AUTH_REDIS_URL`)

## 2. Base de données

- Exécuter les migrations Alembic jusqu’à **`111`** (`auth_admin_email_otp_challenges`).

## 3. Domaines & DNS

- Le **hostname** servi en HTTPS pour les passkeys mobiles doit être celui pour lequel :
  - les **Associated Domains** iOS pointent (`webcredentials:`),
  - **Digital Asset Links** Android valident,
  - les fichiers **`/.well-known/...`** répondent **200** avec JSON.

## 4. Fichiers well-known à vérifier (manuel)

Après déploiement, depuis un poste externe :

```bash
curl -sS -D- "https://<RP_HOST>/.well-known/apple-app-site-association" | head
curl -sS -D- "https://<RP_HOST>/.well-known/assetlinks.json" | head
```

Vérifier : pas de 301 vers un chemin incorrect, `Content-Type` JSON, corps parseable.

## 5. Xcode (iOS)

- [ ] Capability **Associated Domains**
- [ ] Domaine `webcredentials:<WEBAUTHN_RP_ID>`
- [ ] **Signing** / bundle id alignés avec `WEBAUTHN_AASA_APP_IDS`

## 6. Android

- [ ] `package_name` = `ANDROID_PACKAGE_NAME`
- [ ] SHA-256 = certificat **effectivement** utilisé pour la build store (ou debug pour tests internes)
- [ ] Fichier `assetlinks.json` accessible sur le **même** host que celui attendu par le navigateur / Credential Manager

## 7. Diagnostic API (admin)

Avec un JWT **admin** :

```http
GET /admin/security/passkeys/config
GET /admin/security/passkeys/config?probe=true
```

Contrôler `warnings`, `origins`, `webcredentials_apps_template`, `assetlinks_expected`, et éventuellement `well_known_probe`.

## 8. Tests sur appareils réels

- [ ] Enrôlement passkey (compte admin déjà connecté par mot de passe ou autre)
- [ ] Login passkey depuis l’écran **Connexion compte**
- [ ] Fallback **Use verification code** → réception e-mail → saisie code → session active
- [ ] Annulation Face ID / empreinte → retour UI sans blocage
- [ ] (Option) Flux `/api/2fa` avec `purpose=login` **avec** JWT Person inchangé pour les autres parcours

## 9. Mobile (build)

- `AUTH_API_BASE_URL` (ou équivalent `--dart-define`) pointe vers l’API qui sert **`/auth/*`** et **`.well-known`** si c’est le même host RP.
