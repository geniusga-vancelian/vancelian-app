# Runbook — environnement local Arquantix (sécurisation opérationnelle)

**Vue d’ensemble et onboarding court** : **[LOCAL_SETUP.md](./LOCAL_SETUP.md)** (à lire en premier).

**Objectif** : un démarrage local **prévisible**, une **base logique unique**, et aucune surprise du type « autre projet Compose », « autre volume », ou « autre `DB_NAME` » sans intention explicite.

**Périmètre** : configuration locale, Docker Compose, variables d’environnement, diagnostics. Hors fonctionnalités produit.

**CMS Strapi** : **retiré** du dépôt (plus de service `arquantix-cms`, plus de port 1337 dans le compose). Le contenu applicatif passe par **Next.js + Prisma** et l’API FastAPI.

---

## 1. Source de vérité

| Élément | Fichier / emplacement |
|--------|------------------------|
| Ports, `COMPOSE_PROJECT_NAME`, `DB_*`, secrets partagés API | `.env.arquantix` (racine du dépôt) |
| API Python lancée **hors** Docker | `services/arquantix/api/.env.local` |
| RPC Base (replay / réconciliation on-chain) | `.env.arquantix` (Docker) + `api/.env.local` (scripts host) — voir [BASE_RPC_RECONCILIATION_SETUP.md](./BASE_RPC_RECONCILIATION_SETUP.md) |
| Next / Prisma / BFF lancés **hors** Docker | `services/arquantix/web/.env.local` |
| Variables chargées par Next **dans** Docker (ex. vidéo admin) | `.env` racine (aligner `DATABASE_URL` sur la même base que ci‑dessus) |
| Compose | Dans ce dépôt : **`docker-compose.arquantix-recovery.yml`** (via `ARQUANTIX_COMPOSE_FILE`) — le fichier `docker-compose.arquantix.yml` est **legacy** / référence |

**Base logique (dev local)** : le nom dans **`DB_NAME`** (`.env.arquantix`) doit être **strictement le même** que le segment de base dans **tous** les `DATABASE_URL` (API Alembic, Prisma, `.env` racine). Souvent `arquantix` ou `arquantix_fresh` selon l’historique du volume — **ne pas** changer ce nom dans un seul fichier sans aligner les autres (sinon l’app « voit » une base vide ou différente).

### Après avoir changé `DB_NAME` ou `DATABASE_URL`

Recréer les services qui embarquent ces variables (sinon les conteneurs gardent l’ancienne valeur) :

```bash
make -f Makefile.arquantix arquantix-down
make -f Makefile.arquantix arquantix-up
```

`arquantix-up` et `arquantix-up-safe` sont **identiques** : `up -d --remove-orphans` (volumes inchangés).  
(Équivalent manuel : `docker compose … up -d --remove-orphans` avec les mêmes `-f` / `--env-file` / `--project-name` que le Makefile.)

### Si la base `arquantix` n’existe pas encore dans le cluster

Lister les bases (sans nom de conteneur fixe : utiliser le **service** `arquantix-db`) :

```bash
docker compose --project-name "$(grep '^COMPOSE_PROJECT_NAME=' .env.arquantix | head -1 | cut -d= -f2)" \
  --env-file .env.arquantix -f docker-compose.arquantix.yml \
  exec arquantix-db psql -U arquantix -d postgres -c "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY 1;"
```

Si vous n’avez que d’anciennes bases de test (ex. uniquement `arquantix_fresh`) et que vous voulez **basculer** vers `arquantix` : créer la base vide puis y restaurer les données (dump/restore) ou exécuter les migrations — **ne pas** supprimer l’ancienne base tant que la copie n’est pas validée. Création minimale :

```bash
docker compose --project-name "$(grep '^COMPOSE_PROJECT_NAME=' .env.arquantix | head -1 | cut -d= -f2)" \
  --env-file .env.arquantix -f docker-compose.arquantix.yml \
  exec arquantix-db psql -U arquantix -d postgres -c "CREATE DATABASE arquantix;"
```

Puis relancer l’API pour que Alembic applique le schéma (`alembic upgrade head` au démarrage du conteneur).

---

## 2. Commande officielle de démarrage

Depuis la **racine** du dépôt :

```bash
make -f Makefile.arquantix arquantix-up
```

Cette commande utilise :

- `--project-name` = valeur de `COMPOSE_PROJECT_NAME` dans `.env.arquantix` (dans ce dépôt, souvent **`arquantixrecovery`**) ;
- `--env-file .env.arquantix` ;
- fichier compose = `ARQUANTIX_COMPOSE_FILE` dans `.env.arquantix` (souvent **`docker-compose.arquantix-recovery.yml`**).

Les **volumes de données** Postgres et Redis ont des **noms fixes** dans le compose (`arquantix_arquantix-db-data`, `arquantix_arquantix-redis-data`). Un changement de nom de projet Compose **ne crée pas** silencieusement une nouvelle base vide sur ces chemins.

**Reprise de session « tout-en-un »** (nettoyage hôte optionnel, smoke tests, worker Binance si présent) :

```bash
bash scripts/start-arquantix.sh
```

---

### Projet Compose officiel (`COMPOSE_PROJECT_NAME`)

- **Valeur attendue** : `COMPOSE_PROJECT_NAME` dans `.env.arquantix` (dans ce dépôt : **`arquantixrecovery`** — à ne pas confondre avec l’ancien namespace **`arquantix`**).
- **Qui l'utilise** : `Makefile.arquantix`, `scripts/dev-reset.sh`, `scripts/start-arquantix.sh` (garde-fous avant `make arquantix-up`).
- **Pourquoi c'est critique** : `docker compose` isole par **nom de projet**. Si la même `docker-compose.arquantix.yml` a été démarrée avec un autre `--project-name` (secours du type `arquantix_validate`, `arquantix_live`), le **Makefile** cible toujours le projet **lu dans `.env.arquantix`** — pas forcément la stack qui tourne. Les **volumes** Postgres/Redis restent les mêmes (noms figés dans le compose), mais les **conteneurs** actifs peuvent appartenir à un autre projet → désalignement `.env` / runtime.

**Vérification** : `make -f Makefile.arquantix arquantix-doctor` ou `bash scripts/arquantix_local_doctor.sh` (section *Alignement projet Compose*).

---

## 3. Que faire si le projet officiel ne pilote pas les conteneurs réellement actifs

Symptômes typiques :

- `docker compose ls` : projet **`arquantix`** en **dead**, autre ligne (**`arquantix_live`**, **`arquantix_validate`**, etc.) **running** pour le même fichier.
- `make -f Makefile.arquantix arquantix-down` ne stoppe pas les conteneurs visibles dans `docker ps`.
- Le doctor affiche **CRITICAL** : label `com.docker.compose.project` sur `arquantix-api` ≠ `COMPOSE_PROJECT_NAME` dans `.env.arquantix`.

**Procédure (sans destruction de données)** :

1. **Ne pas** multiplier les `up` avec des `-p` inventés sans lire cette section — c'est la cause habituelle de divergence.
2. **Projet réel** : inspecter un conteneur du service API, ex.  
   `docker ps -q --filter label=com.docker.compose.service=arquantix-api` puis  
   `docker inspect <id> --format '{{index .Config.Labels "com.docker.compose.project"}}'`  
   (ou : `make -f Makefile.arquantix arquantix-doctor`)
3. **Arrêter ce projet** (volumes conservés, **sans** `-v`) :  
   `docker compose --project-name <projet_réel> --env-file .env.arquantix -f docker-compose.arquantix.yml down`
4. Si **`No such container`** / fantômes : **redémarrer Docker Desktop**, puis réessayer l'étape 3 ou `bash scripts/dev-reset.sh --stop` (le script tente aussi d'arrêter des noms de projet historiques).
5. **Stack officielle** : `make -f Makefile.arquantix arquantix-up` puis `make -f Makefile.arquantix arquantix-doctor` → verdict Compose **OK**.

**À éviter** : laisser une stack de secours tourner indéfiniment ; **`down -v`** sans l'avoir décidé.

**Secours exceptionnel** : uniquement **`down`** du projet fautif pour débloquer, puis retour au projet officiel **`arquantix`** (voir étape 5).

---

## 4. Commande officielle d’arrêt

```bash
make -f Makefile.arquantix arquantix-down
```

Les données dans les volumes nommés **restent** (comportement `down` sans `-v`).

### Dépannage : erreur `No such container` au `up` (projet `arquantix` incohérent)

Symptôme : `make -f Makefile.arquantix arquantix-up` ou `docker compose … up -d` échoue avec `Error response from daemon: No such container: …` alors que `docker ps -a` montre des lignes **Dead** ou sans nom.

Cause fréquente : métadonnées Docker / Compose désynchronisées (Docker Desktop, IDs fantômes).

1. Suivre la section **§3** (projet officiel vs conteneurs actifs) : arrêter le **projet réel** lu sur les labels, puis repartir sur le projet attendu dans `.env.arquantix`.
2. **Redémarrer Docker Desktop** si besoin.
3. Réessayer `make -f Makefile.arquantix arquantix-up`.

**Ne pas** lancer une stack de secours avec un nouveau `--project-name` pour « remplacer » le Makefile sans lire §3 — cela recrée une divergence. En secours minimal, seule la commande **`down`** du projet fautif est acceptable pour débloquer, puis **`make arquantix-up`** pour le projet officiel.

### À éviter

- **`docker compose down -v`** (détruit les volumes déclarés) — les cibles **`make arquantix-reset` / `arquantix-clean`** sont **désactivées** dans le Makefile pour éviter une perte de données accidentelle ; un `down -v` manuel reste possible et dangereux.
- Changer **`COMPOSE_PROJECT_NAME`** « pour voir » : inutile pour les données (volumes nommés) mais multiplie les réseaux / conteneurs orphelins et la confusion.
- Lancer plusieurs stacks en parallèle avec des **ports identiques** dans `.env.arquantix` (conflits TCP).

---

## 5. Vérifications de santé

**Doctor local (ports + Docker web vs Next hôte + HTTP + Postgres)** — Lot 1 stabilisation :

```bash
make -f Makefile.arquantix local-doctor
```

Voir [LOCAL_STACK_DOCTOR.md](./LOCAL_STACK_DOCTOR.md). Règle : **un seul** service sur le port web (3000 par défaut) — conteneur `arquantix-web` **ou** `npm run dev`, pas les deux en conflit.

**Doctor DB (API · Alembic · Prisma, tables CMS)** — Lot 2 stabilisation :

```bash
make -f Makefile.arquantix local-db-doctor
```

Voir [LOCAL_DB_ALIGNMENT.md](./LOCAL_DB_ALIGNMENT.md) — qui lit quel `DATABASE_URL`, pourquoi l’API peut être OK alors que le web échoue, et procédure prudente si `prisma migrate deploy` ne suffit pas (base non vide).

| Vérification | Commande / critère |
|--------------|----------------------|
| Ports + conflit web Docker vs Next hôte | `make -f Makefile.arquantix local-doctor` — voir [LOCAL_STACK_DOCTOR.md](./LOCAL_STACK_DOCTOR.md) |
| Cible DB API vs web + tables Prisma CMS (`page_i18n`, …) | `make -f Makefile.arquantix local-db-doctor` — voir [LOCAL_DB_ALIGNMENT.md](./LOCAL_DB_ALIGNMENT.md) |
| Diagnostic lecture seule (Compose / labels) | `bash scripts/arquantix_local_doctor.sh` ou `make -f Makefile.arquantix arquantix-doctor` |
| API | `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:${API_PORT:-8000}/health` → **200** |
| OpenAPI | `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:${API_PORT:-8000}/openapi.json` → **200** |
| Web (Next dans Docker) | `curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:${WEB_PORT:-3000}/` → **200** (ajuster `WEB_PORT`) |
| Postgres (service compose) | `docker compose --project-name <COMPOSE_PROJECT_NAME> --env-file .env.arquantix -f docker-compose.arquantix.yml exec arquantix-db psql -U arquantix -d <DB_NAME> -c "SELECT current_database();"` |
| Migrations API | `docker compose … exec arquantix-api alembic current` (stack up) |
| Stack (script existant) | `make -f Makefile.arquantix arquantix-check` |

**WeasyPrint (PDF)** : fiable dans l’image Docker de l’API ; sur macOS **hors** Docker, le rendu peut échouer sans bibliothèques système — utiliser l’API en conteneur pour les tests PDF.

---

## 6. Ce qu’il ne faut jamais faire (sans procédure explicite)

1. **Ne pas** renommer le projet Compose au hasard (`clean2`, `recover`, etc.) pour contourner Docker : préférer `docker compose ls`, `make -f Makefile.arquantix arquantix-doctor`, la section **§3** (projet officiel vs conteneurs actifs), redémarrage de Docker Desktop si état incohérent.
2. **Ne pas** changer **`DB_NAME`** / **`DATABASE_URL`** dans **un seul** fichier sans vérifier **tous** les fichiers listés en §1 — c’est la cause typique d’une base « vide » ou incohérente.
3. **Ne pas** lancer **`alembic upgrade`** ou des scripts de migration en croyant cibler une URL si `.env.arquantix` / `.env.local` ne sont pas alignés — vérifier avec le doctor et `printenv DATABASE_URL` dans le conteneur.
4. **Ne pas** supprimer de volumes Docker **sans** avoir identifié le nom (`docker volume ls` / `inspect`).

---

## 7. Procédure de récupération

### La stack ne monte pas

1. `docker info` — si erreur : lancer Docker Desktop (macOS) ou le service Docker.
2. `bash scripts/arquantix_local_doctor.sh`
3. `docker compose --project-name "$(grep '^COMPOSE_PROJECT_NAME=' .env.arquantix | head -1 | cut -d= -f2)" --env-file .env.arquantix -f docker-compose.arquantix.yml ps -a`
4. Si erreur « No such container » / projet `dead` : redémarrer Docker Desktop ; au besoin `docker compose down --remove-orphans` pour le projet listé dans `docker compose ls` (sans `-v`).

### La base « semble vide »

1. Vérifier **`DB_NAME`** dans `.env.arquantix` et qu’il correspond au nom de base dans chaque **`DATABASE_URL`** (même chaîne que le segment final de l’URL).
2. Vérifier que vous ne vous connectez pas à une **autre** base du même cluster :  
   `docker compose --project-name "$(grep '^COMPOSE_PROJECT_NAME=' .env.arquantix | head -1 | cut -d= -f2)" --env-file .env.arquantix -f docker-compose.arquantix.yml exec arquantix-db psql -U arquantix -d postgres -c "\l"`
3. Si des données historiques existent uniquement dans une autre base logique (ex. ancienne base de test), **ne pas** deviner : dump/restore PostgreSQL ou assistance DBA — hors scope d’un simple `DB_NAME=`.

### Le service pointe vers le mauvais backend

- **Dans Docker** : `BACKEND_URL` par défaut vers `http://arquantix-api:8000` (réseau compose).
- **Next sur l’hôte** : `services/arquantix/web/.env.local` — `BACKEND_URL` / `NEXT_PUBLIC_BACKEND_URL` vers `http://127.0.0.1:${API_PORT}`.

---

## 8. Fichiers techniques (référence)

- **Volumes / réseau nommés** : `docker-compose.arquantix.yml` — noms explicites pour les données et le réseau applicatif.
- **`docker-compose.arquantix.attach-volumes.yml`** : conservé pour cas **exceptionnels** uniquement ; **pas** utilisé par le Makefile ni `dev-reset.sh` (voir entête du fichier).
- **Scripts** : `scripts/dev-reset.sh`, `scripts/start-arquantix.sh` — alignés sur `COMPOSE_PROJECT_NAME` lu depuis `.env.arquantix`, sans bascule automatique vers un second projet.
- **`dev-reset.sh` (défaut)** : Docker DB + Redis + API, **sans** `arquantix-web` ; Next sur l’hôte (`npm run dev`, port `WEB_PORT`). **`--no-next`** : lance le conteneur `arquantix-web` à la place (mocks DeFi du `.env.arquantix` neutralisés dans le compose recovery pour `NODE_ENV=production`).

---

## 9. Limites et dépendances machine

- Ports **libres** sur l’hôte (`API_PORT`, `WEB_PORT`, `DB_PORT`, etc.).
- **Docker Desktop** (ou équivalent) sain : états « fantômes » sont possibles après crashs répétés.
- **Secrets** dans `.env*` : fichiers sensibles — ne pas commiter ; faire tourner les clés exposées par erreur.

---

## 10. Prévisualisation PDF sans Flutter (design / debug)

Script : `services/arquantix/api/scripts/generate_pdf_preview.py` — réutilise les mêmes mappers / renderers que les routes `/api/app/...`.

**Depuis la racine du dépôt** (PostgreSQL exposé sur l’hôte, ex. `DB_PORT` dans `.env.arquantix`) :

```bash
make -f Makefile.arquantix pdf-preview ARGS='--email client@exemple.com --type operation --latest'
make -f Makefile.arquantix pdf-preview ARGS='--email client@exemple.com --type euro'
```

Sortie par défaut : `docs/arquantix/generated-pdfs/` (les fichiers `*.pdf` sont ignorés par git).

**WeasyPrint** : sur macOS hors Docker, le rendu peut échouer ; exécuter alors **dans** le conteneur `arquantix-api` (libs Cairo/Pango présentes), avec `DATABASE_URL=postgresql://...@arquantix-db:5432/arquantix`, et copier le fichier vers l’hôte si besoin (`docker cp`), ou `--out-dir /tmp` puis copie manuelle.

Pour comparer **itération après itération** le même cas : fixer un `--transaction-id` stable au lieu de `--latest`.

---

## 11. Voir aussi

- Charte Cursor / IA (stabilité env, interdits, process) : [CURSOR_CHARTE_ENVIRONNEMENT.md](./CURSOR_CHARTE_ENVIRONNEMENT.md)
- Prompts Cursor prêts à l’emploi (PDF, audit pré-prod, boot local) : [CURSOR_PROMPTS.md](./CURSOR_PROMPTS.md)
- Runbook fonctionnel plus large : [RUNBOOK.md](./RUNBOOK.md)

**Dernière mise à jour :** 2026-04-13
