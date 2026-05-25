# Morpho Local Sandbox — guide développeur

Mode de développement permettant de tester **l'expérience Earn Morpho USDC** (vaults, dépôt, retrait, yield, historique, monitoring) **sans transaction blockchain réelle**, sans Morpho GraphQL live et sans RPC Base live.

Le **ledger Prisma reste réel** : positions, transactions et réconciliation sont persistées en base locale.

---

## Architecture (direct on-chain uniquement)

```text
Privy              = login + embedded wallet optionnel
Reown / WalletConnect = wallets externes (MetaMask)
Morpho             = direct_morpho uniquement (prepare → sign → confirm)
Vancelian          = ledger + registry + reconciliation + monitoring
```

Flux sandbox :

```
UI /app/invest
  → API /api/portal/morpho/*  (direct_morpho)
       ↓ si MORPHO_LOCAL_SANDBOX_ENABLED
  morphoLocalSandbox.ts (mock GraphQL / RPC)
       ↓
  morphoVaultLedger.ts (Prisma réel)
```

**Exécution wallet en dev :**
- **Embedded Privy** — gas sponsorisé si activé côté Privy
- **MetaMask / WalletConnect** — via Reown (`NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`) — optionnel
- **Local Mock Wallet** — sans extension ni Reown (`EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true`) — **recommandé pour localhost**

---

## Workflow complet localhost (Morpho + wallet externe mocké)

```env
MORPHO_LOCAL_SANDBOX_ENABLED=true
EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true
```

```bash
npm run dev
```

Puis :

1. Login `/app/login` (Privy réel)
2. `/dev/wallet-sandbox` → **Link Local Mock Wallet**
3. `/dev/morpho-sandbox` → **Seed my current user** (optionnel, position initiale)
4. `/app/invest` → sélecteur **Local Mock Wallet** → dépôt 10 USDC / retrait
5. Ledger écrit `wallet_source = external_evm`, `wallet_provider = local_mock`

Voir aussi [LIFI_LOCAL_SANDBOX.md](./LIFI_LOCAL_SANDBOX.md) pour le swap mocké avec le même wallet.

---

## Prérequis

- Postgres local (`DATABASE_URL` dans `web/.env.local`)
- Login portail Privy fonctionnel (session JWT portail)
- `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID` si test MetaMask externe
- Node.js + dépendances installées dans `services/arquantix/web`

---

## Configuration `.env.local`

```env
MORPHO_LOCAL_SANDBOX_ENABLED=true
MORPHO_LOCAL_SANDBOX_YIELD_BPS=450

# WalletConnect / MetaMask (optionnel en sandbox)
NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID=c81911c59a601f3c793d361a74c1486d
NEXT_PUBLIC_BASE_RPC_URL=https://mainnet.base.org

# Optionnel — seed CLI ciblé
# MORPHO_LOCAL_SANDBOX_PERSON_EMAIL=votre@email.dev
# MORPHO_LOCAL_SANDBOX_PERSON_ID=
# MORPHO_LOCAL_SANDBOX_WALLET_ADDRESS=0x00000000000000000000000000000000000101
# MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID=local_mock_privy_wallet

# Wallet externe mock — sans MetaMask / Reown (recommandé localhost)
EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true
```

**Important :** `MORPHO_LOCAL_SANDBOX_ENABLED=true` est **interdit en production** (guard au démarrage).

---

## Démarrage rapide

```bash
cd services/arquantix/web
npm run morpho:seed-local   # vaults + registry (+ position si person_id connu)
npm run dev
```

Puis :

| URL | Rôle |
|-----|------|
| http://localhost:3000/dev/morpho-sandbox | Panneau dev (seed / reset / yield) |
| http://localhost:3000/dev/wallet-sandbox | Panneau dev wallet mock externe |
| http://localhost:3000/app/login | Login portail Privy |
| http://localhost:3000/app/invest | UI Earn Morpho |
| http://localhost:3000/app/wallets | Lier MetaMask ou Local Mock Wallet |
| http://localhost:3000/admin/morpho-vaults/monitoring | Monitoring (Healthy en sandbox) |

---

## Panneau dev `/dev/morpho-sandbox`

Disponible uniquement si :

- `NODE_ENV !== production`
- `MORPHO_LOCAL_SANDBOX_ENABLED=true`

### Actions

| Bouton | Route API | Effet |
|--------|-----------|-------|
| **Seed my current user** | `POST /api/dev/morpho-sandbox/seed-current-user` | Vaults publiés, registry, wallet lié, position ~90 USDC, 2 tx historiques |
| **Reset my sandbox position** | `POST /api/dev/morpho-sandbox/reset-current-user` | Supprime **uniquement** les tx/positions sandbox de l'utilisateur courant |
| **Add mock yield** | `POST /api/dev/morpho-sandbox/add-yield` | Augmente `lastAssetsRaw` sans toucher au `principalNetRaw` |

---

## Tester deposit / withdraw / yield

### Option A — Local Mock Wallet (recommandé)

1. `MORPHO_LOCAL_SANDBOX_ENABLED=true` + `EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true` + `npm run dev`
2. Login `/app/login`
3. `/dev/wallet-sandbox` → **Link Local Mock Wallet**
4. `/dev/morpho-sandbox` → **Seed my current user** (optionnel)
5. `/app/invest` → sélecteur **Local Mock Wallet** → dépôt / retrait / yield mock

### Option B — MetaMask réel (optionnel)

1. `MORPHO_LOCAL_SANDBOX_ENABLED=true` + `npm run dev`
2. Login `/app/login` (Privy)
3. `/dev/morpho-sandbox` → **Seed my current user**
4. `/app/wallets` → Connect Wallet → Vérifier ce wallet
5. `/app/invest` → **MetaMask / externe** → dépôt / retrait

---

## Commandes npm

```bash
npm run morpho:seed-local
npm run test:morpho-vault
node --import tsx --test src/lib/wallet/externalWallet.test.ts
```

---

## Données legacy en base

Les anciennes lignes ledger `integration_mode = privy_earn` (si présentes) sont des **données historiques en lecture seule**.  
Toute **nouvelle** exécution Morpho utilise `direct_morpho` uniquement.

---

## Limites connues

| Limite | Détail |
|--------|--------|
| **Privy auth requis** | Login portail toujours nécessaire (identité `person_id`) |
| **Sandbox = pas de chain live** | Pas de vraie tx Base en mode sandbox |
| **Production** | Sandbox impossible (`MORPHO_LOCAL_SANDBOX_ENABLED` bloqué) |
| **Wallet externe MetaMask** | Wallet connecté doit correspondre au wallet vérifié |
| **Local Mock Wallet** | Pas de MetaMask — tx simulées (`0xmocked…`) |

---

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `src/lib/portal/morphoLocalSandboxConfig.ts` | Flag env + guard production |
| `src/lib/portal/mocks/morphoLocalSandbox.ts` | Mock centralisé (vaults, deposit, withdraw, yield) |
| `src/lib/portal/morphoLocalSandboxDev.ts` | Seed / reset / status / add-yield dev |
| `src/lib/wallet/externalWalletMock.ts` | Wallet externe mock local |
| `src/lib/wallet/externalWalletMockDev.ts` | Routes dev link/unlink/status |
| `scripts/seed-morpho-local-sandbox.ts` | Seed CLI |
