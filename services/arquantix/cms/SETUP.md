# Setup Strapi CMS - Guide d'Initialisation

**Problème:** Strapi nécessite d'être initialisé avec `create-strapi-app` avant de fonctionner dans Docker.

## Solution Rapide

### Option 1: Initialiser Strapi Localement (Recommandé)

```bash
cd services/arquantix/cms

# Sauvegarder les fichiers de config existants
mkdir -p .config-backup
cp config/* .config-backup/ 2>/dev/null || true

# Supprimer le dossier cms (on va le réinitialiser)
cd ..
rm -rf cms

# Initialiser Strapi avec la structure de base
npx create-strapi-app@latest cms \
  --quickstart \
  --no-run \
  --dbclient postgres \
  --dbhost localhost \
  --dbport 5432 \
  --dbname arquantix_cms \
  --dbusername strapi \
  --dbpassword strapi \
  --dbssl false

# Copier les fichiers de config sauvegardés
cp .config-backup/* cms/config/ 2>/dev/null || true

# Installer les dépendances
cd cms
npm install

# Revenir à la racine
cd ../../..
```

### Option 2: Utiliser Strapi via Docker uniquement (Plus complexe)

Si vous voulez éviter d'initialiser localement, il faut créer manuellement toute la structure Strapi dans le Dockerfile, ce qui est plus complexe.

## Après Initialisation

Une fois Strapi initialisé:

1. **Démarrer les services:**
   ```bash
   make -f Makefile.arquantix arquantix-up
   ```

2. **Accéder à Strapi Admin:**
   - http://localhost:1338/admin
   - Créer un compte admin

3. **Créer les Content Types:**
   - Voir `docs/arquantix/CONTENT_MODEL.md` pour les détails

---

**Note:** Pour un démarrage rapide sans initialisation complète, vous pouvez utiliser Strapi Cloud ou une instance Strapi déjà configurée.


