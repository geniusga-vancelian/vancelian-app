# Configuration RPC Base — scripts de réconciliation (Phase 4+)

Ce document décrit **uniquement** comment fournir une URL RPC Base (`chain_id=8453`) aux scripts
`replay_onchain`, `reconcile_wallet` et aux services qui appellent `eth_getLogs` / receipts.

**Hors périmètre** : modification Docker Compose, build web, logique métier.

Références : `services/arquantix/api/services/privy_wallet/evm_chain_config.py`, runbook env
[LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md).

---

## 1. Variable attendue (source de vérité code)

La résolution est centralisée dans `resolve_chain_rpc_url(chain_id)` :

| `chain_id` | Variables testées **dans cet ordre** (première non vide gagne) |
|------------|----------------------------------------------------------------|
| **8453** (Base) | `BASE_RPC_URL` → `BASE_RPC_URL_PRIMARY` → `NEXT_PUBLIC_BASE_RPC_URL` |
| 1 (Ethereum) | `ETHEREUM_RPC_URL` → `ETH_RPC_URL` → `MAINNET_RPC_URL` |

**Non utilisé par le code API** (présent parfois dans `.env.arquantix` à titre documentaire) :
`BASE_RPC_URL_FALLBACK` — le fallback n’est pas lu par `resolve_chain_rpc_url`.

Si aucune des trois variables Base ci-dessus n’est définie dans le process Python, les scripts
lèvent :

```text
ERROR: RPC non configuré pour chain_id=8453
```

---

## 2. Où les variables sont lues selon le contexte

### FastAPI (conteneur Docker ou API hôte)

1. Au démarrage, `database.py` charge **dans cet ordre** :
   - `services/arquantix/api/.env.local` (prioritaire)
   - `services/arquantix/api/.env`
2. Le conteneur `arquantix-api` reçoit en plus **`env_file: .env.arquantix`** (racine dépôt)
   via `docker-compose.arquantix-recovery.yml` — les variables y sont injectées dans
   l’environnement du process.

**Conséquence** : l’API Docker a en général le RPC même si `api/.env.local` ne contient pas
`BASE_RPC_URL`, tant que `.env.arquantix` (racine) le définit.

### Scripts CLI (`python3 -m scripts.replay_onchain`, `reconcile_user`, etc.)

Les scripts importent `database` → même chargement dotenv que ci-dessus :

- **`api/.env.local`** puis **`api/.env`**
- **Pas** de chargement automatique de **`.env.arquantix`** (racine)

C’est la cause habituelle de l’erreur **sur le Mac hôte** : le RPC est dans `.env.arquantix`
mais absent de `services/arquantix/api/.env.local`.

### Next.js / web

`NEXT_PUBLIC_BASE_RPC_URL` sert au **portail / wagmi** côté navigateur. L’API Python peut
aussi la lire en 3ᵉ choix pour Base, mais les scripts host doivent surtout définir
`BASE_RPC_URL` ou `BASE_RPC_URL_PRIMARY`.

---

## 3. État typique (vérification)

### Conteneur API

```bash
cd /chemin/vers/vancelian-app

docker compose --project-name arquantixrecovery \
  --env-file .env.arquantix \
  -f docker-compose.arquantix-recovery.yml \
  exec -T arquantix-api sh -c \
  'echo BASE_RPC_URL=${BASE_RPC_URL:+set}; echo BASE_RPC_URL_PRIMARY=${BASE_RPC_URL_PRIMARY:+set}'

docker compose --project-name arquantixrecovery \
  --env-file .env.arquantix \
  -f docker-compose.arquantix-recovery.yml \
  exec -T arquantix-api python3 -c \
  "from services.privy_wallet.evm_chain_config import resolve_chain_rpc_url; print('OK' if resolve_chain_rpc_url(8453) else 'MISSING')"
```

Attendu : `set` / `OK`.

### Hôte (Mac, hors Docker)

```bash
cd services/arquantix/api
python3 -c "
from services.privy_wallet.evm_chain_config import resolve_chain_rpc_url
print('OK' if resolve_chain_rpc_url(8453) else 'MISSING')
"
```

Si `MISSING` → ajouter la variable dans **`api/.env.local`** (voir §4).

---

## 4. Où définir les variables (sans toucher au Compose)

### Docker (API + scripts dans le conteneur)

| Fichier | Rôle |
|---------|------|
| **`.env.arquantix`** (racine du dépôt) | Déjà référencé par `env_file` du service `arquantix-api` |

Lignes attendues (exemple — **remplacer la clé Alchemy**, ne pas committer de secret réel) :

```bash
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<VOTRE_CLE_ALCHEMY>
BASE_RPC_URL_PRIMARY=https://base-mainnet.g.alchemy.com/v2/<VOTRE_CLE_ALCHEMY>
# Optionnel pour le web ; 3ᵉ fallback côté API Python :
NEXT_PUBLIC_BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<VOTRE_CLE_ALCHEMY>
```

Après modification : redémarrer uniquement l’API (pas de `down -v`) :

```bash
cd /chemin/vers/vancelian-app
docker compose --project-name arquantixrecovery --env-file .env.arquantix \
  -f docker-compose.arquantix-recovery.yml up -d --no-deps arquantix-api
```

### Exécution host (scripts depuis `services/arquantix/api`)

**Recommandé** — ajouter dans **`services/arquantix/api/.env.local`** (fichier local non
versionné, aligné sur [LOCAL_SETUP.md](./LOCAL_SETUP.md)) :

```bash
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<VOTRE_CLE_ALCHEMY>
```

Vous pouvez recopier la même URL que dans `.env.arquantix` (racine) sans dupliquer la clé
dans le dépôt git : copie manuelle locale uniquement.

**Alternative ponctuelle** (sans éditer `.env.local`) — exporter depuis `.env.arquantix` :

```bash
cd /chemin/vers/vancelian-app/services/arquantix/api
set -a
source ../../../.env.arquantix
set +a
python3 -m scripts.replay_onchain --chain base --from-block 100 --to-block 101 --dry-run
```

---

## 5. Commandes de test

### Host (après §4)

```bash
cd services/arquantix/api

python3 -m scripts.replay_onchain \
  --chain base \
  --from-block 100 \
  --to-block 101 \
  --dry-run
```

Succès : JSON avec `dry_run: true`, pas de ligne `ERROR: RPC non configuré`.

### Conteneur (si le host n’a pas la variable)

```bash
cd /chemin/vers/vancelian-app

docker compose --project-name arquantixrecovery \
  --env-file .env.arquantix \
  -f docker-compose.arquantix-recovery.yml \
  exec -T arquantix-api \
  python3 -m scripts.replay_onchain \
    --chain base \
    --from-block 100 \
    --to-block 101 \
    --dry-run
```

Même commande pour `reconcile_user` :

```bash
docker compose --project-name arquantixrecovery \
  --env-file .env.arquantix \
  -f docker-compose.arquantix-recovery.yml \
  exec -T arquantix-api \
  python3 -m scripts.reconcile_user \
    --person-id <UUID> \
    --dry-run
```

---

## 6. Erreurs fréquentes

| Symptôme | Cause probable | Action |
|----------|----------------|--------|
| `RPC non configuré pour chain_id=8453` sur **host** | `BASE_RPC_*` absent de `api/.env.local` ; `.env.arquantix` non chargé par `database.py` | §4 host |
| Même erreur dans le **conteneur** | `.env.arquantix` sans `BASE_RPC_URL` / clé vide ; API pas redémarrée après edit | Vérifier §3 + restart `arquantix-api` |
| `couldn't find env file: .../api/.env.arquantix` | Docker lancé depuis `api/` au lieu de la racine | `cd` racine dépôt, `--env-file .env.arquantix` |
| `ModuleNotFoundError: database` | Script lancé sans `-m scripts.*` ni `cd api` | `cd services/arquantix/api` + `python3 -m scripts.replay_onchain` |
| Replay lent / timeout | Plage de blocs trop large (max 50k) ou RPC public saturé | Réduire la plage ; Alchemy avec clé dédiée |
| `Aucun wallet actif à surveiller` | Pas de `person_crypto_wallets` actifs pour Base | Normal en dry-run sur petite plage ; vérifier wallets en DB |

---

## 7. Fichiers consultés pour cet audit

| Fichier | Rôle |
|---------|------|
| `services/arquantix/api/services/privy_wallet/evm_chain_config.py` | Résolution RPC par `chain_id` |
| `services/arquantix/api/database.py` | Chargement `.env.local` / `.env` |
| `services/arquantix/api/services/onchain_indexer/block_range_replay.py` | Appel RPC replay |
| `services/arquantix/api/scripts/replay_onchain.py` | CLI replay |
| `services/arquantix/api/scripts/reconcile_user.py` | CLI reconcile (indirect via wallet dry-run) |
| `.env.arquantix` (racine) | Variables Docker + souvent RPC Base en local |
| `services/arquantix/api/.env.local` | Surcharge host API / scripts |
| `docker-compose.arquantix-recovery.yml` | `env_file: .env.arquantix` sur `arquantix-api` |

---

## 8. Recommandation finale

1. **Conteneur** : conserver `BASE_RPC_URL` dans **`.env.arquantix`** (déjà le cas si l’audit
   `exec` affiche `set`) — aucun changement Compose nécessaire.
2. **Mac / scripts host** : ajouter **une ligne** dans
   **`services/arquantix/api/.env.local`** :

   ```bash
   BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<VOTRE_CLE_ALCHEMY>
   ```

   (copier la valeur depuis votre `.env.arquantix` local existant, sans la committer.)

3. Tant que `.env.local` n’est pas aligné, utiliser les scripts **dans le conteneur** (§5).

4. Phase 5A admin UI **ne dépend pas** du RPC host pour lister les discrepancies — seuls
   replay / indexation on-chain en ont besoin.
