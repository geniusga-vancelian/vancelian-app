# Rapport : audit et unification des connexions base de données (Arquantix)

> **Supersédé pour l’architecture cible** par la **phase 2** : base unique `arquantix` — voir `DB_UNIFICATION_PHASE_2_REPORT.md` et `DB_RUNBOOK_UPDATED.md`. Le texte ci-dessous reste utile comme historique (audit « deux bases »).

Date de l’audit factuel : 2026-04-01. Périmètre : `services/arquantix` et fichiers racine du monorepo utilisés par ce service (`docker-compose.arquantix.yml`, `.env.arquantix.example`, `vancelian-app/.env`).

---

## Executive Summary

- **Serveur PostgreSQL cible (local typique)** : un **même cluster** sur `localhost`, port hôte **`5443`** (mapping Docker fréquent `5443:5432` dans la doc et les `.env` actifs du service).
- **Deux bases logiques** sur ce cluster (architecture **volontaire**, pas un accident de multi-serveur) :
  - **`arquantix_quant`** — API FastAPI + SQLAlchemy + **Alembic** (migrations métier).
  - **`arquantix_admin`** — **Next.js + Prisma** (CMS / contenu admin, schéma Prisma).
- **Source de vérité pour l’URL API** : `api/.env.local` puis `api/.env`, puis variable d’environnement `DATABASE_URL`, puis défaut dans `api/database.py` (`localhost:5443`, `arquantix_quant`).
- **Alembic** importe `DATABASE_URL` depuis `database.py` après le même chargement dotenv → **même URL que l’API** dans un run normal.
- **Risque principal de confusion** : le fichier **`vancelian-app/.env` à la racine du repo** peut pointer vers un autre host/port (ex. `5432` / `arquantix`) alors que **l’API ne charge pas ce fichier** → configuration **fantôme** pour les développeurs qui croient que la racine pilote l’API.
- **Docker template** : `docker-compose.arquantix.yml` expose par défaut **`DB_PORT=5433`** et `POSTGRES_DB=arquantix` — **divergent** des `.env` courants du service (`5443`, bases `arquantix_quant` / `arquantix_admin`) ; à harmoniser explicitement dans `.env.arquantix` ou la doc d’exploitation.
- **Garde-fous ajoutés** : `scripts/db_config_audit.py`, `make doctor-db` / `make show-db-config`, `make migrate-api`, logs `[API]` / `[Alembic]` au démarrage / migration, `npm run db:info` côté web.

---

## Current DB Consumers

| Consumer | Fichier / mécanisme | Résolution de l’URL | Schéma |
|----------|---------------------|---------------------|--------|
| **API FastAPI** | `api/database.py` — `load_dotenv(api/.env.local)` puis `api/.env` ; `DATABASE_URL` ou défaut construit | `postgresql://…@host:port/arquantix_quant` (typique) | `public` (SQLAlchemy) |
| **Alembic** | `api/alembic/env.py` — même dotenv + `from database import DATABASE_URL` | Identique à l’API | idem |
| **Web / Prisma** | `web/prisma/schema.prisma` → `env("DATABASE_URL")` ; Next charge `.env*` à la racine `web/` | Typiquement `…/arquantix_admin` sur le **même host:port** que la quant | Tables Prisma → `public` (mappings `@map`) |
| **Scripts API** (`alembic_state_inspect.py`, `alembic_repair_and_upgrade.py`, etc.) | **`os.getenv("DATABASE_URL")` uniquement** — **ne chargent pas** `api/.env` | Dépend du shell ; risque d’écart si pas `export` ou `cd api && set -a && source .env` | — |
| **Tests backend** | `pytest` + `conftest` / skips si pas `DATABASE_URL` | Variable d’environnement explicite attendue pour certains tests | — |
| **CI GitHub** | Workflows Arquantix web/ECR vus : pas de `DATABASE_URL` dans les extraits — build/deploy web sans audit DB dans le workflow | N/A build | — |

---

## Config Sources Found

| Fichier / emplacement | Variable | Valeur ou pattern (état observé sur machine d’audit) | App | Priorité / note |
|------------------------|----------|------------------------------------------------------|-----|-----------------|
| `api/.env.local` | `DATABASE_URL` | `localhost:5443` / `arquantix_quant` | API, Alembic | Prioritaire sur `api/.env` |
| `api/.env` | `DATABASE_URL` | idem | API, Alembic | Surchargé par `.env.local` si les deux définissent |
| `web/.env` | `DATABASE_URL` | `localhost:5443` / `arquantix_admin` | Prisma, Next | Base CMS |
| `web/.env.local` | — | Peut être absent | Web | Si présent, prime sur `web/.env` (Next) |
| `web/.env.example` | placeholder | `5432` / `dbname` | Doc seulement | Ne pas confondre avec la prod locale |
| `vancelian-app/.env` (racine) | `DATABASE_URL` | Ex. `5432` / `arquantix` | **Non lu par l’API Arquantix** | **Legacy / autre outil / confusion** |
| `api/database.py` | défaut | `DB_HOST`…`DB_NAME` → `5443`, `arquantix_quant` | API | Si aucun `.env` ni `DATABASE_URL` |
| `docker-compose.arquantix.yml` | `DB_PORT`, `DB_NAME` | défaut `5433`, `arquantix` | Container Postgres | Crée la DB **initiale** du conteneur ; les apps utilisent souvent d’**autres** DB créées dans le même serveur |
| `.env.arquantix.example` | `DB_PORT`, `DB_NAME` | `5433`, `arquantix` | Compose | À aligner avec la stack réelle documentée |

---

## Active vs Legacy Configs

- **Actif (cohérent)** : API + Alembic sur `arquantix_quant` @ `localhost:5443` ; Web sur `arquantix_admin` @ même cluster.
- **Legacy / fantôme** : racine `vancelian-app/.env` avec autre port/base si personne ne s’en sert pour Arquantix API.
- **Template / ambigu** : `.env.arquantix.example` et `docker-compose.arquantix.yml` (port `5433`, nom `arquantix`) vs pratique courante `5443` + `arquantix_quant` / `arquantix_admin`.
- **Scripts shell API** : « cassés » ou trompeurs si lancés sans `DATABASE_URL` dans l’environnement alors que l’API fonctionne via fichiers `.env`.

---

## Source Of Truth

| Question | Réponse factuelle |
|----------|-------------------|
| Base réelle API en local | Celle résolue par `api/database.py` (fichiers `api/.env*` + env) — typiquement **`arquantix_quant`** |
| Base réelle Alembic | **La même** que `DATABASE_URL` importée depuis `database.py` |
| Base réelle Web/Prisma | Celle de `DATABASE_URL` côté `web/` — typiquement **`arquantix_admin`** |
| Divergence réelle multi-serveur ? | **Non** si les deux URLs ont le même `host:port` ; **oui** en bases **distinctes** mais sur **un** PostgreSQL (volontaire) |
| `repo/.env` | **Non source de vérité** pour l’API Arquantix |

---

## Target Architecture

**Recommandation durable (pragmatique)** :

1. **Un seul serveur PostgreSQL** par environnement (local/staging/prod).
2. **Deux bases de données** sur ce serveur : `arquantix_quant` (API) et `arquantix_admin` (Prisma), **tant que** les schémas ne sont pas fusionnés.
3. **Un seul port hôte** documenté pour tout le monde (ex. `5443`), avec `.env.arquantix` / compose alignés.
4. **Exception explicite** : deux bases logiques ≠ deux serveurs ; documentée ici et dans `DB_RUNBOOK.md`.

Si à terme l’équipe fusionne tout en **une seule base** + schémas ou tables unifiées, ce sera un **projet de migration** dédié (hors scope de ce rapport).

---

## Convergence Plan

| Lot | Actions |
|-----|---------|
| **1 — Vérité des configs** | Standardiser `DB_PORT` dans `.env.arquantix` / compose sur le port réellement utilisé ; commenter en tête de `vancelian-app/.env` que l’API Arquantix lit `services/arquantix/api/.env*`. |
| **2 — API / Alembic** | Déjà alignés via `database.py` ; conserver ; utiliser `make migrate-api` pour des runs reproductibles. |
| **3 — Web / Prisma** | Garder `DATABASE_URL` → `arquantix_admin` ; `npm run db:info` avant `db:migrate`. |
| **4 — Tests** | Documenter `DATABASE_URL` requise pour certains tests ; option : wrapper pytest qui charge `api/.env.local`. |
| **5 — Nettoyage** | Mettre à jour `.env.arquantix.example` pour mentionner création des DB `arquantix_quant` / `arquantix_admin` ; retirer ou clarifier les vieux exemples `5432` dans les templates si trompeurs. |
| **6 — Scripts API** | Faire pointer les scripts d’admin sur le même chargement dotenv que `database.py` (refactor léger ultérieur). |

---

## Guardrails Added

- **`scripts/db_config_audit.py`** : inventaire fichiers + URL effective API + comparaison cluster avec le web ; `--json` ; code de sortie 1 si erreur.
- **`make show-db-config` / `make doctor-db`** : exécute l’audit.
- **`make migrate-api`** : `cd api && python3 -m alembic upgrade head`.
- **API** : `api/db_connection_info.py` + log au startup dans `api/main.py` (hors mode testing).
- **Alembic** : bannière `[Alembic] host=… port=…` en début de migration online.
- **Web** : `npm run db:info` (`web/scripts/print-web-db.ts`).

---

## Files Changed

- `api/db_connection_info.py` (nouveau)
- `api/main.py` (log startup DB)
- `api/alembic/env.py` (log migration)
- `Makefile` (`show-db-config`, `doctor-db`, `migrate-api`, aide)
- `scripts/db_config_audit.py` (déjà présent ; référencé ici)
- `web/scripts/print-web-db.ts` (nouveau)
- `web/package.json` (`db:info`)
- `DB_CONNECTION_AUDIT_AND_UNIFICATION_REPORT.md` (ce fichier)
- `DB_RUNBOOK.md`

---

## Remaining Risks / Next Steps

- **Scripts Python dans `api/scripts/`** sans dotenv : risque de migrations / inspections sur la mauvaise DB si l’opérateur n’exporte pas `DATABASE_URL`.
- **Compose vs local** : tant que `DB_PORT` diffère (`5433` vs `5443`), les nouveaux devs peuvent se tromper — **harmoniser les exemples**.
- **Fusion future** une seule base : nécessite migration Prisma + Alembic et fenêtre de bascule ; ne pas improviser sans dump/restore planifié.

---

## Référence rapide : commandes de vérification

```bash
cd services/arquantix
make doctor-db
cd web && npm run db:info
```

Les logs au démarrage de l’API et d’Alembic affichent également la cible (URL masquée).
