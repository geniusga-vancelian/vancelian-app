# ⚠️ DEPRECATED — Ce fichier est obsolète

**Utilisez plutôt:** [START_ARQUANTIX.md](./START_ARQUANTIX.md) ou [README.md](./README.md)

---

# 🚀 Guide de Démarrage - Arquantix (OBSOLÈTE)

> ⚠️ **ATTENTION:** Ce guide contient des références à Strapi qui n'est plus utilisé.
> 
> **Strapi a été retiré du projet.** Utilisez [START_ARQUANTIX.md](./START_ARQUANTIX.md) pour le guide à jour.

Ce guide explique comment lancer tous les serveurs du projet Arquantix en développement local.

## 📋 Architecture

Le projet Arquantix comprend **2 services principaux** (Strapi retiré) :

1. **API** (FastAPI) - Port `8000`
2. **Web** (Next.js) - Port `3000`
3. **Database** (PostgreSQL) - Port `5443` (arquantix-db)

**⚠️ Strapi n'est plus utilisé.**

## 🔧 Prérequis

### 1. Node.js 20+
```bash
# Vérifier la version
node --version

# Si nvm n'est pas installé
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.zshrc

# Installer Node.js 20
nvm install 20
nvm use 20
nvm alias default 20
```

### 2. Python 3.9+
```bash
# Vérifier la version
python3 --version
```

### 3. Docker Desktop
- Assurez-vous que Docker Desktop est démarré
- Vérifier : `docker ps`

## 🗄️ Étape 1 : Démarrer la Base de Données

### Option A : Via Docker Compose (si disponible)
```bash
cd /Users/gael/Library/CloudStorage/OneDrive-Vancelian/Documents/vancelian-app
docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-db
```

### Option B : PostgreSQL Local
Si vous avez PostgreSQL installé localement, assurez-vous qu'il est démarré.

**Configuration attendue :**
- Host: `localhost`
- Port: `5443` (arquantix-db)
- Database: `arquantix` (API) ou `arquantix_admin` (Web)
- User: `arquantix`
- Password: `arquantix`

**⚠️ IMPORTANT:** Ne pas utiliser le port 5434 (zitadel-db) pour Arquantix.

## 🔌 Étape 2 : Démarrer l'API (FastAPI)

```bash
cd services/arquantix/api

# Installer les dépendances (première fois)
pip install -r requirements.txt

# Vérifier que le fichier .env existe avec DATABASE_URL
# Exemple : DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix"

# Démarrer l'API
uvicorn main:app --reload --port 8000
```

**L'API sera accessible sur :** http://localhost:8000
**Documentation API :** http://localhost:8000/docs

## ⚠️ Étape 3 : Strapi (RETIRÉ)

**Strapi n'est plus utilisé dans ce projet.** Toutes les fonctionnalités CMS sont gérées par Next.js via Prisma.

## 🌐 Étape 3 : Démarrer l'Application Web (Next.js)

```bash
cd services/arquantix/web

# Installer les dépendances (première fois)
npm install

# Vérifier que le fichier .env existe
# Voir web/README_ADMIN.md pour la configuration

# Appliquer les migrations Prisma (première fois)
npm run db:migrate

# Générer le client Prisma
npm run db:generate

# Démarrer le serveur de développement
npm run dev
```

**L'application sera accessible sur :** http://localhost:3000
**Admin panel :** http://localhost:3000/admin/login

**Configuration `.env` requise dans `web/` :**
```env
DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix_admin"
AUTH_SECRET="dev-secret-change-me"
ADMIN_SEED_EMAIL="admin@local.dev"
ADMIN_SEED_PASSWORD="ChangeMeNow123!"
NEXT_PUBLIC_BASE_URL="http://localhost:3000"
```

## 🎯 Démarrage Rapide (Tous les Serveurs)

Ouvrez 3 terminaux et exécutez dans chacun :

### Terminal 1 - API
```bash
cd services/arquantix/api
uvicorn main:app --reload --port 8000
```

### Terminal 2 - Web
```bash
cd services/arquantix/web
npm run dev
```

## ✅ Vérification

Une fois tous les serveurs démarrés, vérifiez :

- ✅ **API** : http://localhost:8000/docs
- ✅ **Web** : http://localhost:3000
- ✅ **Admin** : http://localhost:3000/admin/login

## 🐛 Dépannage

### Erreur de connexion à la base de données

1. Vérifier que PostgreSQL est démarré :
   ```bash
   docker ps | grep arquantix-db
   # ou
   docker exec arquantix-db psql -U arquantix -d arquantix
   ```

2. Vérifier les variables d'environnement dans les fichiers `.env`

### Erreur de port déjà utilisé

Si un port est déjà utilisé :
- **API** : Modifier le port dans la commande `uvicorn` (ex: `--port 8001`)
- **Web** : Modifier le port dans `web/.env` ou utiliser `npm run dev -- -p 3001`

### Erreur de dépendances manquantes

```bash
# API
cd services/arquantix/api
pip install -r requirements.txt

# Web
cd services/arquantix/web
rm -rf node_modules
npm install
```

## 📚 Documentation Complémentaire

- **[README.md](./README.md)** - Source de vérité (à jour)
- **[START_ARQUANTIX.md](./START_ARQUANTIX.md)** - Guide pas-à-pas détaillé (à jour)
- **API** : `api/README.md`
- **Web** : `web/README_ADMIN.md`
- **Database** : `api/README_RUN_DB.md`

---

**⚠️ Ce fichier est obsolète. Utilisez [START_ARQUANTIX.md](./START_ARQUANTIX.md) à la place.**

**Dernière mise à jour :** 2026-01-08 (marqué comme obsolète)

