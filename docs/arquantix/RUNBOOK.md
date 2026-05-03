# Runbook — Arquantix (Next.js + API + PostgreSQL)

**Date:** 2026-04-13  
**Status:** opérationnel (local)

**Entrée unique — setup local, quick start, fichiers d’env** : **[LOCAL_SETUP.md](./LOCAL_SETUP.md)**.

> **Le CMS Strapi a été retiré du projet et n’est plus utilisé.** La stack Docker locale est : **arquantix-db**, **arquantix-redis**, **arquantix-api**, **arquantix-web** (projet Compose typique : **`arquantixrecovery`**, fichier **`docker-compose.arquantix-recovery.yml`** — voir `.env.arquantix`).

---

## TL;DR

**Mode recommandé :** stack **100 % Docker** (API + Web + DB + Redis). Aucun besoin de lancer Next.js ou FastAPI sur l’hôte dans un usage standard.

Procédures pour démarrer, arrêter et dépanner Arquantix en local (**Next.js + FastAPI + PostgreSQL + Redis** via Docker Compose).

**Environnement « verrouillé »** (commandes officielles, `DB_NAME`, pièges à éviter) : **[LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md)**.

### Reprise de session (recommandé)

Depuis la **racine du dépôt** :

```bash
bash scripts/start-arquantix.sh
# ou
make -f Makefile.arquantix arquantix-dev-start-clean
```

**Résumé** : vérifie `.env.arquantix`, `services/arquantix/api/.env.local` et `services/arquantix/web/.env.local` (base **`arquantix_fresh`** selon votre réglage) ; arrête les anciens workers `run_binance_ws_ingestion.py` et, sauf option, les processus sur les ports Web/API côté hôte ; lance **`make -f Makefile.arquantix arquantix-up`** (aligné sur `.env.arquantix`) ; smoke HTTP (`/health`, `/openapi.json`, `/`, `/admin/login`) ; optionnellement worker Binance WS (logs : `/tmp/run_binance_ws_ingestion.log`).

**Options** : `--skip-worker` ; `--skip-host-cleanup`.

**Arrêt** : `bash scripts/stop-arquantix.sh` ; `bash scripts/stop-arquantix.sh --compose-down` (worker + `arquantix-down`). Équivalent : `make -f Makefile.arquantix arquantix-dev-stop`.

**À ne pas faire** sans le vouloir : second `next dev` ou **uvicorn** sur les mêmes ports que Docker ; ancien worker Binance après changement de `DB_NAME`.

Les **ports** suivent **`.env.arquantix`** (`WEB_PORT`, `API_PORT`, etc.) — souvent Web **3000** et API **8000**.

**DX (racine du dépôt)** : `make -f Makefile.arquantix local-doctor` (ports 3000 / 8000 / 5443, conflit Docker web vs Next hôte, garde-fous :3001/:5433 dans les env — [LOCAL_STACK_DOCTOR.md](./LOCAL_STACK_DOCTOR.md)), **`make -f Makefile.arquantix local-db-doctor`** (cible DB API · Alembic · Prisma + tables CMS — [LOCAL_DB_ALIGNMENT.md](./LOCAL_DB_ALIGNMENT.md)), **`make -f Makefile.arquantix local-env-guard`** (scan env listés), `make doctor` (diagnostic + durée), `make doctor-fix` (correctifs sûrs), `make status` ou `make status-watch` (tableau terminal stack **recovery**, lecture seule). Détail : [QUICK_START.md](./QUICK_START.md), entrée unique : [LOCAL_SETUP.md](./LOCAL_SETUP.md).

---

## Source de vérité des fichiers d’environnement

Tableau détaillé et modes de travail : **[LOCAL_SETUP.md](./LOCAL_SETUP.md)**.

| Contexte | Fichier de vérité |
|----------|-------------------|
| Docker Compose / ports (`DB_PORT`, `WEB_PORT`, `COMPOSE_PROJECT_NAME`, …) | `.env.arquantix` (racine du repo) |
| API Python hors conteneur | `services/arquantix/api/.env.local` |
| Next / BFF / Prisma hors conteneur | `services/arquantix/web/.env.local` (principal) ; `services/arquantix/web/.env` si utilisé |
| Variables pour Next **dans** Docker (ex. vidéo admin) | `.env` racine (`DATABASE_URL` aligné sur la même base) |

---

## Base de données locale (API Alembic + Prisma web)

Même base PostgreSQL pour l’API et Prisma :

1. **API** : Alembic — au démarrage du conteneur : `alembic upgrade head` (voir `services/arquantix/api/Dockerfile`).
2. **Web** : Prisma — en dev, **`prisma migrate deploy`** n’est en général pas le réflexe sur une base déjà remplie par Alembic (risque P3005). Préférer **`npx prisma db push`** si besoin, puis seed / `npm run db:sync` sous `services/arquantix/web`.

---

## Secours PostgreSQL (`pg_hba.conf` tronqué / octets NUL)

Si l’API ne joint plus Postgres depuis le réseau Docker :

1. Conteneur `arquantix-db` actif.
2. `bash services/arquantix/tooling/fix_arquantix_pg_hba.sh`
3. `docker restart` du conteneur `arquantix-api` (nom exact selon `docker ps`).

Les **nouveaux** volumes DB exécutent aussi `services/arquantix/db/docker-entrypoint-initdb.d/`.

### Dérive schéma (`alembic_version` = head mais DDL incomplet)

Si des routes renvoient 500 (colonnes / tables manquantes) **sans** vouloir effacer la base : **backup `pg_dump -Fc` d’abord**, puis script idempotent (voir migrations 110 / 128 / 129 dans le repo), puis redémarrage API.

---

## Architecture locale (Docker)

| Service Compose | Rôle |
|-----------------|------|
| `arquantix-db` | PostgreSQL (données app) |
| `arquantix-redis` | Redis |
| `arquantix-api` | FastAPI |
| `arquantix-web` | Next.js |

**Pas de service `arquantix-cms`.** Ancien dossier `services/arquantix/cms/` : voir [README](../../services/arquantix/cms/README.md) (deprecated).

---

## Commandes disponibles

Depuis la racine :

```bash
make -f Makefile.arquantix <command>
```

Invocation Compose **alignée sur `.env.arquantix`** (souvent `COMPOSE_PROJECT_NAME=arquantixrecovery`, `ARQUANTIX_COMPOSE_FILE=docker-compose.arquantix-recovery.yml`) :

```bash
docker compose --project-name "$(grep '^COMPOSE_PROJECT_NAME=' .env.arquantix | head -1 | cut -d= -f2)" \
  --env-file .env.arquantix \
  -f "$(grep '^ARQUANTIX_COMPOSE_FILE=' .env.arquantix | head -1 | cut -d= -f2)" \
  <subcommand>
```

Alias pratique (adapter les valeurs si besoin) :

```bash
export ARQUANTIX_COMPOSE='docker compose --project-name arquantixrecovery --env-file .env.arquantix -f docker-compose.arquantix-recovery.yml'
```

### ⚠️ IMPORTANT — Legacy (`docker-compose.arquantix.yml`)

Le fichier **`docker-compose.arquantix.yml`** est un fichier **historique (legacy)**. Il **ne doit pas** être utilisé pour **démarrer** la stack au quotidien.

**Toujours utiliser :** **`docker-compose.arquantix-recovery.yml`** (avec `COMPOSE_PROJECT_NAME` et `.env.arquantix` — voir ci‑dessus).

**Pourquoi :** éviter les conflits de réseau Docker, les incohérences de namespace, et garantir l’alignement avec `.env.arquantix`.

Le fichier legacy peut encore être mentionné dans d’anciens scripts ou teardowns ; le mode **recovery** et les procédures associées sont décrits dans [LOCAL_DOCKER_RECOVERY.md](../LOCAL_DOCKER_RECOVERY.md).

---

## Procédures

**Ports de référence** (lire `.env.arquantix`) :

| Service | Hôte (exemples) | Conteneur |
|---------|-----------------|-----------|
| PostgreSQL | `${DB_PORT:-5443}` → | `arquantix-db:5432` |
| API FastAPI | `${API_PORT:-8000}` | `8000` |
| Next | `${WEB_PORT:-3000}` | `3000` |

### 1. Démarrer les services

```bash
make -f Makefile.arquantix arquantix-up
# ou
make -f Makefile.arquantix arquantix-recovery-up
```

**URLs typiques** : Web → `http://localhost:${WEB_PORT:-3000}/` ; API → `http://127.0.0.1:${API_PORT:-8000}/health`.

### 2. Arrêter sans supprimer les volumes

```bash
make -f Makefile.arquantix arquantix-down
```

### 3. « Reset » destructif (volumes)

Les cibles **`arquantix-reset`** et **`arquantix-clean`** sont **désactivées** dans le Makefile (risque `down -v`). Ne pas utiliser `docker compose down -v` sans procédure validée.

### 4. Logs

```bash
make -f Makefile.arquantix arquantix-logs
# ou
docker compose … logs -f arquantix-api
docker compose … logs --tail=100 arquantix-web
```

### 5. Build / shell web

```bash
make -f Makefile.arquantix arquantix-build
make -f Makefile.arquantix arquantix-shell-web
```

**`arquantix-shell-cms`** : désactivé — Strapi retiré du compose.

**Next en local (hors Docker)** : `scripts/dev-reset.sh` ou `cd services/arquantix/web && npm run dev`.

**Next en Docker** — volume `.next` : le compose peut recouvrir `/app/.next` ; après changements sensibles sur les routes, rebuild image ou regénérer `.next` selon votre flux.

### 6. Worker ingestion Binance (hors Docker)

Les scripts sur l’hôte n’héritent pas du `docker compose`. Après changement de `DB_NAME` ou reboot, relancer le worker avec la même env que la stack (`source .env.arquantix`). Voir aussi `scripts/start-arquantix.sh`.

### 7. Doctor DX (`make doctor` / `make doctor-fix`)

- **`make doctor`** — diagnostic lisible : Docker, `.env.arquantix`, services **db / redis / api / web**, `/health` API, page Web, Postgres (`pg_isready`), Redis (`PING`), réseau **arquantix_recovery_network**, détection **legacy** `arquantix` (sans action automatique). Verdict final : **SAFE**, **WARNING** ou **CRITICAL** (scripts : `scripts/doctor.sh`).
- **`make doctor-fix`** — uniquement des actions **sûres** : `compose up -d --remove-orphans`, puis si besoin **`restart`** de `arquantix-api` ou `arquantix-web`. **Jamais** `down -v`, prune de volumes, ni modification de données (script : `scripts/doctor_fix.sh`).

Diagnostic Compose détaillé (historique) : `make -f Makefile.arquantix arquantix-doctor` → `scripts/arquantix_local_doctor.sh`.

---

## Autostart Mac (optionnel)

La stack Arquantix peut démarrer automatiquement au login via un **LaunchAgent**.

**Script utilisé :** `scripts/start_arquantix_recovery_boot.sh`

**Comportement :**

- Démarre uniquement la stack Docker **recovery** (`arquantixrecovery` + `docker-compose.arquantix-recovery.yml`).
- Ne fait **jamais** de `down -v` ni de suppression de volumes.
- Vérifie automatiquement la santé de l’API (`/health`).

**Logs (launchd) :**

- `/tmp/com.arquantix.autostart.stdout.log`
- `/tmp/com.arquantix.autostart.stderr.log`

**Forcer un lancement manuel** (si l’agent est installé) :

```bash
launchctl kickstart -k gui/$(id -u)/com.arquantix.autostart
```

Installation et désinstallation : [LOCAL_MAC_AUTOSTART.md](../LOCAL_MAC_AUTOSTART.md).

---

## Debug

### Ports déjà utilisés

```bash
lsof -nP -iTCP:${WEB_PORT:-3000} -sTCP:LISTEN
lsof -nP -iTCP:${API_PORT:-8000} -sTCP:LISTEN
lsof -nP -iTCP:${DB_PORT:-5443} -sTCP:LISTEN
```

### PostgreSQL applicatif

Le service s’appelle **`arquantix-db`**. Exemple (adapter projet / fichier compose) :

```bash
docker compose --project-name arquantixrecovery --env-file .env.arquantix -f docker-compose.arquantix-recovery.yml ps arquantix-db
```

---

## Voir aussi

- [QUICK_START.md](./QUICK_START.md) — onboarding : **`make setup`**
- [LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md)
- [LOCAL_DOCKER_RECOVERY.md](../LOCAL_DOCKER_RECOVERY.md)
- [API (FastAPI)](../../services/arquantix/api/) — OpenAPI `/docs`

**Dernière mise à jour :** 2026-04-13
