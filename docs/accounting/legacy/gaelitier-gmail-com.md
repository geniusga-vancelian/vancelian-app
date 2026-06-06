# Legacy gelé — gaelitier@gmail.com

Référence audit : `docs/arquantix/gaelitier-final-audit.json` (lecture seule prod, juin 2026).

## Verdict opérationnel

**Compte sain** pour l'exploitation courante. Urgence comptaire fonds clients **clôturée**.

| Couche | Statut |
|--------|--------|
| EURC wallet Base ↔ ledger | OK (91,41) |
| USDC liquid wallet Base ↔ ledger | OK (62,64) |
| USDC vault Morpho PE | OK (114,10, hors ERC20) |
| USDT ledger ↔ PE | OK (150,03 ; physique Ethereum) |
| Swaps LI.FI | 0 zombie |
| Swap AAVE→EURC `76830776-039d-48a3-9e58-df48b0b10f7e` | ledger complet |
| Collateral Lombard actif (CBBTC/CBETH locked) | = wallet on-chain |

## Écarts legacy — ne pas auto-corriger

```yaml
legacy_frozen: true
requires_protocol_proof: true
do_not_auto_fix: true
```

### UVP (`user_vault_positions`)

| Asset | UVP legacy | PE vault |
|-------|------------|----------|
| USDC | 221 | 114,10 |
| EURC | 8 | 0 |

### OVT Lombard / vault (scope compare)

| Gap | Expected | Current PE |
|-----|----------|------------|
| USDC liability | 252 | 69 |
| USDC vault (OVT) | 121,94 | 114,10 |
| USDC trading (OVT net) | 130,06 | 62,64 |
| EURC vault (OVT/UVP) | 8 | 0 |
| CBBTC locked (OVT) | 0,005236 | 0,00031643 |
| CBETH locked (OVT) | 0,012749 | 0,00472963 |

11 OVT Lombard restants : échec `insufficient_trading_available` (collateral déjà en protocole).

### Cost basis

26 swaps CONFIRMED sans `cost_basis_executions` — traitement PR B, pas d'impact soldes.

### Reporting / UI (hors legacy)

- API `crypto_positions` affiche ledger global (ex. USDC 176) vs spendable ~62 — PR C.
- Audit v1 : `global_delta_usd` 263,91 et `fully_reconciled=false` trompeurs — PR A.

## Personnes / wallets

- person_id : `8b0e0044-f1ef-47a5-99d4-370598a77492`
- Wallet Privy Base : `0x7ae683c429ec2bc66bf1eb93713b5644dd265a44`
