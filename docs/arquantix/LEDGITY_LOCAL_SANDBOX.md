# Ledgity Local Sandbox — guide développeur

Mode de développement permettant de tester **l’expérience vaults Ledgity (lyUSDC / lyEURC)** sans transaction blockchain réelle ni RPC Base live.

Le **ledger Prisma reste réel** : positions, transactions et réconciliation sont persistées en base locale.

---

## Architecture

```text
UI /app/invest (PortalLedgityVaultSection)
  → API /api/portal/ledgity/*
       ↓ si LEDGITY_LOCAL_SANDBOX_ENABLED
  ledgityLocalSandbox.ts (mock catalog / positions / prepare)
       ↓
  morphoVaultLedger.ts (Prisma réel, integrationMode = ledgity_vault)
```

---

## Workflow localhost

```env
LEDGITY_LOCAL_SANDBOX_ENABLED=true
MORPHO_LOCAL_SANDBOX_ENABLED=true   # optionnel si vous testez aussi Morpho
EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true
```

```bash
npm run ledgity:seed-vaults
npm run dev
```

Puis :

1. Login `/app/login`
2. `/dev/wallet-sandbox` → **Link Local Mock Wallet** (si mock wallet activé)
3. `/app/invest` → section **Vaults Ledgity (RWA)** → dépôt / retrait sandbox

Les opérations sandbox finalisent côté serveur (`serverCompleted: true`) sans signature on-chain.

---

## Configuration `.env.local`

```env
LEDGITY_LOCAL_SANDBOX_ENABLED=true
LEDGITY_LOCAL_SANDBOX_YIELD_BPS=900
LEDGITY_LOCAL_SANDBOX_PPS=1.0578

# Optionnel — wallet / personne cible
# LEDGITY_LOCAL_SANDBOX_PERSON_EMAIL=ledgity-sandbox@local.dev
# LEDGITY_LOCAL_SANDBOX_PERSON_ID=
# LEDGITY_LOCAL_SANDBOX_WALLET_ADDRESS=0x00000000000000000000000000000000000102
# LEDGITY_LOCAL_SANDBOX_PRIVY_WALLET_ID=local_mock_ledgity_wallet

# Beta (optionnel)
# LEDGITY_BETA_ENABLED=true
# LEDGITY_BETA_ALLOW_ALL_USERS=true
```

---

## Vaults mock

| Vault | Adresse | Actif |
|-------|---------|-------|
| lyUSDC | `0x916f179D5D9B7d8Ad815AC2f8570aabF0C6a6e38` | USDC |
| lyEURC | `0xFaA1e3720e6Ef8cC76A800DB7B3dF8944833b134` | EURC |

APY mock ~9 %, PPS mock ~1.0578 (configurable via env).

---

## Seed configs DB

```bash
npm run ledgity:seed-vaults
```

Upsert les lignes `portal_morpho_vault_configs` avec `integrationMode = ledgity_vault`.

---

## Tests

```bash
npm run test:ledgity-vault
```

---

## Garde-fous

- `LEDGITY_LOCAL_SANDBOX_ENABLED` **interdit en production** (`NODE_ENV=production` → throw).
- Live mainnet requiert `LEDGITY_VAULTS_ENABLED=true` (désactivé par défaut — voir [LEDGITY_AUDIT.md](./LEDGITY_AUDIT.md)).

---

## API routes sandbox

| Route | Méthode | Rôle |
|-------|---------|------|
| `/api/portal/ledgity/vaults` | GET | Catalog mock + beta flags |
| `/api/portal/ledgity/position` | GET | Position simulée (ledger + yield) |
| `/api/portal/ledgity/prepare` | POST | Opération finalisée serveur |
| `/api/portal/ledgity/confirm` | POST | Confirmation ledger |
| `/api/portal/ledgity/history` | GET | Historique Prisma |
