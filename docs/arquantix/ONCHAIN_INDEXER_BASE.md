# Indexer continu Base (Phase 6)

Alimente `**raw_onchain_events**` depuis la chaîne Base, sans toucher aux balances, dépôts, corrections ou discrepancies.

## Principe

```
Base RPC → scan par chunks → raw_onchain_events (insert idempotent)
                              → onchain_indexer_checkpoints (après chunk OK)
```

**Interdit** : `person_wallet_balances`, `person_wallet_deposits`, `reconciliation_corrections` apply, résolution auto des discrepancies, rebuild global.

## Variables d'environnement


| Variable                                  | Défaut  | Description                                                    |
| ----------------------------------------- | ------- | -------------------------------------------------------------- |
| `ONCHAIN_INDEXER_BASE_ENABLED`            | `false` | Écriture autorisée seulement si `true` (ou `--force` en local) |
| `ONCHAIN_INDEXER_BASE_START_BLOCK`        | —       | Premier bloc si aucun checkpoint (obligatoire au premier run)  |
| `ONCHAIN_INDEXER_BASE_CHUNK_SIZE`         | `10`    | Taille des sous-plages `eth_getLogs` (cap Alchemy Free = 10)   |
| `ONCHAIN_INDEXER_BASE_CONFIRMATIONS`      | `12`    | Blocs de finalité avant le tip                                 |
| `ONCHAIN_INDEXER_BASE_MAX_BLOCKS_PER_RUN` | `500`   | Limite par exécution `--once` (évite boucle infinie locale)    |
| `ONCHAIN_INDEXER_BASE_NATIVE_ENABLED`     | `false` | Scan ETH natif via `eth_getBlockByNumber` (plus coûteux)       |
| `BASE_RPC_URL`                            | —       | RPC Base (voir `BASE_RPC_RECONCILIATION_SETUP.md`)             |


## Commandes local

Depuis `services/arquantix/api` (charger `api/.env.local` si besoin) :

```bash
# Prévisualisation — aucune écriture
python3 -m scripts.run_onchain_indexer --chain base --once --dry-run

# Écriture raw + checkpoint (ENABLED=true requis)
export ONCHAIN_INDEXER_BASE_ENABLED=true
export ONCHAIN_INDEXER_BASE_START_BLOCK=28000000
python3 -m scripts.run_onchain_indexer --chain base --once --no-dry-run

# Local sans ENABLED (dry-run only, ou --force pour test)
python3 -m scripts.run_onchain_indexer --chain base --once --no-dry-run --force
```

Replay manuel d'une plage (Phase 4, inchangé) :

```bash
python3 -m scripts.replay_onchain --chain base --from-block X --to-block Y --dry-run \
  --wallet-address 0x... --assets USDC,EURC --block-chunk 10
```

## Commandes Docker

Sans modifier la stack : exécuter le script **depuis l'hôte** avec `DATABASE_URL` / `BASE_RPC_URL` pointant vers l'env existant, ou :

```bash
docker exec -it arquantix-api python3 -m scripts.run_onchain_indexer --chain base --once --dry-run
```

(Adapter le nom du conteneur API selon `docker compose ps`.)

**Pas de cron / worker auto** en Phase 6 : lancer `--once` via cron externe uniquement après validation ops.

## Sécurité

- Wallets suivis : `PersonCryptoWallet` actifs (`revoked_at` null).
- Insert idempotent : `(chain_id, tx_hash, log_index)` — les events déjà présents (y compris `**consumed_by_correction_id`**) ne sont **pas modifiés**.
- Checkpoint avancé **uniquement** après succès complet d'un chunk RPC.
- Erreur RPC : checkpoint inchangé, statut `error` dans `onchain_indexer_checkpoints.metadata_json`.
- Plage max **50 000** blocs par run ; `MAX_BLOCKS_PER_RUN` plafonne en local.

## Limites

- Pilote **Base** (`chain_id=8453`) uniquement.
- ERC20 : USDC, EURC, etc. selon `ERC20_CONTRACT_TO_ASSET`.
- ETH natif : optionnel, scan bloc par bloc (coût RPC élevé).
- Alchemy Free : chunks de 10 blocs max pour `eth_getLogs`.
- Pas d'API admin start/stop dans cette phase.

## Vérifier les raw events

```sql
SELECT id, chain_id, tx_hash, log_index, wallet_address, asset, amount_raw,
       consumed_by_correction_id, parsed_at
FROM raw_onchain_events
ORDER BY parsed_at DESC
LIMIT 20;
```

Checkpoint :

```sql
SELECT * FROM onchain_indexer_checkpoints WHERE chain_id = 8453;
```

## Après indexation — réconciliation

```bash
python3 -m scripts.reconcile_user --person-id <UUID> --no-dry-run
```

Puis revue admin : `/admin/onchain-reconciliation` — les discrepancies balance-only peuvent gagner une preuve `raw_onchain_event` ; l'**apply** reste soumis au workflow 5B/5C (double approbation, consommation unique).

## Migration

```bash
cd services/arquantix/api
python3 -m alembic upgrade head   # révision 165 — onchain_indexer_checkpoints
```

## Tests

```bash
python3 -m pytest tests/test_phase6_continuous_indexer.py -q
```

