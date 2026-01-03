# 🚀 Démarrage Rapide Strapi

## Problème avec Docker

Strapi 4.18.0 a des problèmes de build dans Docker. **Pour le développement local, utilisez Strapi directement.**

## ✅ Solution Recommandée (Développement Local)

### 1. Installer Node.js 20 via nvm

```bash
# Si nvm n'est pas installé
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.zshrc

# Installer Node.js 20
nvm install 20
nvm use 20
nvm alias default 20
```

### 2. Démarrer PostgreSQL (via Docker)

```bash
# Depuis la racine du repo
docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-db
```

### 3. Démarrer Strapi

```bash
cd services/arquantix/cms

# Installer les dépendances (première fois)
npm install

# Démarrer Strapi
npm run develop
```

### 4. Accéder à Strapi

Ouvrez **http://localhost:1337/admin** dans votre navigateur.

## 🐳 Docker (Pour la Production)

Pour la production, le build de Strapi sera fait dans le pipeline CI/CD avant le déploiement sur ECS Fargate.

## 📝 Configuration

Le fichier `.env` dans `services/arquantix/cms/` doit contenir :

```env
DATABASE_CLIENT=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5433
DATABASE_NAME=arquantix_cms
DATABASE_USERNAME=arquantix
DATABASE_PASSWORD=arquantix
DATABASE_SSL=false
HOST=0.0.0.0
PORT=1337
```

---

**Dernière mise à jour:** 2026-01-01


