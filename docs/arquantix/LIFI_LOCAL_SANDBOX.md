# LI.FI Local Sandbox — guide développeur

Mode de développement pour tester **le flux Swap LI.FI** avec un wallet externe mocké, sans MetaMask, sans Reown, sans RPC live.

Complète le mock backend existant (`LIFI_SWAPS_MOCK` → `catalog.mock_mode` côté API Python).

---

## Architecture localhost

```text
Privy              = login réel (session portail)
Local Mock Wallet  = wallet externe vérifié sans extension
LI.FI              = quote / approve / swap simulés
Ledger swap        = historique local (backend mock ou hash 0xmocked…)
```

---

## Configuration `.env.local`

```env
# Sandbox LI.FI web (dev uniquement)
LIFI_LOCAL_SANDBOX_ENABLED=true

# Wallet externe mock (requiert un parent sandbox)
EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true

# Optionnel — mock backend Python (catalog.mock_mode)
# LIFI_SWAPS_MOCK=true   (côté services/arquantix/api)
```

**Guards :**
- `LIFI_LOCAL_SANDBOX_ENABLED` interdit en production
- `EXTERNAL_WALLET_LOCAL_MOCK_ENABLED` requiert `LIFI_LOCAL_SANDBOX_ENABLED=true` **ou** `MORPHO_LOCAL_SANDBOX_ENABLED=true`

---

## Démarrage rapide

```bash
cd services/arquantix/web
npm run dev
```

| URL | Rôle |
|-----|------|
| http://localhost:3000/dev/wallet-sandbox | Lier le Local Mock Wallet |
| http://localhost:3000/app/login | Login Privy |
| http://localhost:3000/app/swap | UI Swap LI.FI |

---

## Workflow complet

1. Configurer `.env.local` :
   ```env
   LIFI_LOCAL_SANDBOX_ENABLED=true
   EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true
   ```
2. `npm run dev`
3. Login `/app/login`
4. `/dev/wallet-sandbox` → **Link Local Mock Wallet** → **Select as execution wallet**
5. `/app/swap` → choisir paire → quote → confirm
6. Sélecteur wallet → **Local Mock Wallet**
7. Swap simulé :
   - Si `catalog.mock_mode=true` (backend) → hash mock + submit sans signature
   - Si wallet `local_mock` actif → hash `0xmocked…` sans appel wagmi/Reown
8. Historique swap affiché en success

---

## Routes dev wallet mock

| Méthode | Route | Effet |
|---------|-------|-------|
| `GET` | `/api/dev/external-wallet-mock/status` | Statut mock + session |
| `POST` | `/api/dev/external-wallet-mock/link` | Crée wallet vérifié `0x1111…1111` |
| `DELETE` | `/api/dev/external-wallet-mock/unlink` | Révoque le wallet mock |

Metadata `person_crypto_wallets` :
```json
{
  "wallet_provider": "local_mock",
  "is_verified": true,
  "morpho_sandbox": true,
  "lifi_sandbox": true
}
```

---

## Mock wallet

| Champ | Valeur |
|-------|--------|
| `address` | `0x1111111111111111111111111111111111111111` |
| `chainId` | `8453` (Base) |
| `connector` | `local_mock` |
| Fake tx hash | `0xmocked…` |

---

## Tests

```bash
npm run test:morpho-vault   # inclut externalWalletMock.test.ts
node --import tsx --test src/lib/wallet/externalWalletMock.test.ts
```

---

## Fichiers clés

| Fichier | Rôle |
|---------|------|
| `src/lib/wallet/lifiLocalSandboxConfig.ts` | Flag `LIFI_LOCAL_SANDBOX_ENABLED` |
| `src/lib/wallet/externalWalletMockConfig.ts` | Flag `EXTERNAL_WALLET_LOCAL_MOCK_ENABLED` |
| `src/lib/wallet/externalWalletMock.ts` | Constantes + hash mock |
| `src/lib/wallet/usePortalTxSigner.ts` | Bypass wagmi si `local_mock` |
| `src/components/portal/swap/useLifiSwapExecution.ts` | Swap mock sans signature |
| `src/app/dev/wallet-sandbox/` | Panneau dev |

---

## Voir aussi

- [MORPHO_LOCAL_SANDBOX.md](./MORPHO_LOCAL_SANDBOX.md) — Earn Morpho mocké avec le même wallet externe
- [LIFI_SWAP_ENGINE_V1.md](./LIFI_SWAP_ENGINE_V1.md) — moteur swap prod
