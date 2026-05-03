# Arquantix — environnement local (entrée unique)

**Objectif** : une référence **unique** pour onboarder en ~5 minutes, sans se perdre entre les fichiers d’env et les runbooks.

**Aller plus loin (détail)** : [LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md) (Compose, `DB_NAME`, pièges), [RUNBOOK.md](./RUNBOOK.md) (arrêt, logs, cibles Makefile), [LOCAL_DB_ALIGNMENT.md](./LOCAL_DB_ALIGNMENT.md) (Prisma vs Alembic), [../../services/arquantix/mobile/docs/LOCAL_IOS_AND_BFF.md](../../services/arquantix/mobile/docs/LOCAL_IOS_AND_BFF.md) (Flutter).

---

## 1. Source de vérité des fichiers d’environnement

| Rôle | Fichier | Contenu typique |
|------|---------|-----------------|
| **Stack Docker** (ports publiés, `COMPOSE_PROJECT_NAME`, `DB_NAME`, `DB_PORT`, `WEB_PORT`, `API_PORT`) | **`.env.arquantix`** (racine du dépôt) | Lu par `Makefile.arquantix` et Compose — **référence pour les numéros de ports** |
| **Prisma / Next sur l’hôte** (hors conteneur web) | **`services/arquantix/web/.env.local`** | `DATABASE_URL` pour Prisma, secrets dev, surcharge locale |
| **API Python sur l’hôte** (hors conteneur API) | **`services/arquantix/api/.env.local`** | `DATABASE_URL` ou `DB_*` alignés sur la même base logique |
| **Next dans Docker** (variables injectées au build / runtime conteneur) | **`.env` à la racine du repo** | Souvent `DATABASE_URL`, clés R2, etc. — **uniquement ce que le compose charge pour `arquantix-web`** |

**Règle** : le **nom de base** dans **`DB_NAME`** (`.env.arquantix`) doit correspondre au **segment base** des `DATABASE_URL` utilisés par API, web et Prisma sur **la même** instance Postgres locale — sinon « API OK, web KO » est fréquent. Voir [LOCAL_DB_ALIGNMENT.md](./LOCAL_DB_ALIGNMENT.md).

**Ports officiels (défauts courants)** : web **3000**, API **8000**, Postgres hôte **5443** — pas **3001** ni **5433** comme cibles documentées (ports historiques / erreurs).

---

## 2. Quick start (≤ 3 commandes)

Depuis la **racine du dépôt** :

```bash
cp .env.arquantix.example .env.arquantix   # une fois, puis éditer si besoin
make setup
make -f Makefile.arquantix local-doctor && make -f Makefile.arquantix local-db-doctor
```

**Résultat attendu** : stack Docker up, API `/health` OK, web répond sur le port `WEB_PORT` (souvent 3000), doctors sans **ERROR** (warnings possibles).

**Vérifier le web** : ouvrir `http://127.0.0.1:3000/fr` (ou `WEB_PORT` dans `.env.arquantix`).

---

## 3. Modes de travail

### A. Recommandé — full Docker

```bash
make -f Makefile.arquantix arquantix-up
```

Pas besoin de `npm run dev` ni `uvicorn` sur l’hôte pour un usage standard.

### B. Alternatif — Next sur l’hôte

Next écoute sur **`WEB_PORT`** (souvent 3000). **Ne pas** lancer en parallèle le conteneur `arquantix-web` sur le **même** port — le `local-doctor` signale ce conflit.

### C. Flutter iOS

- **Simulateur** : `127.0.0.1:3000` (BFF), `127.0.0.1:8000` (auth API).
- **iPhone physique** : `http://<IP_LAN_MAC>:3000` et `:8000` — jamais `localhost` vers le Mac.

Voir le doc mobile ci-dessus.

---

## 4. Commandes utiles (rappel)

| Action | Commande |
|--------|----------|
| Doctor ports / Docker vs Next hôte | `make -f Makefile.arquantix local-doctor` |
| Doctor DB API / Prisma / tables CMS | `make -f Makefile.arquantix local-db-doctor` |
| Garde-fous ports dépréciés (3001 / 5433 dans les env) | `bash scripts/arquantix_lot4_env_guard.sh` |

---

## 5. Erreurs fréquentes

| Symptôme | Piste |
|----------|--------|
| Conflit port 3000 | `local-doctor` — Docker web **et** `next dev` |
| Web 500 / Prisma | `local-db-doctor` — schéma Prisma vs base réelle |
| Flutter ne joint pas le Mac | Mauvaise IP ou `localhost` sur iPhone physique |
| « Ça marchait hier » | `DB_NAME` ou `DATABASE_URL` changé dans un seul fichier |

---

## 6. Limites réelles (pas de confusion)

| Idée reçue | Réalité |
|------------|---------|
| Prisma = Alembic | **Non** — deux migrations distinctes ; même Postgres possible, schémas gérés différemment. |
| API OK ⇒ web OK | **Non** — bases ou URLs différentes ; voir [LOCAL_DB_ALIGNMENT.md](./LOCAL_DB_ALIGNMENT.md). |
| Simulateur = iPhone | **Non** — réseau différent (`127.0.0.1` vs IP LAN). |
| Cookie = URL pour i18n | **Non** — la locale peut être cookie **et** chemin (`/fr`) ; ce sont des mécanismes différents. |

---

## 7. Documentation connexe (éviter la duplication)

- **Sécurisation env / Compose** : [LOCAL_ENV_RUNBOOK.md](./LOCAL_ENV_RUNBOOK.md)
- **Procédures longues / Makefile** : [RUNBOOK.md](./RUNBOOK.md)
- **Onboarding une commande** : [QUICK_START.md](./QUICK_START.md)

**Strapi** : retiré du runtime — ne pas suivre les anciens guides centrés Strapi ; préférer ce document et [RUNBOOK.md](./RUNBOOK.md).
