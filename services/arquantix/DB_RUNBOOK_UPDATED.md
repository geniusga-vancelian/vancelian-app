# Runbook — base PostgreSQL unique `arquantix`

> Ancien mode deux bases : voir l’historique dans `DB_RUNBOOK.md`. **Toute nouvelle procédure utilise ce document.**

## Cible

- **Une base** : `arquantix` (sur le cluster habituel, ex. `localhost:5443`).
- **API + Alembic + Prisma** : même `DATABASE_URL` (même **nom** de base ; le mot de passe peut différer en théorie mais en pratique identique).

## Vérification rapide

```bash
cd services/arquantix
make doctor-db
```

Si vous voyez `DATABASE NAME MISMATCH`, corrigez `api/.env*` ou `web/.env*` pour le même segment `…/arquantix`.

```bash
cd web && npm run db:info
```

## Démarrer PostgreSQL (Docker)

```bash
# depuis la racine du monorepo vancelian-app
DB_PORT=5443 DB_NAME=arquantix docker compose -f docker-compose.arquantix.yml up -d arquantix-db
```

Créer la base applicative si le conteneur n’a créé que `POSTGRES_DB` par défaut :

```bash
docker exec -it arquantix-db psql -U arquantix -d postgres -c "CREATE DATABASE arquantix OWNER arquantix;"
```

*(À ne faire qu’une fois si la base n’existe pas.)*

## Migrations

**Alembic (API)**

```bash
cd services/arquantix
make migrate-api
# ou : cd api && python3 -m alembic upgrade head
```

**Prisma (Web)**

```bash
cd services/arquantix/web
npm run db:info
npx prisma migrate deploy   # prod / staging
# ou en dev : npm run db:migrate
```

## Fusion depuis deux bases historiques

Voir **étapes détaillées** et rollback dans `DB_UNIFICATION_PHASE_2_REPORT.md` et le script :

```bash
python3 scripts/db_merge_quant_admin.py --print-backup-commands
```

## Logs au runtime

- API : ligne `[API] host=… port=… database=…` au démarrage.
- Alembic : ligne `[Alembic] …` avant `upgrade`.
- Web : `npm run db:info`.

## Tests backend

Exporter explicitement la même URL que l’API :

```bash
export DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix"
cd services/arquantix/api
pytest …
```

## Pièges

1. **`vancelian-app/.env` à la racine** : n’est pas lu par `api/database.py` — ne pas s’y fier pour l’API Arquantix.  
2. **Scripts `api/scripts/*.py`** qui n’appellent pas `load_dotenv` : exporter `DATABASE_URL` ou `set -a && source .env.local`.  
3. **Table `pages`** : côté API legacy = `legacy_json_pages` ; CMS = `pages` (Prisma).

## Si une divergence réapparaît

1. `make doctor-db`  
2. Aligner les deux `DATABASE_URL` sur `…/arquantix`  
3. Redémarrer API et `npm run dev`
