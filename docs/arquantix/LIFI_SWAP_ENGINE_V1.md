# LI.FI Swap Engine V1 — Vancelian / Arquantix

Document de référence pour l’intégration contrôlée du moteur de swap crypto basé sur LI.FI.

## Objectif V1

Permettre des swaps **crypto ↔ crypto** et **cross-chain** depuis les wallets Privy, avec :

- whitelist stricte **V1 : USDC, USDT, ETH — EVM uniquement** (Ethereum, Arbitrum, Base, Polygon),
- orchestration **100 % backend** (aucun appel LI.FI côté front),
- UX simplifiée type neobank,
- fees Vancelian transparents,
- états de transaction traçables.

## Architecture

```
Privy Wallet (signature client)
        ↓
Frontend (Web / Flutter) — BFF Next.js
        ↓
FastAPI Orchestrator (/api/swaps/*)
        ↓
LI.FI API (li.quest/v1) — clé serveur uniquement
        ↓
DEX / Bridges
```

### Principe de sécurité

| Interdit front | Obligatoire backend |
|----------------|---------------------|
| Appeler LI.FI directement | Valider assets / chaînes |
| Token lists libres | Construire quotes |
| Adresses contrat arbitraires | Appliquer fees + slippage |
| Routes custom | Retourner payload signable |

## Fichiers créés / modifiés

### Backend (`services/arquantix/api`)

| Fichier | Rôle |
|---------|------|
| `config/supported_swap_assets.py` | Whitelist assets + chaînes + adresses |
| `services/lifi/config.py` | Env LI.FI + `SWAP_FEE_BPS`, slippage |
| `services/lifi/lifi_client.py` | Client HTTP LI.FI |
| `services/lifi/lifi_validation_service.py` | Validation montants / whitelist |
| `services/lifi/lifi_quote_service.py` | Quote + simplification UX |
| `services/lifi/lifi_execute_service.py` | Execute + lifecycle |
| `services/lifi/routes.py` | Routes API |
| `services/lifi/models.py` | Table `person_wallet_swaps` |
| `alembic/versions/159_person_wallet_swaps.py` | Migration DB |

### Web (`services/arquantix/web`)

| Fichier | Rôle |
|---------|------|
| `src/lib/portal/swapClient.ts` | Client BFF portail |
| `src/app/api/portal/swaps/*` | BFF proxy |
| `src/app/api/mobile/flutter/swaps/*` | BFF mobile |
| `src/components/portal/swap/PortalSwapScreen.tsx` | UI swap |
| `src/app/app/(shell)/wallet/swap/page.tsx` | Page `/app/wallet/swap` |

### Mobile (`services/arquantix/mobile`)

| Fichier | Rôle |
|---------|------|
| `lib/features/wallet/data/lifi_swap_api.dart` | API BFF |
| `lib/features/wallet/presentation/screens/lifi_swap_screen.dart` | Écran swap |

## Routes API

| Méthode | Route | Auth | Description |
|---------|-------|------|-------------|
| GET | `/api/swaps/supported-assets` | Public | Catalogue whitelist (sans adresses) |
| POST | `/api/swaps/quote` | JWT | Estimation LI.FI |
| POST | `/api/swaps/execute` | JWT | Payload transaction signable |
| POST | `/api/swaps/{id}/submit` | JWT | Enregistre tx hash post-signature |
| GET | `/api/swaps/{id}` | JWT | Statut lifecycle |

BFF portail : `/api/portal/swaps/*`  
BFF mobile : `/api/mobile/flutter/swaps/*`

## Whitelist V1

### Chaînes

- Ethereum, Arbitrum, Base, Polygon (EVM)
- Solana

### Actifs

**V1 (actuel)** : USDC, USDT, ETH — chaînes EVM : Ethereum, Arbitrum, Base, Polygon.

*(Actifs élargis — BTC, SOL, etc. — reportés aux versions ultérieures.)*

Les actifs « majors » wrapped (BNB, XRP, TRX, AVAX) sont limités à Ethereum en V1.

## Fees & slippage

| Variable | Défaut | Description |
|----------|--------|-------------|
| `SWAP_FEE_BPS` | 50 (0,50 %) | Fee Vancelian affichée au client |
| `LIFI_FEE_BPS` | 25 | Fee integrator LI.FI (portail partenaire) |
| `DEFAULT_SLIPPAGE_BPS` | 50 | Slippage par défaut |
| Max slippage | 100 bps (1 %) | Plafond hard |

## États de transaction

```
PENDING → QUOTE_RECEIVED → AWAITING_SIGNATURE → SUBMITTED → CONFIRMED
                                                         ↘ FAILED
                                    EXPIRED (TTL quote 120s)
```

Messages UX :

- Preparing route...
- Waiting signature...
- Submitting transaction...
- Swap completed

## Variables d’environnement

```bash
LIFI_API_KEY=
LIFI_BASE_URL=https://li.quest/v1
LIFI_INTEGRATOR_ID=vancelian.finance
SWAP_FEE_BPS=50
DEFAULT_SLIPPAGE_BPS=50
LIFI_SWAPS_ENABLED=1
```

Secrets prod : `scripts/arquantix-sync-lifi-secrets.sh` (ECS `arquantix-api`).

## Flow utilisateur

1. Client choisit From / To / Amount (sélecteurs whitelist uniquement).
2. Front appelle BFF → `POST /api/swaps/quote`.
3. Backend valide, appelle LI.FI, stocke session DB, retourne quote simplifiée.
4. Client confirme → `POST /api/swaps/execute` → reçoit `transactionRequest`.
5. **Privy SDK signe** la transaction EVM (`useSendTransaction` web / `eth_sendTransaction` Flutter).
6. Client soumet tx hash → `POST /api/swaps/{id}/submit`.
7. Poll `GET /api/swaps/{id}` → backend interroge LI.FI `/status` → `CONFIRMED`.

## Tests

```bash
cd services/arquantix/api
python3 -m pytest tests/test_lifi_swap_whitelist.py tests/test_lifi_swap_routes.py tests/test_lifi_config.py -v
```

Migration requise pour tests routes :

```bash
alembic upgrade head  # revision 159
```

## Limitations V1

- Signature Privy **EVM** branchée (web + Flutter) ; **Solana** signing SDK à compléter.
- Polling LI.FI `/status` déclenché via `GET /api/swaps/{id}` (lazy, pas de worker).
- Pas de réconciliation ledger post-swap (soldes Privy via webhooks dépôt).
- Mock exchange interne (`/api/app/exchange/swap`) **coexiste** — produit LI.FI est séparé.

## Risques restants

1. **Signature client** — go-live nécessite Privy `sendTransaction` EVM + Solana.
2. **Réconciliation** — crédit destination après bridge multi-step.
3. **Rate limit LI.FI** — 100 RPM (portail) ; monitorer en prod.
4. **MiCA / VARA** — whitelist réduit le risque ; revue compliance avant gros volumes.

## Roadmap V2

- Best execution / routing intelligent
- RFQ / market makers
- Gas abstraction
- Intégration vaults / trésorerie
- Polling status LI.FI + webhooks
- Expert mode (hors scope V1)

## Explicitement hors scope V1

Memecoins, import token, ERC20 arbitraire, leverage, perps, limit orders, routing custom, expert mode.
