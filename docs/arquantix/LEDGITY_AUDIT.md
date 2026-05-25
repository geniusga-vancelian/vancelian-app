# Ledgity Vault — synthèse audit (v1)

Document de référence pour l’intégration Ledgity ERC4626 sur Base dans le portail Arquantix.

---

## Contrats (Base mainnet, chainId 8453)

| Rôle | Adresse |
|------|---------|
| lyUSDC vault | `0x916f179D5D9B7d8Ad815AC2f8570aabF0C6a6e38` |
| lyEURC vault | `0xFaA1e3720e6Ef8cC76A800DB7B3dF8944833b134` |
| USDC (Circle) | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` |
| EURC (Circle) | `0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42` |

---

## Modèle ERC4626

- **Dépôt** : `approve(asset, vault)` puis `deposit(assets, receiver)` sur le vault.
- **Retrait** : `withdraw(assets, receiver, owner)` — le wallet signe directement.
- **Parts (shares)** : décimales 18 ; le prix par part (PPS) augmente avec le rendement RWA.
- **Lecture on-chain** : `totalAssets()`, `convertToAssets(shares)`, `balanceOf(wallet)`.

Le portail calcule le PPS via `convertToAssets(1e18)` et affiche le rendement utilisateur à partir du ledger (principal net vs actifs courants).

---

## Architecture portail

```text
UI /app/invest (PortalLedgityVaultSection)
  → API /api/portal/ledgity/*
       ↓ si LEDGITY_LOCAL_SANDBOX_ENABLED
  ledgityLocalSandbox.ts (mock catalog / positions)
       ↓ sinon si LEDGITY_VAULTS_ENABLED
  ledgityVaultAdapter.ts (lecture ERC4626 Base RPC)
       ↓
  morphoVaultLedger.ts (Prisma — ledger partagé Morpho/Ledgity)
```

`integrationMode = ledgity_vault` sur `portal_morpho_vault_configs` et `onchain_vault_transactions`.

---

## Feature flags (prod)

| Variable | Défaut | Rôle |
|----------|--------|------|
| `LEDGITY_VAULTS_ENABLED` | `false` | Active les lectures on-chain live et les dépôts/retraits réels |
| `LEDGITY_DEPOSITS_DISABLED` | `true` | Bloque les dépôts (retraits autorisés si withdraws OK) |
| `LEDGITY_BETA_ENABLED` | `false` | Restreint l’accès aux allowlists |

**Tant que `LEDGITY_VAULTS_ENABLED=false`**, la route `prepare` live renvoie **503** avec message d’audit en cours.

---

## Risques identifiés

1. **Smart contract** — bugs ou upgrades non audités sur les vaults Ledgity / ERC4626.
2. **Liquidité RWA** — retraits peuvent être retardés si liquidité insuffisante côté protocole.
3. **Contrepartie RWA** — exposition aux actifs réels sous-jacents (crédit, immobilier, etc.).
4. **Prix de part (PPS)** — rendement non garanti ; variation selon performance RWA.
5. **Stablecoin** — USDC/EURC dépeg théorique (Circle).
6. **RPC Base** — indisponibilité transient (503 `ledgity.base_rpc_busy`).

---

## Recommandations pré-production

- [ ] Audit externe des vaults lyUSDC / lyEURC
- [ ] Tests mainnet faible montant avec `LEDGITY_VAULTS_ENABLED=true`
- [ ] Monitoring PPS / TVL (cron ou alertes)
- [ ] Runbook beta (`LEDGITY_BETA_*`) avant ouverture large
- [ ] Vérifier liquidité disponible avant activation dépôts

---

## Références code

- `src/lib/portal/ledgity/` — adapter, tx builder, sandbox, beta
- `src/app/api/portal/ledgity/` — routes BFF
- `scripts/data/ledgity-vault-configs.seed.json` — configs CMS
