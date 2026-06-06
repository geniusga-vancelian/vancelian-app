# Dette comptable legacy — périmètre gelé

Ce dossier recense les écarts **historiques** identifiés par audit qui ne doivent **pas** être corrigés automatiquement en production sans preuve protocole on-chain et validation explicite.

## Statut global

```yaml
legacy_frozen: true
requires_protocol_proof: true
do_not_auto_fix: true
impacts_client_funds: false
impacts_current_operations: false
```

## Doctrine

Les soldes **actifs** clients sont réconciliés via :

- `ledger_liquid == on_chain_wallet` (par chaîne)
- ventilation PE : `trading_available`, `vault_position`, `trading_locked_collateral`, `liability`
- swaps LI.FI : settlement ledger complet

Les écarts listés ici concernent des **migrations**, **tables legacy** (`user_vault_positions`, OVT non backfillés) et **reporting** — pas des fonds manquants ou des soldes spendables faux une fois la doctrine custody appliquée.

## Périmètres gelés

| Périmètre | Table / source | Risque si auto-fix | Action autorisée |
|-----------|----------------|-------------------|------------------|
| UVP legacy | `user_vault_positions` | double comptage vault | lecture, doc, migration planifiée |
| OVT vault | `onchain_vault_transactions` | void ledger / double vault | backfill PE uniquement avec preuve Morpho |
| OVT Lombard | `onchain_vault_transactions` | lock collateral inexistant | reconcile protocole Lombard d'abord |
| Liability historique 252 vs 69 USDC | OVT-derived vs PE metadata | fausse dette / fausse quittance | audit protocole, pas void |
| Cost basis manquants | `cost_basis_executions` | aucun sur soldes | PR B, dry-run + Go |

## Fichiers

- [`gaelitier-gmail-com.md`](./gaelitier-gmail-com.md) — cas de référence post-réconciliation (juin 2026)
- [`FROZEN_SCOPE.json`](./FROZEN_SCOPE.json) — inventaire machine-readable

## PRs de clôture (hors legacy)

1. **PR A** — Audit doctrine fix (priorité absolue)
2. **PR C** — Portfolio breakdown UI/API
3. **PR B** — Cost basis backfill (après A et C, Go explicite)

## Interdit sans accord explicite

- `void` ledger USDC / USDT / EURC pour masquer vault ou bundle
- backfill Lombard OVT en force (`insufficient_trading_available`)
- aligner UVP → PE vault par écriture directe sans reconcile Morpho
- modifier dette 69 USDC ou cible 252 USDC sans état protocole
