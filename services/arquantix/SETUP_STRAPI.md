# Setup Strapi pour Arquantix

## 🚀 Démarrage Rapide

### Option 1: Via Docker Compose (Recommandé)

```bash
# Depuis la racine du repo
make -f Makefile.arquantix arquantix-up

# Ou directement
docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-cms
```

**Note:** Le premier démarrage peut prendre 3-5 minutes car Strapi s'initialise automatiquement.

### Option 2: Développement Local (sans Docker)

Si vous avez Node.js 20-24 installé:

```bash
cd services/arquantix/cms

# Si Strapi n'est pas encore initialisé
npx create-strapi-app@latest . --quickstart

# Démarrer Strapi
npm run develop
```

## 📋 Première Utilisation

1. **Accéder à l'admin:**
   - Ouvrir http://localhost:1337/admin
   - Créer votre premier compte admin

2. **Créer les Content Types:**
   - Aller dans "Content-Type Builder"
   - Créer:
     - `global` (singleton)
     - `page` (collection, avec i18n)
     - `news` (collection, avec i18n)
     - `contactSubmission` (collection)

3. **Configurer les Permissions:**
   - Settings → Users & Permissions Plugin → Roles → Public
   - Activer les permissions nécessaires

4. **Créer du contenu:**
   - Content Manager → Créer votre contenu

## 🐛 Dépannage

### Strapi ne démarre pas

Vérifier les logs:
```bash
docker compose -f docker-compose.arquantix.yml logs -f arquantix-cms
```

### Erreur d'initialisation

Si l'initialisation échoue, supprimer et réessayer:
```bash
docker compose -f docker-compose.arquantix.yml down
rm -rf services/arquantix/cms/*
docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-cms
```

---

**Dernière mise à jour:** 2026-01-01


