# Phase 0 bis — Analyse bundles production portail

**Date :** 2026-05-29  
**Statut :** audit quantitatif — **aucun code modifié**  
**Build :** `rm -rf .next && NODE_ENV=production npm run build` (Next.js **14.2.35**)  
**Log build :** `/tmp/arquantix-next-build-clean.log`  
**Référence plan :** [PORTAL_NAVIGATION_PERFORMANCE_AUDIT.md](./PORTAL_NAVIGATION_PERFORMANCE_AUDIT.md)

---

## 1. Executive Summary

### Mesure clé

Sur les routes portail « onglets principaux », le **First Load JS production** est dominé par le **layout `(shell)`**, pas par le code métier de la page :

| Route | First Load JS (Next build) | Dont Shared JS | Route JS (page) |
|-------|---------------------------:|---------------:|----------------:|
| `/app/academy` | **1 370 kB** | 1 364 kB | 5.7 kB |
| `/app/dashboard` | **1 440 kB** | 1 437 kB | 3.4 kB |
| `/app/markets` | **1 620 kB** | 1 608 kB | 12.0 kB |
| `/app/invest` | **1 620 kB** | 1 606 kB | 13.8 kB |
| `/app/profile` | **1 580 kB** | 1 567 kB | 13.2 kB |

**~95–99 % du First Load JS est du Shared JS** (layout + chunks communs). Le JS spécifique à la page fait **3–14 kB** dans le rapport Next.

### Web3 dans le shell

10 chunks Web3 identifiés dans le manifest `(shell)/layout` totalisent :

| Métrique | Valeur |
|----------|--------|
| Taille brute (minifiée) | **4 929 kB** |
| Taille gzip estimée (mesurée) | **~1 313 kB** |

Ces chunks contiennent **Privy, Wagmi, RainbowKit, TanStack Query, viem, et le stack Li.FI/signing** — et sont référencés dans le First Load de **dashboard, markets, academy, profile, invest, wallet, swap, borrow**.

### Fuites confirmées (preuves bundle)

1. **`/app/academy`** charge les mêmes chunks Privy/Wagmi (`55500-*.js`, `43239-*.js`) que `/app/wallet/swap` — **sans fonctionnalité Web3**.
2. **`/app/markets`** embarque **+234 kB gzip** de chunks vs academy (RainbowKit, Wagmi, Li.FI helpers) — lié aux imports statiques markets/invest (sections bundles, modales).
3. **`portalWalletRouteHelpers`** contamine **33 routes API** ; le graphe serveur Web3 est consolidé dans **`69096.js` (5,1 MB brut)** avec `createPublicClient` + `@privy-io`.
4. **`warmAllPortalMainRoutes`** déclenche **6 prefetch RSC + ~8–11 requêtes API** au mount shell (impact runtime prod : réseau/CPU, pas bundle initial).

### Recommandation immédiate (post-audit)

Priorité #1 : **retirer Web3 du layout `(shell)`** → gain estimé **~1,2–1,3 MB First Load JS** sur 7/10 routes analysées (Scenario A).

---

## 2. Route Bundle Table

Données **officielles Next.js build** + comptage chunks manifest (`.next/app-build-manifest.json`).

| Route | First Load JS | Route JS | Shared JS | Chunks (JS) | Hydration (estimée) |
|-------|-------------:|---------:|----------:|------------:|---------------------|
| `/app/dashboard` | **1 440 kB** | 3.4 kB | 1 436.6 kB | 22 | Élevée — shell Web3 + dashboard scope |
| `/app/markets` | **1 620 kB** | 12.0 kB | 1 608.0 kB | 29 | Élevée — shell Web3 + WS quotes + sections bundles |
| `/app/academy` | **1 370 kB** | 5.7 kB | 1 364.3 kB | 17 | Élevée — shell Web3 seul (page 17.8 kB brute) |
| `/app/profile` | **1 580 kB** | 13.2 kB | 1 566.8 kB | 23 | Élevée — shell Web3 + RainbowKit (ConnectExternalWallet) |
| `/app/invest` | **1 620 kB** | 13.8 kB | 1 606.2 kB | 30 | Élevée — shell Web3 + modales vault/bundle (transitive) |
| `/app/invest/[slug]` | **270 kB** | 3.1 kB | 266.9 kB | 22 | Modérée — **pas de chunks Privy 55500 dans l’entrée page**¹ |
| `/app/markets/[ticker]` | **167 kB** | 13.7 kB | 153.3 kB | 12 | Faible entrée page — **25 chunks shell absents du manifest page**¹ |
| `/app/wallet/crypto` | **1 440 kB** | 8.0 kB | 1 432.0 kB | 22 | Élevée (Web3 justifié partiellement) |
| `/app/wallet/swap` | **1 610 kB** | 20.1 kB | 1 589.9 kB | 27 | Très élevée — Li.FI + signing (justifié) |
| `/app/borrow` | **1 640 kB** | 25.8 kB | 1 614.2 kB | 28 | Très élevée — Lombard + Privy (justifié) |

**Global shared (toutes routes app) :** 91.6 kB (`52117-*.js` + `fd9d1056-*.js` + autres).

¹ **Note importante :** pour `/app/markets/[ticker]` et `/app/invest/[slug]`, le rapport Next affiche un First Load bas car le manifest **page** n’inclut pas les 25 chunks du `(shell)/layout` Web3. En navigation **depuis un autre onglet portail**, le shell Web3 est **déjà en cache**. En **hard refresh direct** sur une URL ticker, le layout `(shell)` est quand même requis côté App Router — les chunks layout se chargent via l’arbre layout (non comptés dans la ligne page du build). **25 chunks shell-only = ~1 511 kB gzip** absents du manifest `[ticker]`.

### Largest imported chunks (communs aux routes « onglets »)

| Chunk | Brut | Gzip (~) | Contenu détecté |
|-------|-----:|---------:|-----------------|
| `55500-da797add1ee6341d.js` | 2 898 kB | 742 kB | **Privy + viem + Li.FI/signing** |
| `8e1b1b5f-955f2e4a47ea639f.js` | 755 kB | 217 kB | **Privy + viem + Li.FI** |
| `66498-c1efe45f9d7eccab.js` | 537 kB | 132 kB | **viem** |
| `43239-c9db4455e798c546.js` | 246 kB | 81 kB | **wagmi + RainbowKit + TanStack Query** |
| `92763-16582cf9e0a7ee34.js` | 235 kB | 71 kB | **viem** |
| `4e88bc13-ebfaec8ea069d467.js` | 144 kB | 36 kB | **RainbowKit** |

---

## 3. Shared Chunk Analysis

### 3.1 `(shell)/layout` — point central

| Métrique | Valeur |
|----------|--------|
| Fichiers JS dans manifest layout | **34** |
| Taille JS layout (brute, somme manifest) | **6 248 kB** |
| Entry chunk `layout-de154d328956abfa.js` | **78.7 kB** (réf. PortalWeb3Providers, PortalShell) |

**Routes consommatrices du layout shell (First Load ≥ 1,37 MB) :**

- `/app/dashboard`, `/app/markets`, `/app/academy`, `/app/profile`, `/app/invest`
- `/app/wallet/crypto`, `/app/wallet/swap`, `/app/wallet/savings`, `/app/borrow`
- `/app/markets/bundle/[productCode]` (**1,76 MB** First Load)
- `/app/wallet/crypto/bundle/[portfolioId]` (**1,68 MB**)

### 3.2 Root layout (`/layout`)

| Métrique | Valeur |
|----------|--------|
| JS root layout (brute) | **693 kB** |
| Web3 | **Non** (SiteChrome, Navigation imports statiques) |

Impact portail : `SiteChrome` en mode `bareChrome` rend `{children}` seul, mais le **module** SiteChrome (Navigation, ScrollMotionEffects) reste dans le chunk root (~693 kB brut).

### 3.3 Différentiel markets vs academy (pollution page+shared)

**13 chunks présents sur `/app/markets` mais pas `/app/academy` :**

| Impact | Valeur |
|--------|--------|
| Extra brut | **767 kB** |
| Extra gzip | **234 kB** |

Inclut : RainbowKit (`4e88bc13`), Wagmi stack (`43239`), viem (`92763`, `59878`), Li.FI (`23074`, `12991`, `61614`), page markets (`page-a0ff85f89f40cac0.js`, 37 kB).

**Invest vs academy :** +784 kB brut / **+240 kB gzip** (14 chunks extra).

Les **page chunks** eux-mêmes sont légers et **ne contiennent pas** les strings `BundleInvestDialog` / `usePrivy` — la pollution est **100 % transitive** via imports statiques du graphe client (sections → modales → hooks).

---

## 4. Web3 Leakage Analysis

Analyse par **présence de marqueurs** dans les chunks du manifest First Load (layouts + page).

| Route | Privy | Wagmi | RainbowKit | viem | viem/chains | TanStack Query | LI.FI |
|-------|:-----:|:-----:|:----------:|:----:|:-----------:|:--------------:|:-----:|
| `/app/dashboard` | ✅ | ✅ | ✅ | ✅ | ✅ (trans.) | ✅ | ✅ |
| `/app/markets` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/app/academy` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/app/profile` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/app/invest` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/app/invest/[slug]` | ✅* | ✅* | ✅* | ✅* | ✅* | ✅* | ✅* |
| `/app/markets/[ticker]` | ❌† | ❌† | ❌† | ❌† | ❌† | ❌† | ✅ (61614) |
| `/app/wallet/crypto` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `/app/wallet/swap` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (+ page) |
| `/app/borrow` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ (+ page) |

\* Chunks Web3 présents via sous-arbre client partagé (VaultModuleWeb, layout partiel) — First Load build **270 kB** mais marqueurs détectés dans chunks chargés.  
† Non listés dans manifest **page** ; shell layout Web3 se charge via navigation parente ou requête layout parallèle.

### Routes read-only chargeant Web3 sans besoin fonctionnel immédiat

| Route | Web3 au load | Justification actuelle | Verdict |
|-------|:------------:|------------------------|---------|
| `/app/academy` | Complet | Aucune | **Fuite majeure** |
| `/app/dashboard` | Complet | Aucune tx ; scope wallet read-only possible via API | **Fuite majeure** |
| `/app/markets` | Complet + extra Li.FI | Invest dialog via `PortalCryptoBundlesSection` (import statique) | **Fuite majeure** |
| `/app/invest` | Complet + modales | Modales Morpho/Ledgity/Bundle importées statiquement | **Fuite majeure** |
| `/app/profile` | Complet | Section wallets → RainbowKit (besoin **localisé**) | **Fuite partielle** |
| `/app/markets/[ticker]` | Minimal à l’entrée | Chart SVG natif ; pas de tx | **Acceptable** (si shell découplé) |

---

## 5. Hydration Analysis

### 5.1 Providers montés globalement (layout `(shell)`)

Arbre client hydraté sur **chaque route shell** :

```
PortalWeb3Providers
  └─ ExternalWalletProvider
       ├─ WagmiProvider          ← hydratation + reconnect
       ├─ QueryClientProvider    ← TanStack Query
       ├─ RainbowKitProvider     ← hydratation + WC modal tree
       └─ ExecutionWalletProvider ← fetch wallets, localStorage, effects
  └─ PortalAuthPrivyGate
       └─ PrivyPortalProvider    ← Privy SDK init, captcha, session
            └─ PortalShell
                 ├─ NavPendingProvider
                 ├─ PortalChainProvider
                 ├─ PortalWalletScopeProvider  ← fetch person-wallets + external wallets au mount
                 ├─ PortalTopnav               ← fetch /api/portal/profile (avatar)
                 └─ {page}
```

### 5.2 Estimation poids hydration par route

| Route | Providers globaux | Composants page lourds | Poids hydration |
|-------|:-----------------:|------------------------|-----------------|
| `/app/academy` | 7 providers + shell | Listes, pagination, search | **Élevé** (injustifié — Web3 idle) |
| `/app/dashboard` | 7 providers + shell | Progressive fetch, chart SVG | **Élevé** |
| `/app/markets` | 7 providers + shell | WS quotes, multiples sections | **Très élevé** |
| `/app/profile` | 7 providers + shell | Settings + ConnectExternalWallet | **Élevé** |
| `/app/markets/[ticker]` | Si shell en cache : oui ; sinon partiel | Chart SVG, sidebar | **Modéré** |
| `/app/wallet/swap` | 7 providers + shell | Swap flow, Li.FI | **Très élevé** (justifié) |

### 5.3 Coût Privy/Wagmi à l’hydratation (qualitatif + quantitatif)

| SDK | Effet au mount | Taille chunk (gzip) |
|-----|----------------|-------------------:|
| Privy (`55500` + `8e1b1b5f`) | Init auth, captcha provider, listeners | **~959 kB** |
| Wagmi + RainbowKit (`43239` + `4e88bc13`) | Config chains, reconnect, WalletConnect metadata | **~117 kB** |
| viem (multiple chunks) | Dépendances parse/encode (même sans tx) | **~284 kB** |
| TanStack Query | Client query cache | inclus dans `43239` |
| Li.FI/signing (`61614`, `23074`, `12991`) | Hooks swap/bundle chargés transitivement | **~25 kB** gzip + gros raw dans `55500` |

**Total Web3 hydration footprint (gzip, 10 chunks clés) : ~1 313 kB parse + exécution JS main thread.**

---

## 6. Bundle Pollution Analysis

### A — `PortalWeb3Providers`

| Métrique | Valeur |
|----------|--------|
| Modules importés (direct) | `@rainbow-me/rainbowkit`, `wagmi` (5 chains), `@tanstack/react-query`, `ExecutionWalletProvider` |
| Chunks attribuables | `43239`, `4e88bc13`, + part de `66498`/`92763` |
| Taille gzip combinée Wagmi/RainbowKit/TanStack | **~117 kB** |
| + viem transitive | **~284 kB** gzip (chunks viem) |
| Routes affectées | **Toutes** routes `(shell)` (~25+ pages portail) |

### B — `PortalBundleInvestDialog`

| Métrique | Valeur |
|----------|--------|
| Import statique depuis | `PortalCryptoBundlesSection` (markets), `PortalPlacerView` (invest), bundle detail |
| Page chunk markets (direct) | **37 kB** — **sans** marqueurs Privy/Li.FI |
| Impact réel | Chunks Li.FI **`23074`, `12991`, `61614`** + wagmi/rainbowkit dans manifest markets (**+234 kB gzip vs academy**) |
| `/app/markets` reçoit Li.FI ? | **Oui** (chunks présents dans First Load 1 620 kB) |

Chaîne transitive mesurée :

```
PortalCryptoBundlesSection → PortalBundleInvestDialog → useBundleLifiInvest
  → useLifiSwapExecution → usePortalTxSigner → Privy + wagmi + viem
```

### C — `warmAllPortalMainRoutes`

| Métrique | Valeur |
|----------|--------|
| Routes prefetch (Next RSC) | **6** : dashboard, crypto-wallet, invest, markets, academy, profile |
| APIs `revalidatePortalCache` au mount shell | **~8** (dashboard×2, crypto, invest, markets, profile×3) |
| + `PortalTopnav` mount | **+1** route (profile) + **+3** APIs |
| + `preloadPrivyPortalProvider` | **1** import dynamique chunk Privy |
| **Total requêtes réseau idle (1ère visite shell)** | **~11–14** prefetch/API |

**Impact production :**

- **Bande passante** : téléchargement anticipé de chunks RSC pour 6 routes (~ plusieurs MB si non cache CDN).
- **CPU serveur** : `/api/portal/markets` (7 upstreams, timeout 30 s), dashboard core+portfolio, etc.
- **Contention** : parallèle avec le chargement de la page courante → latence navigation perçue.
- **Ne augmente pas** le First Load JS statique, mais **dégrade le runtime** post-mount.

### D — `portalWalletRouteHelpers`

#### Graphe d’imports source

```
portalWalletRouteHelpers.ts
├─ requirePortalPersonId / requirePortalSessionToken     [auth seul — OK]
├─ morphoLedgerErrorResponse / morphoRpcErrorResponse
├─ ledgityVaultLiquidity.ts
│    └─ baseRpcProvider.ts → viem + viem/chains (base)
├─ MorphoVaultLedgerError, Lombard*, Ledgity*
└─ baseRpcErrors.ts (pas viem direct)
```

#### Contamination serveur (webpack server chunks)

| Chunk serveur | Taille brute | Marqueurs |
|---------------|-------------:|-----------|
| `69096.js` | **5 136 kB** | `createPublicClient`, `@privy-io` |
| `19621.js` | **573 kB** | `createPublicClient` |
| `81760.js` | **12 kB** | `ledgityVaultLiquidity` |

Handlers `route.js` individuels sont **2–18 kB** — le coût est dans les **shared server chunks** chargés à la demande.

#### 33 routes API important `portalWalletRouteHelpers`

**Read-only / listing (devraient utiliser session helpers only) :**

- `crypto-wallet/route.ts`, `crypto-wallet/[asset]/route.ts`
- `savings-wallet/route.ts`, `savings-wallet/[vault]/route.ts`
- `morpho/vaults/route.ts`
- `wallets/external/route.ts`, `wallets/external/[id]/route.ts`, `nonce`, `verify`
- `lombard/markets/route.ts`, `lombard/position/route.ts`, `lombard/qa-context/route.ts`
- `ledgity/vaults/route.ts`, `ledgity/position/route.ts`, `ledgity/history/route.ts`
- `morpho/position/route.ts`, `morpho/history/route.ts`
- `privy/send-sponsored-transaction/route.ts`
- + 4 routes `dev/*` mock/sandbox

**Web3 execution (helpers vault OK) :**

- `morpho/prepare|confirm`, `ledgity/prepare|confirm`, `lombard/prepare|confirm|quote|capacity`

**Non contaminées (référence) :**

- `/api/portal/markets`, `/api/portal/academy`, `/api/portal/profile`, `/api/portal/dashboard/core` — **pas** de `portalWalletRouteHelpers`

---

## 7. Impact Simulation

Estimations basées sur mesures gzip réelles. Fourchettes conservatrices.

### Scenario A — Web3 Boundary Only

**Action :** retirer Privy/Wagmi/RainbowKit/ExecutionWallet du layout `(shell)` ; boundary lazy sur wallet/swap/borrow/modales.

| Route | First Load actuel | First Load estimé | Δ |
|-------|------------------:|------------------:|--:|
| `/app/academy` | 1 370 kB | **~120–180 kB** | **−88–91 %** |
| `/app/dashboard` | 1 440 kB | **~130–200 kB** | **−86–91 %** |
| `/app/markets` | 1 620 kB | **~280–350 kB** | **−78–83 %** |
| `/app/profile` | 1 580 kB | **~200–280 kB** | **−82–87 %** |
| `/app/wallet/swap` | 1 610 kB | **~1 550–1 610 kB** | ~0 % (Web3 requis) |

**Hydration :** suppression de **7 providers** + init Privy/Wagmi sur routes read-only → **TTI −2–5 s** (4G, estimation).

**Routes affectées :** ~25 pages `(shell)` ; 7 routes Web3 gardent le boundary.

### Scenario B — Prefetch Cleanup Only

**Action :** supprimer `warmAllPortalMainRoutes`, `preloadPrivyPortalProvider` au mount ; garder hover prefetch léger.

| Métrique | Impact |
|----------|--------|
| First Load JS | **~0 %** (inchangé) |
| Requêtes réseau post-mount | **−11 à −14** par session |
| Bytes téléchargés idle | **−2–8 MB** (prefetch RSC 6 routes, variable cache) |
| CPU serveur idle | **−6–8 handlers API** lourds (markets, dashboard) |
| Navigation perçue | Légèrement **plus lente** au 1er hover (acceptable) |

### Scenario C — API Helper Split Only

**Action :** `portalSessionRouteHelpers` vs `portalVaultRouteHelpers` ; imports dynamiques RPC.

| Métrique | Impact |
|----------|--------|
| First Load JS client | **0 %** |
| Cold start `/api/portal/markets` | **0 %** (déjà propre) |
| Cold start `/api/portal/crypto-wallet` | **−5 MB** chunk server partagé non requis (estim.) |
| Mémoire worker Node (p95) | **−10–30 %** sous charge API mixte |
| Routes impactées | **33** handlers |

### Scenario D — Combined (A + B + C + code-split modales)

| Métrique | Gain cumulé estimé |
|----------|-------------------|
| First Load `/app/academy` | **1 370 → ~100–150 kB** |
| First Load `/app/markets` | **1 620 → ~200–280 kB** |
| Hydration main thread | **−70–85 %** temps SDK init (read-only routes) |
| Requêtes idle post-mount | **−11–14** |
| Server cold paths read-only API | **−5 MB** chunk viem/privy non chargé |

---

## 8. 80/20 Ranking

| Rank | Change | Effort | Expected Gain (production) |
|:----:|--------|:------:|----------------------------|
| **1** | **Web3 boundary — retirer providers du `(shell)/layout`** | M | **−1,2–1,3 MB First Load JS** sur academy/dashboard/markets ; **−70–85 % hydration** read-only |
| **2** | **Dynamic import modales exécution** (BundleInvest, Morpho/Ledgity vault, Li.FI) | M | **−234 kB gzip** markets vs academy ; invest −240 kB gzip |
| **3** | **Supprimer warmup massif shell** (`warmAllPortalMainRoutes`, `preloadPrivy`) | S | **−11–14 requêtes** idle ; **−2–8 MB** transfert ; latence navigation **−20–40 %** sous charge |
| **4** | **Split `portalSessionRouteHelpers`** (33 routes API) | M | Cold start API read-only **−5 MB** server chunk ; mémoire **−10–30 %** |
| **5** | **`next/dynamic` sur écrans portail** (page.tsx → Screen) | S–M | Meilleur cache route-level ; **−10–20 %** TTI navigation répétée |

*(S = 0,5–1 j, M = 2–4 j)*

---

## 9. Final Recommendation

### Verdict quantitatif

Le problème production est **confirmé par build** : ce n’est pas une hypothèse dev-only. Le portail charge **~1,3–1,6 MB de JavaScript** au premier accès d’un onglet principal, dont **~1,31 MB gzip sont directement attribuables à 10 chunks Web3** montés via `(shell)/layout`.

La page academy (**5,7 kB Route JS**) prouve que **le métier n’est pas le problème** — c’est l’**architecture de layout**.

### Séquence d’implémentation recommandée

1. **Phase 0 bis validée** — baseline ci-dessus ; conserver ce doc pour comparaison post-refactor.
2. **Scenario A** en premier (Web3 boundary) — ROI maximal mesuré.
3. **Scenario B** en parallèle (prefetch) — risque faible, gain runtime immédiat.
4. **Dynamic modales** (Scenario A.2) — markets/invest.
5. **Scenario C** — split API helpers.
6. Re-build et **comparer ligne par ligne** le tableau §2.

### Validation post-remédiation

```bash
cd services/arquantix/web
rm -rf .next && NODE_ENV=production npm run build 2>&1 | tee /tmp/build-after.log
grep '/app/academy\|/app/markets\|/app/dashboard' /tmp/build-after.log
```

**Critères de succès :**

- `/app/academy` First Load JS **< 200 kB**
- `/app/markets` First Load JS **< 350 kB** (sans Web3 boundary sur la page)
- Chunks `55500-*`, `43239-*` **absents** du manifest academy/dashboard
- `/app/wallet/swap` First Load JS **≥ 1,4 MB** (Web3 toujours présent)

---

## Annexe — Méthodologie

| Étape | Commande / artefact |
|-------|---------------------|
| Build production | `rm -rf .next && NODE_ENV=production npm run build` |
| Tailles routes | Sortie standard Next « Route (app) » |
| Shared JS | `First Load JS − Route JS` (colonne build) |
| Marqueurs Web3 | Scan contenu chunks `.next/static/chunks/*.js` (regex Privy/wagmi/viem/Li.FI) |
| Gzip | `zlib.gzipSync` sur fichiers minifiés (approximation transfert HTTP) |
| Server graph | `.next/server/chunks/*.js` + tailles `route.js` |
| Manifest | `.next/app-build-manifest.json` |

**Limites :**

- First Load JS Next = **minifié** (gzip réel ~25–35 % en dessous pour chunks dupliqués).
- Routes `[ticker]` / `[slug]` : métrique build page ≠ expérience complète avec shell layout (voir note §2).
- Pas de mesure TTI/LCP terrain (nécessite staging + Web Vitals — recommandé avant/après).

---

*Audit only — aucun fichier source modifié.*
