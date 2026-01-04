# 🔍 AUDIT DATABASE - ARQUANTIX CMS

**Date :** 2026-01-04  
**Objectif :** État des lieux avant configuration Docker Postgres pour le CMS admin

---

## 📋 INVENTAIRE

### 1. Fichiers Docker/DB identifiés

#### Docker Compose
- ❌ **Aucun `docker-compose.yml` ou `docker-compose.yaml` trouvé** dans :
  - `/services/arquantix/` (racine du service)
  - `/services/arquantix/api/`
  - `/services/arquantix/web/`
  - `/` (racine du repo)

#### Dockerfiles
- ✅ `services/arquantix/web/Dockerfile` : Dockerfile Next.js pour déploiement ECS
  - Multi-stage build (deps, builder, runner)
  - Port exposé : 3000
  - Pas de configuration DB

- ✅ `services/arquantix/api/Dockerfile` : Dockerfile API (présent mais non audité en détail)

#### Scripts de base de données
- ✅ `services/arquantix/web/prisma/schema.prisma` : Schéma Prisma avec models User et Session
- ✅ `services/arquantix/web/prisma/seed.ts` : Script seed pour créer super admin
- ✅ `services/arquantix/web/prisma.config.ts` : Configuration Prisma v7 (datasource URL dans ce fichier)
- ❌ Aucun script SQL d'initialisation (`init.sql`, `migrations/`, etc.)

#### Variables d'environnement
- ✅ `services/arquantix/web/.env` : **EXISTE** (non lisible pour sécurité)
- ✅ `services/arquantix/web/.env.example` : **EXISTE** (template créé)

### 2. Configuration Prisma

**Fichier :** `services/arquantix/web/prisma/schema.prisma`

```prisma
datasource db {
  provider = "postgresql"
  // Pas d'URL ici (Prisma v7 utilise prisma.config.ts)
}

models:
  - User (id, email unique, passwordHash, role, createdAt)
  - Session (id, userId, token unique, expiresAt, createdAt)
```

**Fichier :** `services/arquantix/web/prisma.config.ts`

```typescript
datasource: {
  url: process.env["DATABASE_URL"],
}
```

✅ **Variable attendue :** `DATABASE_URL` (format PostgreSQL standard)

### 3. Scripts package.json

**Fichier :** `services/arquantix/web/package.json`

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "db:migrate": "prisma migrate dev",
    "db:seed": "tsx prisma/seed.ts",
    "db:generate": "prisma generate",
    "db:studio": "prisma studio"
  }
}
```

✅ Scripts DB présents et correctement configurés

### 4. Services Docker existants

**Commande :** `docker ps` (filtre postgres/5432)

```
Aucun conteneur Postgres détecté
```

**Commande :** `docker compose ps`

```
Aucun docker-compose actif détecté
```

**Références trouvées dans le codebase :**

- Documentation CMS mentionne : `docker-compose.arquantix.yml` à la racine du repo
- Port utilisé par le CMS : `5433` (config API: `database.py` ligne 15)
- Base de données CMS : `arquantix_cms` (différente de celle du web)

⚠️ **Note :** Il existe des références à un docker-compose à la racine du repo, mais le fichier n'a pas été trouvé lors de l'audit.

✅ **Aucun service Postgres actif** dans l'environnement Docker actuel

### 5. Ports utilisés

**Commande :** `lsof -i :5432 -i :51214 -i :51213`

- Port 5432 (PostgreSQL standard) : **NON UTILISÉ** ✅
- Port 51214 : **NON UTILISÉ** (Prisma Accelerate proxy - pas une vraie DB)
- Port 51213 : **NON UTILISÉ** (Prisma Accelerate proxy)
- Port 5433 : **Référencé dans API/CMS** (non vérifié - utilisé par d'autres services)

✅ **Port 5432 disponible** pour un nouveau service Postgres

⚠️ **Recommandation :** Utiliser le port **5432** (standard) pour éviter tout conflit avec le port 5433 utilisé par le CMS.

### 6. Configuration DATABASE_URL actuelle

**Fichier :** `services/arquantix/web/.env`

```
DATABASE_URL="prisma+postgres://localhost:51213/?api_key=..."
```

⚠️ **DÉCOUVERTE IMPORTANTE :** Le DATABASE_URL utilise **Prisma Accelerate** (`prisma+postgres://`) et non une connexion PostgreSQL directe.

- Format : `prisma+postgres://` (service cloud Prisma)
- Port 51213/51214 : Ports utilisés par Prisma Accelerate (proxy)
- API Key : Token d'authentification Prisma Accelerate

**Ce n'est PAS une base de données PostgreSQL locale.**

---

## 🔍 CAUSES PROBABLES

### Pourquoi DATABASE_URL pointe vers `localhost:51214` ?

**CAUSE IDENTIFIÉE :**

Le DATABASE_URL utilise **Prisma Accelerate** (service cloud Prisma), pas une base de données PostgreSQL locale.

**Prisma Accelerate :**
- Service cloud qui fait proxy vers une base de données PostgreSQL distante
- Format de connexion : `prisma+postgres://` (au lieu de `postgresql://`)
- Ports 51213/51214 : Ports locaux utilisés par le client Prisma Accelerate (tunnel/proxy)
- Nécessite une API key pour l'authentification
- La base de données PostgreSQL réelle est hébergée dans le cloud Prisma

**Conclusion :** 
- Le projet utilise actuellement **Prisma Accelerate** (service cloud)
- Pour le développement local, nous devons créer une **base PostgreSQL locale** avec Docker
- Le port 51214 n'est pas une base de données, mais un proxy Prisma Accelerate

---

## 💡 RECOMMANDATION

### Option 1 : Créer un docker-compose dédié (RECOMMANDÉ) ⭐

**Description :** Créer un `docker-compose.yml` à la racine de `/services/arquantix/web/` avec :
- Service Postgres sur port 5432 (standard)
- Volume persistant pour les données
- Variables d'environnement pour user/password
- Healthcheck

**Avantages :**
- ✅ Isolation complète du service DB
- ✅ Port standard (5432) - pas de conflit
- ✅ Facile à démarrer/arrêter avec `docker compose`
- ✅ Données persistantes via volumes
- ✅ Compatible avec tous les outils PostgreSQL
- ✅ Peut être versionné (sans secrets)

**Risques :**
- ⚠️ Nécessite Docker installé (déjà le cas vu Dockerfile)
- ⚠️ Port 5432 doit être libre (vérifié ✅)

**Commandes exactes :**

```bash
cd services/arquantix/web
docker compose up -d
npm run db:migrate
npm run db:seed
npm run dev
```

**Fichiers à créer :**
- `services/arquantix/web/docker-compose.yml`
- Mise à jour `.env` avec `DATABASE_URL` correct
- Mise à jour `.gitignore` pour exclure `.env` (si pas déjà fait)

---

### Option 2 : Postgres local/natif (NON RECOMMANDÉ)

**Description :** Installer Postgres nativement sur la machine

**Avantages :**
- ✅ Pas besoin de Docker
- ✅ Performances potentielles légèrement meilleures

**Risques :**
- ❌ Nécessite installation système
- ❌ Configuration plus complexe
- ❌ Port 5432 peut être déjà utilisé
- ❌ Moins portable (dev/staging/prod différents)
- ❌ Pas de isolation

**Conclusion :** **Option 1 recommandée** pour la simplicité, la portabilité et la cohérence avec l'infrastructure Docker existante.

---

## 🎯 ACTION RECOMMANDÉE

**Créer un `docker-compose.yml` dédié** dans `services/arquantix/web/` avec :
- Service `postgres` : image `postgres:16-alpine`
- Port mapping : `5432:5432`
- Base de données : `arquantix`
- User/Password : via variables d'environnement
- Volume : `postgres_data` pour persistance

**Mise à jour `.env` :**
```
DATABASE_URL="postgresql://arquantix:arquantix@localhost:5432/arquantix?schema=public"
```

---

**Audit terminé.** Prêt pour implémentation.

