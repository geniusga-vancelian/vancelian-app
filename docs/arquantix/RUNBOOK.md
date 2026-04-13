# Runbook - Arquantix Vitrine + CMS

**Date:** 2026-01-01  
**Status:** 🚧 En cours de développement

---

## TL;DR

Procédures opérationnelles pour démarrer, arrêter, réinitialiser, et gérer le développement local d'Arquantix (Next.js + Strapi + PostgreSQL via Docker Compose).

**Environnement local « verrouillé » (commandes officielles, base `arquantix`, pièges à éviter)** : voir **[LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md)**.

### Reprise de session (recommandé)

Une seule commande depuis la **racine du dépôt** :

```bash
bash scripts/start-arquantix.sh
# ou
make -f Makefile.arquantix arquantix-dev-start-clean
```

**Ce que ça fait (résumé)** : vérifie que `.env.arquantix`, `services/arquantix/api/.env.local` et `services/arquantix/web/.env.local` référencent la base canonique **`arquantix`** ; arrête les anciens workers `run_binance_ws_ingestion.py` et, sauf option, les **node / Python** qui occupent les ports Web/API sur l’hôte ; lance **`make -f Makefile.arquantix arquantix-up`** (seule voie officielle) ; contrôle conteneurs, ports, `DATABASE_URL` des services **api/web**, smoke HTTP (`/health`, `/openapi.json`, `/`, `/admin/login`) ; relance le **worker Binance WS** avec `source .env.arquantix` (logs : `/tmp/run_binance_ws_ingestion.log` par défaut).

**Options** : `bash scripts/start-arquantix.sh --skip-worker` (ne pas relancer le worker) ; `--skip-host-cleanup` (ne pas tuer les serveurs sur les ports).

**Arrêt** : `bash scripts/stop-arquantix.sh` (worker uniquement) ; `bash scripts/stop-arquantix.sh --compose-down` (worker + `arquantix-down`). Équivalent : `make -f Makefile.arquantix arquantix-dev-stop`.

**À ne pas faire** en parallèle sans le vouloir : second `next dev` ou **uvicorn** sur les mêmes ports que Docker ; ancien worker Binance laissé tourner après changement de `DB_NAME`.

Les **ports** affichés en fin de script suivent **`.env.arquantix`** (`WEB_PORT`, `API_PORT`, etc.) — souvent Web **3000** et API **8000** en local.

---

## Source de vérité des fichiers d’environnement

| Contexte | Fichier de vérité |
|----------|-------------------|
| Docker Compose / ports (`DB_PORT`, `WEB_PORT`, etc.) | `.env.arquantix` à la racine du repo |
| API Python en local (hors conteneur) | `services/arquantix/api/.env.local` |
| Next.js / BFF / Prisma en local | `services/arquantix/web/.env` + `services/arquantix/web/.env.local` |
| `.env` à la racine du repo | Aligner `DATABASE_URL` sur la même base que la stack (`arquantix` sur `DB_PORT`) ; la **référence** reste `.env.arquantix` + `.env.local` API/web |

---

## Base de données locale (API Alembic + Prisma web)

Sur la **même** base PostgreSQL partagée entre l’API et Prisma :

1. **API** : migrations **Alembic** (`services/arquantix/api`) — au démarrage du conteneur : `alembic upgrade head` (voir `services/arquantix/api/Dockerfile`).
2. **Web** : schéma Prisma — en dev local, **`prisma migrate deploy` n’est en général pas le réflexe** sur une base déjà remplie par Alembic (risque P3005). Utiliser plutôt **`npx prisma db push`** si besoin d’aligner le schéma, puis **`npx prisma db seed`** (ou `npm run db:sync` sous `services/arquantix/web`).

---

## Secours PostgreSQL (`pg_hba.conf` tronqué / octets NUL)

Si l’API ne joint plus Postgres depuis le réseau Docker (`no pg_hba.conf entry` / conteneur `arquantix-api` en restart) :

1. Conteneur `arquantix-db` actif.
2. Exécuter : `bash services/arquantix/tooling/fix_arquantix_pg_hba.sh`
3. Puis : `docker restart arquantix-api`

Les **nouveaux** volumes DB exécutent aussi `services/arquantix/db/docker-entrypoint-initdb.d/` (règle réseau) — les volumes **existants** déjà corrompus nécessitent le script ou une recréation de volume.

### Dérive schéma (`alembic_version` = head mais DDL incomplet)

Si des routes métier renvoient 500 (ex. colonne `persons.login_frozen` absente, tables `auth_webauthn_challenges` / `auth_passkeys` manquantes) **sans** vouloir effacer la base : **backup `pg_dump -Fc` d’abord**, puis appliquer le script idempotent aligné sur les migrations 110 / 128 / 129 :

```bash
docker exec -i arquantix-db psql -U arquantix -d arquantix < services/arquantix/db/repair_schema_drift_110_128_129.sql
```

Puis `docker restart arquantix-api` et retester les routes concernées.

---

## Ce qui est vrai aujourd'hui

### Commandes Disponibles

Depuis la racine du repo, utiliser `Makefile.arquantix`:

```bash
make -f Makefile.arquantix <command>
```

Ou directement avec Docker Compose (même projet et même env que `make` / `scripts/dev-reset.sh`) :

```bash
docker compose --project-name arquantix --env-file .env.arquantix -f docker-compose.arquantix.yml <command>
```

Pour éviter de répéter la ligne complète, vous pouvez définir dans votre shell :

```bash
export ARQUANTIX_COMPOSE='docker compose --project-name arquantix --env-file .env.arquantix -f docker-compose.arquantix.yml'
```

*(Adapter `--project-name` si votre `COMPOSE_PROJECT_NAME` dans `.env.arquantix` n’est pas `arquantix`.)*

---

> **⚠️ Sections ci-dessous révisées (2026-04)** — Les blocs en tête de document (**source de vérité .env**, **base Alembic + Prisma**, **pg_hba**, **dérive schéma / `repair_schema_drift_110_128_129.sql`**) font foi. Toute procédure plus bas doit utiliser **`Makefile.arquantix`** ou la même invocation Compose que ci-dessus (`--project-name` + `--env-file .env.arquantix`), et les **ports** lus dans **`.env.arquantix`** (`DB_PORT`, `WEB_PORT`, `CMS_PORT`, `API_PORT`), pas des valeurs figées obsolètes.

---

## Procédures (Docker Compose unifié)

**Ports de référence** (voir `docker-compose.arquantix.yml` + `.env.arquantix`) :

| Service | Hôte (exemples) | Conteneur |
|---------|-----------------|-----------|
| PostgreSQL app (API + Prisma) | `${DB_PORT:-5433}` — souvent **5443** en local | `arquantix-db:5432` |
| API FastAPI | `${API_PORT:-8000}` | `8000` |
| Next (image Docker) | `${WEB_PORT:-3001}` | `3000` |
| Strapi | `${CMS_PORT:-1337}` | `1337` (défaut **SQLite** embarqué, pas de service `arquantix-cms-db` dans le compose actuel) |

### 1. Démarrer les services

```bash
make -f Makefile.arquantix arquantix-up
# ou
$ARQUANTIX_COMPOSE up -d
$ARQUANTIX_COMPOSE ps
```

**URLs typiques :** site Next Docker → `http://localhost:${WEB_PORT:-3001}` ; Strapi admin → `http://localhost:${CMS_PORT:-1337}/admin` ; API → `http://127.0.0.1:${API_PORT:-8000}/health`.

### 2. Arrêter sans supprimer les volumes

```bash
make -f Makefile.arquantix arquantix-down
# ou
$ARQUANTIX_COMPOSE down
```

### 3. Réinitialiser les données (destructif)

**⚠️** Supprime les volumes du projet (PostgreSQL app, Redis, etc.).

```bash
make -f Makefile.arquantix arquantix-reset   # interactif
# ou
$ARQUANTIX_COMPOSE down -v
```

### 4. Logs

```bash
make -f Makefile.arquantix arquantix-logs
# ou
$ARQUANTIX_COMPOSE logs -f
$ARQUANTIX_COMPOSE logs -f arquantix-api
$ARQUANTIX_COMPOSE logs --tail=100 arquantix-web
```

### 5. Rebuild / shells / nettoyage profond

```bash
make -f Makefile.arquantix arquantix-build
make -f Makefile.arquantix arquantix-shell-cms
make -f Makefile.arquantix arquantix-shell-web
make -f Makefile.arquantix arquantix-clean   # down -v --rmi local
```

**Next en local (hors Docker)** : `scripts/dev-reset.sh` ou `cd services/arquantix/web && npm run dev` — souvent port **3000** ; l’API reste joignable sur `127.0.0.1:8000`.

**Next en Docker (`arquantix-web`) — volume `.next` :** le compose monte le code source sous `/app` mais un volume anonyme recouvre **`/app/.next`**. `next start` lit **uniquement** ce build : les changements dans `src/app/api/**/route.ts` ne sont **pas** pris en compte tant que vous n’avez pas regénéré `.next` (ex. `cd services/arquantix/web && npm run build` sur l’hôte, puis copier le dossier `.next` dans le conteneur **ou** `docker compose build arquantix-web` et redémarrer). Symptôme typique : BFF obsolète (ex. liste produits PE vide alors que l’API renvoie des bundles).

### 6. Worker ingestion Binance (WebSocket), hors Docker

Les scripts Python lancés **sur l’hôte** n’héritent pas des variables du `docker compose`. Après un changement de `DB_NAME` / `DATABASE_URL`, un redémarrage machine, ou si un ancien processus tourne encore, **relancer explicitement** le worker avec la même source d’env que la stack :

```bash
cd services/arquantix/api
# optionnel : pgrep -fl run_binance_ws_ingestion  puis  kill <pid>
nohup bash -c 'set -a && source ../../.env.arquantix && set +a && exec python3 scripts/run_binance_ws_ingestion.py' \
  >> /tmp/run_binance_ws_ingestion.log 2>&1 &
```

Vérifier dans `.env.arquantix` que `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` correspondent à la base de travail active (**`arquantix`** sur le port exposé par `arquantix-db`).

---

## À vérifier quand ça casse

### Ports déjà utilisés

```bash
lsof -nP -iTCP:${WEB_PORT:-3001} -sTCP:LISTEN
lsof -nP -iTCP:${CMS_PORT:-1337} -sTCP:LISTEN
lsof -nP -iTCP:${DB_PORT:-5443} -sTCP:LISTEN
```

### PostgreSQL applicatif (Arquantix API / Prisma)

Le service s’appelle **`arquantix-db`**, pas `arquantix-cms-db`. Exemple :

```bash
$ARQUANTIX_COMPOSE ps arquantix-db
$ARQUANTIX_COMPOSE logs arquantix-db
docker exec arquantix-db psql -U arquantix -d "${DB_NAME:-arquantix}" -c "SELECT current_database();"
```

### Strapi ↔ Next

Dans le réseau Compose, Strapi écoute le port **1337** (`arquantix-cms:1337`). Les variables `NEXT_PUBLIC_STRAPI_*` doivent être alignées (souvent `http://localhost:1337` depuis le navigateur sur la machine hôte).

---

**Dernière mise à jour:** 2026-04-13

