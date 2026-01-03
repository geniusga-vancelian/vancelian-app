# Développement Strapi - Guide Local

## 🚀 Démarrage Rapide (Recommandé pour le développement)

Pour éviter les problèmes de build dans Docker, utilisez Strapi directement en local :

```bash
cd services/arquantix/cms

# Installer les dépendances (première fois seulement)
npm install

# Démarrer Strapi
npm run develop
```

Strapi sera accessible sur: **http://localhost:1337/admin**

## 📋 Configuration PostgreSQL

Assurez-vous que PostgreSQL est démarré via Docker Compose :

```bash
# Depuis la racine du repo
docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-db
```

Puis configurez `.env` dans `services/arquantix/cms/` :

```env
DATABASE_CLIENT=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5433
DATABASE_NAME=arquantix_cms
DATABASE_USERNAME=arquantix
DATABASE_PASSWORD=arquantix
DATABASE_SSL=false
```

## 🐳 Docker (Pour la production)

Pour la production, le build de Strapi sera fait dans le pipeline CI/CD avant le déploiement sur ECS Fargate.

Le Dockerfile est configuré pour :
- Installer les dépendances
- Builder l'admin panel
- Démarrer Strapi

## 📝 Première Utilisation

1. **Démarrer PostgreSQL** (via Docker Compose)
2. **Démarrer Strapi** (en local avec `npm run develop`)
3. **Accéder à http://localhost:1337/admin**
4. **Créer votre compte admin**
5. **Créer les Content Types**
6. **Configurer les permissions API**

## 🔧 Dépannage

### Erreur de connexion à PostgreSQL

Vérifiez que PostgreSQL est démarré :
```bash
docker compose -f docker-compose.arquantix.yml ps arquantix-db
```

### Erreur de build

Si le build échoue, supprimez `node_modules` et `.tmp` :
```bash
rm -rf node_modules .tmp
npm install
npm run develop
```

---

**Dernière mise à jour:** 2026-01-01


