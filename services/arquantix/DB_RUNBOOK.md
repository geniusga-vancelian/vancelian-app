# Runbook — bases de données Arquantix

> **Unification (phase 2) :** configuration actuelle = **une base `arquantix`**. Procédure à jour : **`DB_RUNBOOK_UPDATED.md`**. Ce fichier décrit encore l’ancien modèle deux bases à titre historique.

## Vue d’ensemble

- **Serveur** : un PostgreSQL par environnement (souvent Docker local).
- **Port hôte typique** : **5443** (mappé sur 5432 dans le conteneur) — vérifier avec `make doctor-db`.
- **Deux bases sur le même serveur** (exception documentée, volontaire) :
  - **`arquantix_quant`** — API FastAPI + Alembic (SQLAlchemy).
  - **`arquantix_admin`** — Next.js + Prisma (CMS).

Ce n’est **pas** du multi-serveur accidentel : c’est **deux noms de base** sur **un** cluster.

---

## Où est définie la « vraie » URL ?

| Composant | Fichiers | Ordre |
|-----------|----------|--------|
| **API + Alembic** | `services/arquantix/api/.env.local`, puis `api/.env`, puis variable d’environnement `DATABASE_URL`, puis défaut dans `api/database.py` | `.env.local` prime sur `.env` |
| **Web / Prisma** | `services/arquantix/web/.env.local`, puis `web/.env`, puis `DATABASE_URL` dans le shell | `.env.local` prime sur `.env` (comme Next.js) |
| **Racine `vancelian-app/.env`** | Non lu par `api/database.py` | Ne pilote **pas** l’API Arquantix |

---

## Vérifier la DB réellement utilisée

```bash
cd services/arquantix
make doctor-db
# ou
python3 scripts/db_config_audit.py
```

Côté web seul :

```bash
cd services/arquantix/web
npm run db:info
```

Au runtime :

- Au démarrage de l’API : ligne `[API] host=… port=… database=…`.
- Lors d’un `alembic upgrade` : ligne `[Alembic] host=…`.

---

## Lancer l’API

1. Démarrer PostgreSQL (Docker ou autre) sur le **même host:port** que dans `api/.env*`.
2. Depuis `services/arquantix/api` (ou via votre script habituel) :

```bash
# Exemple — adapter à votre launcher
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Vérifier la ligne `[API]` dans la console.

---

## Lancer le web (Next)

```bash
cd services/arquantix/web
npm run db:info   # optionnel mais recommandé
npm run dev
```

`DATABASE_URL` doit pointer vers **`arquantix_admin`** sur le **même** `host:port` que l’API.

---

## Alembic (migrations API)

Recommandé (depuis le service) :

```bash
cd services/arquantix
make migrate-api
```

Équivalent manuel :

```bash
cd services/arquantix/api
python3 -m alembic upgrade head
```

La console affiche `[Alembic] host=… port=… database=…` avant d’appliquer les migrations.

---

## Prisma (migrations web)

```bash
cd services/arquantix/web
npm run db:info
npm run db:migrate
```

---

## Tests backend

Certains tests exigent `DATABASE_URL` dans l’environnement ; sans elle, des tests sont ignorés (`pytest.skip`). Avant de lancer la suite :

```bash
export DATABASE_URL="postgresql://…/arquantix_quant"   # aligner sur api/.env.local
cd services/arquantix/api
pytest …
```

*(Amélioration possible : charger automatiquement `api/.env.local` dans `conftest.py` — hors runbook.)*

---

## Scripts `api/scripts/*` (piège)

Des scripts comme `alembic_state_inspect.py` lisent **seulement** `os.environ["DATABASE_URL"]`. Ils **ne** chargent **pas** `api/.env`. Toujours :

```bash
cd services/arquantix/api
set -a && source .env.local 2>/dev/null; set +a
python3 scripts/alembic_state_inspect.py
```

ou exporter `DATABASE_URL` explicitement.

---

## Si une divergence réapparaît

1. `make doctor-db` — lire les **WARNINGS** (ex. racine `.env` vs API).
2. Comparer `host:port` entre bloc « API + Alembic » et « Web/Prisma » : ils doivent être **identiques** ; les **noms de base** peuvent différer (`arquantix_quant` vs `arquantix_admin`).
3. Corriger **uniquement** les fichiers concernés (`api/.env*`, `web/.env*`), pas des fichiers « fantômes ».
4. Redémarrer API et web ; refaire `make doctor-db`.

---

## Docker Compose (racine monorepo)

Fichier : `vancelian-app/docker-compose.arquantix.yml`. Variables typiques : `DB_PORT`, `DB_NAME`. Le conteneur crée une DB initiale (`POSTGRES_DB`) ; les applications peuvent utiliser d’**autres** bases créées manuellement (`CREATE DATABASE arquantix_quant`, etc.). Aligner **`.env.arquantix`** sur le port et les noms réellement utilisés par `api/` et `web/`.

---

## Documents liés

- Rapport détaillé : `DB_CONNECTION_AUDIT_AND_UNIFICATION_REPORT.md`
- Doc canonique Alembic / DB : `docs/canonical/60_DATABASE_ALEMBIC.md`
