# 🔍 AUDIT PROFOND - Site Vitrine Arquantix Ne S'Affiche Plus

**Date:** 2026-01-08  
**Contexte:** Après redémarrage, le site vitrine ne s'affiche plus (erreur 500).  
**Méthodologie:** Audit complet SANS modification de fichiers.

---

## 📊 ÉTAPE 0 - CADRAGE DU WORKSPACE

### Structure du Repo
```
vancelian-app/services/arquantix/
├── web/          (Next.js - Site vitrine + Admin)
├── api/          (FastAPI - Backend)
├── cms/          (Strapi - CMS)
├── start-all.sh  (Script de démarrage)
├── stop-all.sh   (Script d'arrêt)
└── START_SERVERS.md (Documentation)
```

### Scripts Identifiés
- `start-all.sh` - Démarre API, CMS, Web
- `stop-all.sh` - Arrête tous les serveurs
- `cms/start-strapi.sh` - Démarre Strapi avec nvm

---

## 📋 ÉTAPE 1 - SERVICES ATTENDUS (Source: START_SERVERS.md)

### Services à Démarrer

| Service | Port | Commande | DB Requise |
|---------|------|----------|------------|
| **API** (FastAPI) | 8000 | `uvicorn main:app --reload --port 8000` | `arquantix` ou `arquantix_quant` |
| **CMS** (Strapi) | 1337 | `npm run develop` | `arquantix_cms` |
| **Web** (Next.js) | 3000 | `npm run dev` | `arquantix_admin` |
| **Database** (PostgreSQL) | 5434 ou 5433 | Docker | - |

### Ordre de Démarrage Recommandé
1. PostgreSQL (Docker)
2. API (FastAPI)
3. CMS (Strapi)
4. Web (Next.js)

---

## 🐳 ÉTAPE 2 - INFRA DB / DOCKER / VOLUMES

### Containers PostgreSQL Identifiés

| Container | Image | Port Host | Port Container | Status | Volume |
|-----------|-------|-----------|----------------|--------|--------|
| **zitadel-db** | postgres:15-alpine | **5434** | 5432 | ✅ **Running (healthy)** | `zitadel_zitadel-db-data` |
| **arquantix-db** | postgres:15-alpine | **5443** | 5432 | ❌ **Exited (255)** | `vancelian-app_arquantix-db-data` |
| **arquantix-postgres** | postgres:16-alpine | - | 5432 | ⚠️ Created (non démarré) | - |
| **vancelian-postgres** | postgres:16 | - | 5432 | ✅ Running (pas de port exposé) | - |

### Volumes Docker Identifiés
- `vancelian-app_arquantix-db-data` → `/var/lib/docker/volumes/vancelian-app_arquantix-db-data/_data`
- `zitadel_zitadel-db-data` → `/var/lib/docker/volumes/zitadel_zitadel-db-data/_data`
- `vancelian-app_arquantix-cms-db-data`
- `vancelian-app_postgres_data`

### Problème Identifié
- **arquantix-db** (port 5443) est **ARRÊTÉ** (Exited 255)
- **zitadel-db** (port 5434) est **ACTIF** mais c'est la DB d'authentification Zitadel, pas celle de l'app

---

## 🔧 ÉTAPE 3 - CONFIG ENV & DATABASE_URL

### Tableau des Configurations DATABASE_URL

| Service | Fichier | Host | Port | Database | User | Password | Status |
|---------|---------|------|------|----------|------|----------|--------|
| **Web** | `web/.env` | localhost | **5434** | `arquantix_admin` | arquantix | arquantix | ⚠️ **POINTE VERS ZITADEL-DB** |
| **Web** | `web/.env.local` | - | - | - | - | - | Pas de DB config |
| **API** | `api/.env` | localhost | **5443** | `arquantix` | arquantix | arquantix | ❌ **DB ARRÊTÉE** |
| **API** | `api/.env.local` | localhost | **5443** | `arquantix_quant` | arquantix | arquantix | ❌ **DB ARRÊTÉE** |
| **CMS** | `cms/.env` | localhost | **5433** | `arquantix_cms` | arquantix | arquantix | ❌ **PORT INEXISTANT** |
| **API (Docker)** | Container env | **arquantix-db** | 5432 | `arquantix` | arquantix | arquantix | ❌ **HOSTNAME INEXISTANT** |

### Incohérences Détectées

1. **Web pointe vers zitadel-db (port 5434)**
   - `web/.env`: `postgresql://arquantix:arquantix@localhost:5434/arquantix_admin`
   - Port 5434 = zitadel-db (DB d'auth, pas de l'app)
   - **Base `arquantix_admin` existe dans zitadel-db mais est VIDE (0 tables)**

2. **API pointe vers arquantix-db (port 5443) qui est ARRÊTÉ**
   - `api/.env`: `postgresql://arquantix:arquantix@localhost:5443/arquantix`
   - Container arquantix-db est Exited (255)
   - **API en redémarrage continu** (Restarting)

3. **API Docker utilise hostname "arquantix-db" qui n'existe pas**
   - Container env: `DATABASE_URL=postgresql://arquantix:arquantix@arquantix-db:5432/arquantix`
   - Erreur: `could not translate host name "arquantix-db" to address`

4. **CMS pointe vers port 5433 qui n'existe pas**
   - `cms/.env`: `DATABASE_PORT=5433`
   - Aucun container n'expose le port 5433

---

## 📝 ÉTAPE 4 - LOGS ET ERREURS ACTUELLES

### Logs Web (`/tmp/arquantix-web.log`)

**Erreur Principale:**
```
PrismaClientKnownRequestError: 
Invalid `prisma.page.findUnique()` invocation:

The table `public.pages` does not exist in the current database.
```

**Stack Trace:**
```
at async HomePage (webpack-internal:///(rsc)/./src/app/page.tsx:28:18)
```

**Code HTTP:** 500 (Internal Server Error)

### Logs API (`/tmp/arquantix-api.log`)

**Erreur Principale:**
```
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) 
could not translate host name "arquantix-db" to address: Name or service not known
```

**Status:** API en redémarrage continu (Restarting)

### Logs CMS (`/tmp/arquantix-cms.log`)

**Erreur Principale:**
```
npm error enoent Could not read package.json: 
Error: ENOENT: no such file or directory, 
open '/Users/.../cms/package.json'
```

**Cause:** `package.json` manquant dans `cms/`

### Logs Docker

**arquantix-db:**
- Status: Exited (255)
- Derniers logs: Checkpoints normaux, puis arrêt

**zitadel-db:**
- Status: Running (healthy)
- Port: 5434
- Base `arquantix_admin` existe mais contient **0 tables**

---

## 🔍 ÉTAPE 5 - CAUSE RACINE & DIAGNOSTIC

### Cause Racine Identifiée: **MULTIPLE FAILURES EN CASCADE**

#### A) Problème Principal: Web Pointe Vers Mauvaise DB

**Preuve:**
- `web/.env` → `localhost:5434` (zitadel-db)
- Base `arquantix_admin` existe dans zitadel-db mais est **VIDE** (0 tables)
- Erreur: `The table public.pages does not exist`

**Pourquoi ça marchait avant:**
- Probablement que `arquantix-db` (port 5443) était actif
- Ou que les migrations avaient été appliquées sur zitadel-db
- Après redémarrage, arquantix-db s'est arrêté

#### B) Problème Secondaire: arquantix-db Arrêté

**Preuve:**
- Container `arquantix-db` → Status: `Exited (255)`
- Port 5443 non accessible
- API ne peut pas se connecter

**Pourquoi:**
- Container crash au démarrage (ExitCode 255)
- Volume peut être corrompu ou permissions incorrectes

#### C) Problème Tertiaire: API Docker Utilise Hostname

**Preuve:**
- Container env: `DATABASE_URL=postgresql://...@arquantix-db:5432/...`
- Erreur: `could not translate host name "arquantix-db"`

**Pourquoi:**
- Container API essaie de résoudre "arquantix-db" comme hostname Docker
- Mais arquantix-db n'est pas dans le même réseau Docker
- Devrait utiliser `localhost:5443` depuis le host

#### D) Dépendance Site Vitrine → DB

**Preuve:**
- `web/src/app/page.tsx` ligne 13: `await prisma.page.findUnique({ where: { slug: 'home' } })`
- Le site vitrine **DÉPEND** de Prisma pour charger la page d'accueil
- Si la DB est vide ou inaccessible → erreur 500

**Pourquoi cette dépendance:**
- Architecture CMS-driven: le contenu est dans la DB
- Pas de fallback statique si DB vide

---

## 🎯 DIAGNOSTIC FINAL

### Cause Racine la Plus Probable

**SCÉNARIO: Web Branché sur Mauvaise DB (zitadel-db) + DB Vide**

1. **Avant:** 
   - `arquantix-db` (port 5443) était actif
   - Web pointait vers 5443 ou migrations appliquées
   - Site fonctionnait

2. **Après redémarrage:**
   - `arquantix-db` s'est arrêté (crash)
   - Web a été reconfiguré pour pointer vers 5434 (zitadel-db)
   - Base `arquantix_admin` existe dans zitadel-db mais est vide (0 tables)
   - Site crash avec "table pages does not exist"

### Preuves

✅ **Preuve 1:** Container arquantix-db est arrêté
```bash
docker ps -a | grep arquantix-db
# Status: Exited (255)
```

✅ **Preuve 2:** Web pointe vers port 5434 (zitadel-db)
```bash
cat web/.env | grep DATABASE_URL
# postgresql://arquantix:arquantix@localhost:5434/arquantix_admin
```

✅ **Preuve 3:** Base arquantix_admin dans zitadel-db est vide
```bash
docker exec zitadel-db psql -U arquantix -d arquantix_admin -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
# count: 0
```

✅ **Preuve 4:** Erreur Prisma confirme
```
The table `public.pages` does not exist in the current database.
```

✅ **Preuve 5:** Site vitrine dépend de DB (code source)
```typescript
// web/src/app/page.tsx:13
const page = await prisma.page.findUnique({ where: { slug: 'home' } })
```

---

## 🗺️ CARTE DES SERVICES

```
┌─────────────────────────────────────────────────────────────┐
│                    ARCHITECTURE ACTUELLE                    │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐
│   Next.js    │─────────▶│  zitadel-db │  ❌ MAUVAISE DB
│  (Port 3000) │ 5434    │  (Port 5434)│     (0 tables)
└──────────────┘         └──────────────┘
      │
      │ Erreur: table pages does not exist
      ▼
   HTTP 500

┌──────────────┐         ┌──────────────┐
│   FastAPI    │─────────▶│ arquantix-db│  ❌ ARRÊTÉ
│  (Port 8000) │ 5443    │  (Port 5443)│
└──────────────┘         └──────────────┘
      │
      │ Erreur: could not translate hostname
      ▼
   Restarting

┌──────────────┐         ┌──────────────┐
│   Strapi     │─────────▶│   (Port 5433)│  ❌ N'EXISTE PAS
│  (Port 1337) │ 5433    │              │
└──────────────┘         └──────────────┘
```

---

## 📋 PLAN D'ACTION MINIMAL

### Étape 1: Redémarrer arquantix-db (Port 5443)

**Objectif:** Remettre en service la DB principale de l'application

**Commandes:**
```bash
# 1. Vérifier pourquoi arquantix-db est arrêté
docker logs arquantix-db --tail 50

# 2. Redémarrer le container
docker start arquantix-db

# 3. Vérifier qu'il démarre correctement
docker ps | grep arquantix-db
docker logs arquantix-db --tail 20

# 4. Si crash, vérifier le volume
docker volume inspect vancelian-app_arquantix-db-data
```

**Si le container ne démarre pas:**
```bash
# Option A: Recréer le container (si volume OK)
docker rm arquantix-db
docker run -d \
  --name arquantix-db \
  -p 5443:5432 \
  -e POSTGRES_USER=arquantix \
  -e POSTGRES_PASSWORD=arquantix \
  -e POSTGRES_DB=arquantix \
  -v vancelian-app_arquantix-db-data:/var/lib/postgresql/data \
  postgres:15-alpine

# Option B: Si volume corrompu, recréer (⚠️ PERTE DE DONNÉES)
docker volume rm vancelian-app_arquantix-db-data
docker volume create vancelian-app_arquantix-db-data
# Puis recréer le container comme ci-dessus
```

### Étape 2: Corriger web/.env pour Pointer Vers arquantix-db

**Objectif:** Faire pointer Web vers la bonne DB (arquantix-db sur port 5443)

**Modification à faire:**
```env
# web/.env
# AVANT:
DATABASE_URL="postgresql://arquantix:arquantix@localhost:5434/arquantix_admin"

# APRÈS:
DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix_admin"
```

**Vérification:**
```bash
# Vérifier que la base arquantix_admin existe dans arquantix-db
docker exec arquantix-db psql -U arquantix -d arquantix_admin -c "\dt"
```

### Étape 3: Créer Base arquantix_admin dans arquantix-db (si absente)

**Objectif:** S'assurer que la base existe dans la bonne DB

**Commandes:**
```bash
# 1. Vérifier si la base existe
docker exec arquantix-db psql -U arquantix -c "\l" | grep arquantix_admin

# 2. Si absente, créer la base
docker exec arquantix-db psql -U arquantix -c "CREATE DATABASE arquantix_admin OWNER arquantix;"

# 3. Accorder les permissions
docker exec arquantix-db psql -U arquantix -c "GRANT ALL PRIVILEGES ON DATABASE arquantix_admin TO arquantix;"
```

### Étape 4: Appliquer Migrations Prisma sur arquantix_admin

**Objectif:** Créer les tables nécessaires (pages, sections, etc.)

**Commandes:**
```bash
cd services/arquantix/web

# 1. Vérifier l'état des migrations
npx prisma migrate status

# 2. Appliquer les migrations
npx prisma migrate deploy
# OU pour le développement:
npx prisma migrate dev

# 3. Vérifier que les tables sont créées
docker exec arquantix-db psql -U arquantix -d arquantix_admin -c "\dt"
```

### Étape 5: Corriger API Docker (si nécessaire)

**Objectif:** Faire pointer l'API Docker vers localhost au lieu de hostname

**Modification à faire:**
- Si l'API tourne dans Docker, modifier `DATABASE_URL` dans le container
- Utiliser `localhost:5443` au lieu de `arquantix-db:5432`
- Ou utiliser le réseau Docker si les containers sont dans le même réseau

**Commandes:**
```bash
# Vérifier la config actuelle
docker inspect arquantix-api --format '{{range .Config.Env}}{{println .}}{{end}}' | grep DATABASE

# Si nécessaire, recréer le container avec la bonne URL
# (dépend de la configuration docker-compose)
```

### Étape 6: Corriger CMS (Port 5433 → 5443)

**Objectif:** Faire pointer Strapi vers arquantix-db

**Modification à faire:**
```env
# cms/.env
# AVANT:
DATABASE_PORT=5433

# APRÈS:
DATABASE_PORT=5443
```

### Étape 7: Redémarrer Web et Vérifier

**Commandes:**
```bash
# 1. Arrêter le serveur Web actuel
pkill -f "next dev"

# 2. Redémarrer
cd services/arquantix/web
npm run dev

# 3. Vérifier que le site s'affiche
curl http://localhost:3000
# Devrait retourner HTTP 200 (ou 404 si page home n'existe pas encore)
```

---

## ✅ CHECKLIST DE VALIDATION

### Avant d'Appliquer les Correctifs

- [ ] Vérifier que `arquantix-db` peut démarrer
- [ ] Vérifier que le volume `vancelian-app_arquantix-db-data` existe et est accessible
- [ ] Vérifier les logs de `arquantix-db` pour comprendre pourquoi il s'est arrêté

### Après Application

- [ ] `arquantix-db` est Running sur port 5443
- [ ] Base `arquantix_admin` existe dans arquantix-db
- [ ] Tables Prisma sont créées (pages, sections, etc.)
- [ ] `web/.env` pointe vers `localhost:5443`
- [ ] Site vitrine retourne HTTP 200 (ou 404 si pas de contenu, mais pas 500)
- [ ] API peut se connecter à sa DB
- [ ] CMS peut se connecter à sa DB

---

## 🔧 COMMANDES DE DIAGNOSTIC (À Exécuter Avant Fix)

```bash
# 1. État des containers
docker ps -a | grep -E "arquantix|zitadel|postgres"

# 2. Ports en écoute
lsof -i -P | grep LISTEN | grep -E "5434|5443|3000|8000|1337"

# 3. Bases de données dans zitadel-db
docker exec zitadel-db psql -U zitadel -c "\l" | grep arquantix

# 4. Tables dans arquantix_admin (zitadel-db)
docker exec zitadel-db psql -U arquantix -d arquantix_admin -c "\dt"

# 5. Logs arquantix-db (pourquoi arrêté)
docker logs arquantix-db --tail 50

# 6. Volume arquantix-db
docker volume inspect vancelian-app_arquantix-db-data

# 7. Test connexion Web → DB
cd services/arquantix/web
npx prisma db pull --dry-run

# 8. Test connexion API → DB
cd services/arquantix/api
python3 -c "from database import DATABASE_URL; print(DATABASE_URL)"
```

---

## 📊 RÉSUMÉ EXÉCUTIF

### Problème
Le site vitrine ne s'affiche plus (HTTP 500) car:
1. Web pointe vers **zitadel-db** (port 5434) au lieu de **arquantix-db** (port 5443)
2. Base `arquantix_admin` dans zitadel-db est **vide** (0 tables)
3. **arquantix-db** (port 5443) est **arrêté**
4. Site vitrine **dépend de Prisma** pour charger la page d'accueil

### Solution Minimale
1. Redémarrer `arquantix-db` (port 5443)
2. Modifier `web/.env` → port 5443
3. Créer base `arquantix_admin` dans arquantix-db (si absente)
4. Appliquer migrations Prisma
5. Redémarrer Web

### Fichiers à Modifier
- `web/.env` (1 ligne: port 5434 → 5443)
- `cms/.env` (1 ligne: port 5433 → 5443) [optionnel]

### Commandes à Exécuter
- `docker start arquantix-db` (ou recréer si crash)
- `docker exec arquantix-db psql ... CREATE DATABASE ...` (si absente)
- `cd web && npx prisma migrate deploy`
- Redémarrer Web

---

**⚠️ IMPORTANT:** Ne pas modifier les fichiers avant d'avoir validé que `arquantix-db` peut démarrer et que le volume est accessible.





