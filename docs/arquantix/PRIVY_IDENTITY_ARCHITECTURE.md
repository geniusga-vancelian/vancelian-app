# Architecture identité Privy & wallets non-custodial (Vancelian / Arquantix)

Document de référence après audit — **phase bridge** + **phase 2** (vérification JWT serveur, HTTP Flutter), sans refonte JWT globale.

## 1. Trois notions à ne pas confondre

| Entité | Rôle |
|--------|------|
| **`admin_users`** | **Compte login technique** (historique « admin »). Porte hash mot de passe, OTP SMS, passkeys WebAuthn côté serveur, liaison `person_id`. **N’est pas** un rôle métier « administrateur produit ». **Aucune** colonne `privy_user_id` : Privy est ancré via `person_external_identities`. |
| **`persons`** | **Identité humaine / KYC / Customer 360** (`profile_json`, statuts réglementaires). |
| **`pe_clients`** | **Client portfolio** : ownership produit (positions crypto custodiales, custody retail, bundles, etc.). |

## 2. JWT actuel (inchangé dans cette phase)

- **`sub`** = obligatoirement `au:<admin_users.id>` (invariant PR5).
- Claims utiles : `person_id`, session `sid`, flags step-up / device binding, etc.
- **Raison** : compatibilité **Flutter**, **BFF Next** (`backend-jwt.ts`), **refresh rotatif**, **Zero Trust**, **WebAuthn** existants.

**Stratégie temporaire** : Privy et wallets embedded sont **ancrés sur `persons`** ; la session applicative **continue** à passer par `AdminUser` jusqu’à une éventuelle migration de format `sub` (hors périmètre actuel).

## 3. Nouvelles tables (Alembic 156)

### `person_external_identities`

- Liens **fournisseur d’identité externe → `person_id`** uniquement.
- Contrainte **UNIQUE (`provider`, `external_subject`)**.
- **Aucune** colonne sur `admin_users` pour `privy_user_id`.

### `person_crypto_wallets`

- Wallets **user-controlled** (embedded ou external), **non custodial**.
- Séparés de :
  - **`crypto_positions`** / moteur d’exchange interne ;
  - **`crypto_custody_accounts`** (pools techniques agrégés) ;
  - **`custody_accounts`** (fiat/IBAN côté custody module).
- Contrainte **UNIQUE (`provider`, `chain_type`, `address`)**.
- **Ne jamais** stocker de clé privée.

## 4. Variables d’environnement (API FastAPI)

| Variable | Rôle |
|----------|------|
| **`PRIVY_EXCHANGE_VERIFICATION_MODE`** | `stub` (dev/tests uniquement) ou `jwt` (production). |
| **`PRIVY_APP_ID`** | Audience (`aud`) attendue dans le JWT Privy — obligatoire en mode `jwt`. |
| **`PRIVY_JWT_VERIFICATION_KEY`** | Clé publique **PEM ES256** — prioritaire si présente. |
| **`PRIVY_JWKS_URL`** | Alternative : URL `.../jwks.json` ; clé choisie via le `kid` du JWT (cache process). |
| **`PRIVY_APP_SECRET`** | Secret application (API Privy côté serveur) : **lu** pour cohérence ops ; la vérification **locale** du JWT d’accès utilise la **clé publique**, pas le secret. |

### Production ECS (`arquantix-api`, us-east-1)

| Secrets Manager | Variable injectée | Rôle |
|-----------------|-------------------|------|
| `arquantix/prod/privy-app-id` | `PRIVY_APP_ID` | Audience JWT Privy |
| `arquantix/prod/privy-jwks-url` | `PRIVY_JWKS_URL` | JWKS ES256 (si pas de PEM) |

`PRIVY_EXCHANGE_VERIFICATION_MODE=jwt` reste une variable d’environnement plain sur la task definition.

Script ops : `./scripts/arquantix-sync-privy-secrets.sh` — create/update Secrets Manager sans committer les valeurs.

Les déploiements GitHub Actions (`arquantix-api-deploy.yml`) réutilisent la task definition courante : les références `valueFrom` sont **conservées** lors des mises à jour d’image Docker.

### Mode stub (dev / tests)

- Jetons de la forme **`stub:{external_subject}`** où `external_subject` doit correspondre à une ligne `person_external_identities` existante (`provider=privy`).
- **Interdit** si `ENV=production` ou si l’environnement n’est pas considéré comme dev (`core.env.is_dev_mode()` **false**) → erreur `privy.stub_forbidden_in_production`.

### Mode production (JWT)

- `PRIVY_EXCHANGE_VERIFICATION_MODE=jwt`
- Clé de vérification : **`PRIVY_JWT_VERIFICATION_KEY`** (PEM ES256, prioritaire) **ou** **`PRIVY_JWKS_URL`** + `kid` dans l’en-tête du JWT.
- Vérification **ES256** avec `python-jose`, `iss=privy.io`, `aud=PRIVY_APP_ID`.
- **Ne jamais** logger le jeton complet (logs limités au type d’erreur).

### Erreurs API stables (`detail.code`)

- `privy.token_missing`, `privy.token_invalid`, `privy.verification_not_configured`, `privy.stub_forbidden_in_production`
- Échange HTTP wallets : `privy.wallet_address_invalid`, `privy.wallet_chain_unsupported`, `privy.wallet_persist_error`

## 5. Services & endpoints

- **`services/auth/person_identity_bridge.py`** : résolution et liaison Person ↔ identité externe ↔ PeClient ↔ création paresseuse d’`AdminUser` pour session.
- **`services/auth/privy_token_verifier.py`** : vérification stub / JWT.
- **`GET /auth/privy/person-wallets`** (`privy_person_wallets_routes.py`) :
  - Auth : `Authorization: Bearer` (JWT avec `person_id`).
  - Liste des lignes actives `person_crypto_wallets` (non révoquées) pour cette personne — même forme que les entrées `wallets[]` de l’échange.
  - Erreurs typiques : `privy.person_wallets_requires_session`, `privy.person_wallets_invalid_session`, etc.

- **`POST /auth/privy/exchange`** (`privy_exchange_routes.py`) :
  - Entrée : `privy_access_token`, optionnellement `wallets[]` (`address`, `chain_type`, `chain_id`, `wallet_type`).
  - Validation EVM : `0x` + **40** caractères hexadécimaux.
  - Sortie : `access_token`, `refresh_token`, `token_type`, `device_id`, `person_id`, `pe_client_id`, `wallets[]` (lignes actives non révoquées).

- **`POST /auth/privy/link`** (`privy_link_routes.py`) — **production / staging** :
  - Entrée : `Authorization: Bearer` (JWT Vancelian avec claim `person_id`), corps `{ privy_user_id, email? }`.
  - Le `person_id` cible est **uniquement** celui décodé du JWT (pas de `person_id` dans le corps client).
  - Après lien + wallet + **`exchange`**, l’app reçoit la même famille de jetons (`sub=au:…`, device headers) que le login SMS ; les **passkeys** déjà enregistrées sur le même `AdminUser` restent valides tant qu’aucun basculement de session ne les invalide.
  - Sortie : `{ ok, idempotent }`.
  - Codes utiles : `privy.link_requires_session`, `privy.link_invalid_session`, `privy.link_requires_person_claim`, `privy.link_person_not_found`, `privy.link_invalid_privy_user_id`, `privy.link_conflict`.

### Endpoints **dev / test** uniquement (`privy_dev_routes.py` + `privy_dev_tools.py`)

Garde-fou : **interdits** si `ENV=production`. Autorisés si `app.state.testing` (pytest), `ENV` ∈ `test`, `testing`, `local`, `dev`, `development`, ou si `core.env.is_dev_mode()` (sans production).

| Méthode | Chemin | Rôle |
|---------|--------|------|
| `POST` | `/auth/privy/dev-link` | Lier `privy_user_id` → `person_id` existante sans SQL manuel. |
| `GET` | `/auth/privy/dev-current-person` | Lire `person_id` / `pe_client_id` depuis un **JWT Vancelian** (`Authorization: Bearer`). |

Codes d’erreur utiles : `privy.dev_link_forbidden`, `privy.dev_link_conflict`, `privy.dev_link_person_not_found`, `privy.dev_current_person_requires_session`.

Journaux audit (préfixes sûrs) : `privy_dev_link_success`, `privy_dev_link_conflict`, `privy_dev_link_forbidden`.

## 6. Tests & migrations locaux

Sans migration **156** appliquée sur la base pointée par `DATABASE_URL`, les tests `tests/test_person_identity_bridge.py` sont **ignorés** (skip conditionnel).

```bash
cd services/arquantix/api
alembic upgrade head
pytest tests/test_person_identity_bridge.py tests/test_privy_dev_routes.py tests/test_privy_link_routes.py tests/test_privy_person_wallets_routes.py -q
```

**Statut des scénarios** (une fois la migration appliquée) :

| Test | Attendu |
|------|---------|
| Liaison / doublon identité externe | OK |
| Unicité wallet provider+chain+address | OK |
| Login AdminUser paresseux | OK |
| Résolution PeClient | OK |
| Exchange stub → JWT Vancelian `sub=au:…` | OK |
| Mode non configuré → 503 | OK |
| Stub interdit si production-like | OK |
| Token absent → 400 | OK |
| Token stub invalide → 401 | OK |
| Adresse wallet invalide → 400 | OK |
| Wallet valide persisté + réponse | OK |
| JWT ES256 (clé de test) → session | OK |
| Idempotence : un seul `AdminUser` par `person_id` après doubles échanges | OK |
| Dev-link / dev-current-person | OK (`tests/test_privy_dev_routes.py`) |
| Liaison JWT `POST /auth/privy/link` | OK (`tests/test_privy_link_routes.py`) |
| Liste wallets `GET /auth/privy/person-wallets` | OK (`tests/test_privy_person_wallets_routes.py`) |

## Test E2E réel Flutter (sans SQL manuel)

### 1. Variables **backend**

```bash
PRIVY_EXCHANGE_VERIFICATION_MODE=jwt
PRIVY_APP_ID=<app_id_privy>
# Soit PEM :
# PRIVY_JWT_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
# Soit JWKS (sans PEM) :
# PRIVY_JWKS_URL=https://auth.privy.io/api/v1/apps/<app_id_privy>/jwks.json
```

(En local prudence : `ENV=local` ou `dev` — les routes `/auth/privy/dev-*` sont **refusées** si `ENV=production`.)

### 2. Variables **Flutter** (`flutter run` / build)

**Recommandé (local)** : copier `services/arquantix/mobile/.env.flutter.example` vers **`.env.flutter`** dans le même dossier, remplir `PRIVY_APP_ID`, `PRIVY_APP_CLIENT_ID` (optionnel URL / `AUTH_API_BASE_URL`). Les scripts `./run-ios.sh`, `./run-android.sh`, `./run.sh`, `./run-ios-device.sh` chargent ce fichier automatiquement (non versionné, listé dans `.gitignore`).

```bash
cd services/arquantix/mobile
cp .env.flutter.example .env.flutter   # puis éditer .env.flutter
./run-ios.sh
```

À la main :

```bash
flutter run \
  --dart-define=PRIVY_APP_ID=<même_app_id> \
  --dart-define=PRIVY_APP_CLIENT_ID=<client_id_mobile> \
  --dart-define=AUTH_API_BASE_URL=http://localhost:8000
```

Sur appareil physique, remplacer `localhost` par l’IP LAN de la machine qui héberge l’API.

### 3. Flow dans l’app

**Grand public (dashboard)** : le bouton **Create wallet** dans la rangée d’actions sous le graph (clé CMS `more`) ouvre **OAuth Google/Apple** ; la liaison appelle `POST /auth/privy/link` (Bearer), puis wallet embarqué et `exchange` comme ci-dessous.

**Labo dev (OTP / étapes découpées)** :

1. Se connecter au flux **Vancelian classique** (ex. SMS / passcode) pour un **JWT avec `person_id`**.
2. **Profil** → **Développement** → **Privy wallet (labo)**.
3. **Login Privy** (OTP email) → **Create / Get embedded wallet**.
4. **Load current Vancelian person** *ou* coller un UUID `person_id`.
5. **Link Privy to Person** → `POST /auth/privy/dev-link` (sans Bearer sur `person_id` corps — réservé dev).
6. **Exchange Privy token** → session Vancelian + wallets persistés.
7. **Show session status** / DID + adresse wallet.

### 4. Erreurs fréquentes (`detail.code`)

| Code | Cause indicative |
|------|------------------|
| `privy.verification_not_configured` | `PRIVY_EXCHANGE_VERIFICATION_MODE` / clé PEM / `PRIVY_APP_ID` manquants côté API. |
| `privy.token_invalid` | Jeton Privy expiré ou clé publique PEM ne correspond pas au dashboard. |
| `privy.dev_link_forbidden` | API en **production** ou environnement non dev — dev-link désactivé. |
| `privy.dev_current_person_requires_session` | Pas de `Authorization: Bearer` Vancelian (ou JWT sans `person_id`). |
| `privy.wallet_address_invalid` | Adresse EVM mal formatée dans le corps `exchange`. |
| `privy.dev_link_conflict` | `privy_user_id` déjà lié à **une autre** `person_id`. |
| `privy.link_conflict` | Idem **`/auth/privy/link`** (session JWT avec autre personne). |

**Dépôt crypto — message « Not Found » ou HTTP 404 sur `GET /auth/privy/person-wallets`**

| Symptôme | Action |
|---------|--------|
| `detail` FastAPI littérale `"Not Found"` | La route n’existe **pas** sur le serveur contacté : soit **mauvaise URL** (`AUTH_API_BASE_URL` pointe souvent vers **Next :3000** au lieu du **FastAPI :8000**), soit image / conteneur **API ancien** sans le routeur `privy_person_wallets`. Vérifier avec `curl -s -o /dev/null -w "%{http_code}" http://<hôte>:8000/auth/privy/person-wallets` (attendu **401** sans Bearer, pas **404**). |
| HTTP 404 + `privy.person_wallets_person_not_found` | JWT avec `person_id` **sans** ligne correspondante dans `persons` (données incohérentes). |
| Liste vide `{ "wallets": [] }` | Normal si **aucun** `exchange` réussi encore : passer par OAuth → **Create wallet** jusqu’à la fin (`exchange`). |

## 7. Flutter — SDK `privy_flutter` + écran dev

**Dépendance** : package officiel [`privy_flutter`](https://pub.dev/packages/privy_flutter) (éditeur `privy.io`), version épinglée dans `pubspec.yaml`.

### Fichiers

| Fichier | Rôle |
|---------|------|
| `lib/features/wallet/privy/privy_dart_defines.dart` | `PRIVY_APP_ID` / `PRIVY_APP_CLIENT_ID` (`String.fromEnvironment`) |
| `lib/features/wallet/privy/privy_sdk_holder.dart` | Singleton `Privy.init` / `PrivyConfig` |
| `lib/features/wallet/privy/privy_auth_provider.dart` | `PrivyFlutterAuthProvider` — **OAuth** (`loginWithOAuth`) + OTP email Privy |
| `lib/features/wallet/privy/privy_safe_log.dart` | Métadonnées jeton (longueur / suffixe), jamais le JWT complet |
| `lib/core/privy_identity_bridge_service.dart` | `exchangePrivyToken`, `linkPrivyForAuthenticatedSession`, `devLinkPrivyToPerson`, `devCurrentPerson` → API auth |
| `lib/features/home/presentation/screens/home_screen.dart` | Actions héros : clé `more` → **Create wallet** → `PrivyWalletOAuthScreen` |
| `lib/features/wallet/presentation/screens/privy_wallet_oauth_screen.dart` | Parcours OAuth (Google ; Apple sur iOS) → **`/auth/privy/link`** → wallet → `exchange` |
| `lib/features/wallet/presentation/screens/privy_wallet_dev_screen.dart` | **Debug uniquement** (`kDebugMode`) : labo OTP email / étapes séparées |
| Profil → **Développement** | Raccourcis **debug** (« Wallet Privy (OAuth) » + labo OTP) — le flux grand public passe par le dashboard |

### Prérequis natifs

- **Android** : `minSdk` ≥ **27** (`android/app/build.gradle.kts`).
- **iOS** : déploiement ≥ **17.0** (`ios/Podfile` + `Runner.xcodeproj`, requis par le pod `privy_flutter` / PrivySDK).
- **OAuth** : dans `Info.plist` / `AndroidManifest`, déclarer le **URL scheme** de retour (`vancelian` par défaut, voir `PRIVY_OAUTH_SCHEME`). Dans le dashboard Privy, activer les fournisseurs **Google / Apple** (comme dans l’exemple officiel SDK) et autoriser le redirect correspondant au scheme.
- Dashboard Privy : fournisseur **Email** uniquement nécessaire pour le **labo OTP** ; OAuth ne l’utilise pas.

### Variables compile-time (`--dart-define`)

| Define | Description |
|--------|-------------|
| `PRIVY_APP_ID` | App ID dashboard Privy |
| `PRIVY_APP_CLIENT_ID` | Client ID (app mobile) |
| `PRIVY_OAUTH_SCHEME` | Optionnel ; défaut **`vancelian`** — doit matcher CFBundleURLSchemes / `android:scheme` |
| `AUTH_API_BASE_URL` | (déjà supporté) Base FastAPI auth si ≠ dérivation port 8000 |

**Ne pas** passer `PRIVY_APP_SECRET` dans l’app : réservé serveur.

### Test local (résumé)

1. Backend : migration **156** ; `PRIVY_EXCHANGE_VERIFICATION_MODE=jwt` (+ clé publique) ou `stub` en dev.
2. Pour un **E2E sans SQL** : utiliser **dev-link** depuis l’écran (après login Vancelian pour obtenir `person_id`). Sinon : liaison manuelle en base sur `person_external_identities`.
3. Lancer l’app en **debug** avec les defines Privy + `AUTH_API_BASE_URL`.
4. **Profil** → **Développement** → **Wallet Privy (OAuth)** pour le parcours **un clic** (Google / Apple selon bouton), ou **Privy wallet (labo OTP)** pour reproduire l’OTP email étape par étape — voir aussi **Test E2E réel Flutter** ci-dessus.

### Logs sûrs

- `_safeLog` : longueur + quelques derniers caractères ; pas de dump JWT Privy ni Vancelian dans la console.

### Flow mobile (résumé)

1a. Parcours **OAuth** (`privy.oAuth.login` + scheme natif `vancelian`), puis même suite qu’OTP : dev-link automatique depuis l’écran OAuth → `createEmbeddedWalletIfNeeded()` → exchange.  
1b. Parcours **labo OTP** : `sendPrivyEmailCode` / `completePrivyEmailLogin`.
2. `PrivyIdentityBridgeService.instance.exchangePrivyToken(..., wallets: [...])`.
3. `SessionService.storeTokens` (inchangé) + `SessionIdentityContext` hydraté.

**`AUTH_API_BASE_URL`** : voir `SecureApiConfig` si l’auth n’est pas sur le même hôte port 8000.

### Dépannage — `NSURLErrorDomain Code=-1005` (passwordless / OAuth)

L’appel sortant vers `https://auth.privy.io/...` est géré par le **SDK natif Privy**, pas par ton code Dart. **-1005** (« The network connection was lost ») indique en général une **coupure réseau transitoire** (Wi‑Fi instable, **iPhone en debug wireless**, VPN, coupure 4G/5G).

- Côté app : `PrivyFlutterAuthProvider` refait automatiquement jusqu’à **4 tentatives** avec délai sur les erreurs reconnues comme transitoires (`sendCode` + `loginWithCode`).
- À tester : **câble USB** au lieu du wireless, autre réseau Wi‑Fi, désactiver VPN/proxy, ou **simulateur** sur le même Mac.

## 8. Limites actuelles

- Pas de swaps (1inch / ParaSwap), pas de Morpho, pas de signature de transaction, pas de transfert crypto.
- Écran Privy : **debug uniquement** ; pas d’intégration produit dans le parcours login SMS existant.
- OTP **email** côté Privy **(labo)** : le flux produit peut privilégier **OAuth** ; le SMS reste le flux Vancelian existant ; pas de fusion des deux parcours à ce stade.
- Mode `jwt` : aligné sur la **vérification de JWT** documentée côté Privy (clé publique ES256) ; évolutions JWKS / introspection selon feuille de route Privy produit.
- Le **secret** `PRIVY_APP_SECRET` ne remplace pas la clé publique pour valider l’access token utilisateur.

## 9. Custody privilégié & ledger (cible produit)

**Privy est le custody utilisateur de référence** : toute crypto détenue par le client (dépôt on-chain, achat euro→crypto, swap crypto→crypto) se matérialise sur son wallet Privy.

| Flux | Comportement cible |
|------|-------------------|
| Dépôt externe | Webhook `wallet.funds_deposited` → `person_wallet_deposits` + `person_wallet_balances` |
| Achat euro→crypto | Ordre exchange interne → crédit ledger Privy (mock puis settlement on-chain) |
| Swap crypto→crypto | LI.fi (futur) : débit asset A / crédit asset B sur le même wallet Privy ; états intermédiaires LP à modéliser |
| Patrimoine UI | Fusion PE + Privy via `patrimony_merge.py` ; historique via `transaction_merge.py` |

**Réconciliation permanente** : `person_wallet_balances` doit refléter l’état on-chain (webhooks + `reconcile-wallets` admin). Les écarts temporaires pendant un swap LP sont acceptables tant qu’ils sont tracés (statut pending / metadata swap).

**Phase actuelle (mock)** : dépôts simulés (`simulate-deposit`), pas encore de swap LI.fi ; les ordres exchange historiques restent dans `exchange_orders` mais sont exposés avec `custody_provider: privy` dans l’API client.

**Go-live prod & réconciliation :** voir [PRIVY_PROD_GO_LIVE.md](./PRIVY_PROD_GO_LIVE.md) et [PRIVY_RECONCILIATION_ENTERPRISE_PLAN.md](./PRIVY_RECONCILIATION_ENTERPRISE_PLAN.md).

## 10. Prochaines phases

- Raffiner onboarding OAuth (copie, erreurs métier i18n).
- Signature de transactions (EIP-712, etc.).
- Intégration swaps **avec** séparation ledger interne vs wallet utilisateur.
- Morpho / yield : même principe d’**ancrage Person** et traçabilité audit.

## 11. Migration JWT éventuelle (option B — non planifiée)

Passer de `au:<admin_users.id>` à un sujet centré `person:` ou `cus:` impliquerait : `jwt_subject_resolution`, `mobile_identity.py`, **`backend-jwt.ts`**, caches Redis identité, migrations données, fenêtre de coexistence. **Hors scope** tant que le bridge Privy n’est pas stabilisé en production.
