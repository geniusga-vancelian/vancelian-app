# Arquantix — Quick Start (une commande)

Bienvenue sur Arquantix.

**Référence unique environnement local (sources de vérité, quick start, limites)** : **[LOCAL_SETUP.md](./LOCAL_SETUP.md)**.

**Objectif :** lancer toute la plateforme en **une seule commande**, sans configuration complexe.

---

## TL;DR

Installation rapide :

```bash
cp .env.arquantix.example .env.arquantix
make setup
```

Puis ouvrir :

- **Web** → <http://localhost:3000> (ou `WEB_PORT` dans `.env.arquantix`)
- **API** → <http://127.0.0.1:8000/docs> (ou `API_PORT`)

---

## Prérequis

Installer uniquement :

- **Docker Desktop** (obligatoire)
- **Git**

Rien d’autre n’est requis pour le mode standard (**pas** de Node, Python ou Postgres installés sur l’hôte pour faire tourner la stack).

---

## Installation

```bash
git clone <url-du-repo>
cd vancelian-app
cp .env.arquantix.example .env.arquantix   # si besoin, puis éditer
make setup
```

La cible `make setup` vit dans `Makefile.arquantix` et est **exposée à la racine** via le `Makefile` du dépôt.

---

## Ce que fait `make setup`

1. Vérifie la présence de **`.env.arquantix`** et que **Docker** répond.
2. Lance **`docker compose up -d --remove-orphans`** avec le couple lu dans `.env.arquantix` (en pratique : projet **`arquantixrecovery`**, fichier **`docker-compose.arquantix-recovery.yml`**).
3. Attend que l’**API** réponde sur **`/health`** (Alembic s’exécute **au démarrage du conteneur** API — pas d’étape manuelle séparée).
4. Affiche les URLs Web et API.

**Garde-fous :**

- pas de `down -v`
- pas de suppression de volumes
- pas de configuration manuelle au-delà de `.env.arquantix`

---

## Architecture (locale)

| Service        | URL (exemple)              | Rôle        |
|----------------|----------------------------|------------|
| Web (Next.js)  | <http://localhost:3000>    | Frontend   |
| API (FastAPI)  | <http://127.0.0.1:8000>    | Backend    |
| PostgreSQL     | `localhost:5443` (`DB_PORT`) | Base       |
| Redis          | `localhost:6379`           | Cache      |

---

## Stack Docker utilisée

**Officielle (ce dépôt) :**

- **projet :** `COMPOSE_PROJECT_NAME` dans `.env.arquantix` (souvent **`arquantixrecovery`**)
- **fichier :** `ARQUANTIX_COMPOSE_FILE` (souvent **`docker-compose.arquantix-recovery.yml`**)

### IMPORTANT — legacy

Ne **pas** utiliser **`docker-compose.arquantix.yml`** pour démarrer la stack au quotidien. Toujours **`docker-compose.arquantix-recovery.yml`** (+ `.env.arquantix`). Voir [RUNBOOK.md](./RUNBOOK.md).

---

## Commandes utiles

| Action | Commande |
|--------|----------|
| Lancer la stack | `make -f Makefile.arquantix arquantix-up` (ou `make setup` depuis zéro) |
| Arrêt (données conservées) | `make -f Makefile.arquantix arquantix-down` |
| Logs | `make -f Makefile.arquantix arquantix-logs` |
| Santé API | `curl -sS http://127.0.0.1:8000/health` |

### Diagnostic & correctifs sûrs (DX)

| Action | Commande |
|--------|----------|
| Diagnostic lisible (OK / WARNING / ERROR, verdict SAFE ou plus, durée en fin de sortie) | `make doctor` |
| Correctifs **non destructifs** uniquement (`up` idempotent, `restart` api/web si besoin — **jamais** `down -v`) | `make doctor-fix` |
| Tableau terminal **recovery** (snapshot, lecture seule) | `make status` |
| Même tableau en **rafraîchissement** (Ctrl+C pour quitter ; `STATUS_REFRESH_SEC` optionnel) | `make status-watch` |
| **Guide local** (fiche HTML dans le navigateur, une fois l’admin connecté) | ouvrir **`/guide`** — voir aussi `docs/arquantix/LOCAL_OPERATING_GUIDE.html` |

Le diagnostic détaillé Compose/DB (historique) reste : `make -f Makefile.arquantix arquantix-doctor`. L’ancien état « services Arquantix » hors recovery se trouve sous `services/arquantix/` si besoin.

**Remarque :** la copie servie par Next.js vit dans `services/arquantix/web/public/guides/arquantix-local-operating.html` ; après modification du HTML dans `docs/arquantix/`, recopier vers `public/guides/` pour l’aligner.

---

## Reboot / reprise de session

- **Autostart Mac (optionnel)** : voir [LOCAL_MAC_AUTOSTART.md](../LOCAL_MAC_AUTOSTART.md)
- **Manuel :** `make -f Makefile.arquantix arquantix-up` ou `make setup`

---

## Mode recommandé

**Standard = 100 % Docker** : pas besoin de `npm run dev` ni `uvicorn` sur l’hôte pour un usage courant — tout tourne dans les conteneurs.

---

## Problèmes fréquents

**Port déjà utilisé**

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
```

**Docker pas prêt**

Lancer Docker Desktop, puis réessayer `make setup`.

**Reset / données**

Les cibles destructives type `down -v` ne sont **pas** encouragées dans ce repo (risque perte de données). Voir [RUNBOOK.md](./RUNBOOK.md) et [LOCAL_DOCKER_RECOVERY.md](../LOCAL_DOCKER_RECOVERY.md) — **ne pas** lancer `docker compose down -v` sans décision explicite.

---

## Structure utile

```text
services/arquantix/
  api/        # FastAPI
  web/        # Next.js
  db/         # scripts d’init Postgres
```

---

## Source de vérité

| Fichier | Rôle |
|---------|------|
| `.env.arquantix` | Ports, `COMPOSE_PROJECT_NAME`, `DB_*`, etc. |
| `docker-compose.arquantix-recovery.yml` | Stack officielle |

---

## Pour aller plus loin

- [RUNBOOK.md](./RUNBOOK.md)
- [LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md)
- [LOCAL_DOCKER_RECOVERY.md](../LOCAL_DOCKER_RECOVERY.md)
- **Flutter iOS / iPhone** (BFF `:3000`, API `:8000`, simulateur vs LAN) : [../../services/arquantix/mobile/docs/LOCAL_IOS_AND_BFF.md](../../services/arquantix/mobile/docs/LOCAL_IOS_AND_BFF.md)

---

## Résumé

```bash
make setup
```

… et vous êtes prêt à développer (stack Docker alignée sur `.env.arquantix`).
