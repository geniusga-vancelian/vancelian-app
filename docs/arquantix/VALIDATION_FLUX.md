# Validation du Flux Contenu → CMS → Site Vitrine

**Date:** 2026-01-01

---

## TL;DR

Guide de validation pour vérifier que le flux Strapi → Next.js fonctionne correctement.

---

## Prérequis

1. **PostgreSQL démarré:**
   ```bash
   make -f Makefile.arquantix arquantix-db-up
   ```

2. **Strapi démarré:**
   ```bash
   make -f Makefile.arquantix arquantix-strapi-local
   # Attendre: "Server running at http://0.0.0.0:1337/admin"
   ```

3. **Next.js démarré:**
   ```bash
   docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-web
   ```

---

## Validation Strapi

### 1. Vérifier que Strapi est accessible

```bash
curl http://localhost:1337/admin
# Doit retourner du HTML (page de login/admin)
```

### 2. Créer un compte admin (si premier démarrage)

1. Aller sur http://localhost:1337/admin
2. Créer un compte admin
3. Se connecter

### 3. Créer les Content Types

**Option A - Automatique (Recommandé):**

Les Content Types sont définis dans `src/api/*/content-types/*/schema.json`.  
Strapi les créera automatiquement au démarrage.

**Content Types créés:**
- `page` (collection, i18n: fr, en) → `src/api/page/content-types/page/schema.json`
- `global` (singleton) → `src/api/global/content-types/global/schema.json`
- `news` (collection, i18n: fr, en) → `src/api/news/content-types/news/schema.json`
- `contact-submission` (collection) → `src/api/contact-submission/content-types/contact-submission/schema.json`

**Option B - Manuel (si nécessaire):**

1. Aller dans **Content-Type Builder**
2. Créer un nouveau Content Type: **Page**
3. Ajouter les champs:
   - `slug` (UID, Required, Unique)
   - `title` (Text, Required)
   - `content` (RichText, Optional)
   - `seo` (JSON, Optional)
4. Activer **Localization** (i18n)
5. Sélectionner les locales: **fr**, **en**
6. Sauvegarder

**Pour Global (singleton):**
1. Aller dans **Content-Type Builder**
2. Créer un nouveau **Single Type**: **Global**
3. Ajouter les champs:
   - `branding` (JSON, Required)
   - `socials` (JSON, Optional)
   - `seo` (JSON, Optional)
4. Sauvegarder

### 5. Créer les pages "home" FR et EN

1. Aller dans **Content Manager**
2. Sélectionner **Page**
3. Créer une nouvelle entrée:
   - **Locale:** fr
   - **slug:** home
   - **title:** Accueil
   - **content:** (optionnel)
4. Sauvegarder et **Publier**
5. Créer une autre entrée:
   - **Locale:** en
   - **slug:** home
   - **title:** Home
   - **content:** (optionnel)
6. Sauvegarder et **Publier**

### 6. Créer le Global (Singleton)

1. Aller dans **Content Manager**
2. Sélectionner **Global**
3. Créer une entrée:
   - **branding:**
     ```json
     {
       "logo": "/uploads/logo.png",
       "name": "Arquantix",
       "tagline": "Innovation Technology"
     }
     ```
   - **socials:**
     ```json
     {
       "twitter": "",
       "linkedin": ""
     }
     ```
   - **seo:**
     ```json
     {
       "defaultTitle": "Arquantix",
       "defaultDescription": "Arquantix - Innovation Technology"
     }
     ```
4. Sauvegarder et **Publier**

### 7. Configurer les Permissions PUBLIC

1. Aller dans **Settings** → **Users & Permissions Plugin** → **Roles** → **Public**
2. Activer les permissions:
   - **Global:** `find`
   - **Page:** `find`, `findOne`
   - **News:** `find`, `findOne` (si créé)
   - **Contact Submission:** `create`

### 8. Tester l'API Strapi

```bash
# Test Global
curl http://localhost:1337/api/global

# Test Pages FR
curl "http://localhost:1337/api/pages?filters[slug][\$eq]=home&filters[locale][\$eq]=fr"

# Test Pages EN
curl "http://localhost:1337/api/pages?filters[slug][\$eq]=home&filters[locale][\$eq]=en"
```

**Résultat attendu:** JSON avec `data` contenant les entrées.

---

## Validation Next.js

### 1. Vérifier que Next.js est accessible

```bash
curl http://localhost:3011
# Doit retourner du HTML (redirection vers /fr)
```

### 2. Vérifier la configuration Strapi URL

**Dans docker-compose.arquantix.yml:**
```yaml
NEXT_PUBLIC_STRAPI_URL: http://host.docker.internal:1337
NEXT_PUBLIC_STRAPI_API_URL: http://host.docker.internal:1337/api
```

**Vérifier dans le container:**
```bash
docker compose -f docker-compose.arquantix.yml exec arquantix-web env | grep STRAPI
```

### 3. Tester les pages

1. **Page FR:** http://localhost:3011/fr
   - Doit afficher le titre depuis Strapi (`global.branding.name`)
   - Doit afficher le tagline depuis Strapi (`global.branding.tagline`)
   - Si page "home" existe: doit afficher `page.title`

2. **Page EN:** http://localhost:3011/en
   - Même vérifications en anglais

3. **Page racine:** http://localhost:3011
   - Doit rediriger vers /fr

### 4. Tester la gestion d'erreur (Strapi down)

1. Arrêter Strapi (Ctrl+C)
2. Rafraîchir http://localhost:3011/fr
3. **Résultat attendu:** Page s'affiche avec fallbacks:
   - Titre: "Arquantix" (fallback)
   - Tagline: "Bientôt disponible" (fallback)
   - Pas d'erreur 500

---

## Checklist de Validation

- [ ] Strapi accessible sur http://localhost:1337/admin
- [ ] Content Type "page" créé avec i18n (fr, en)
- [ ] Content Type "global" créé (singleton)
- [ ] Page "home" créée en FR (slug=home, publiée)
- [ ] Page "home" créée en EN (slug=home, publiée)
- [ ] Global créé et publié
- [ ] Permissions PUBLIC configurées (find pour global, find/findOne pour page)
- [ ] API Strapi répond: `/api/global` et `/api/pages?filters[slug][$eq]=home&filters[locale][$eq]=fr`
- [ ] Next.js accessible sur http://localhost:3011
- [ ] Page /fr affiche le contenu depuis Strapi
- [ ] Page /en affiche le contenu depuis Strapi
- [ ] Si Strapi down, page s'affiche avec fallbacks (pas d'erreur 500)

---

## Problèmes Courants

### Strapi API retourne 403

**Cause:** Permissions PUBLIC non configurées.

**Solution:** Settings → Users & Permissions Plugin → Roles → Public → Activer `find` pour global et page.

### Next.js ne charge pas les données

**Cause:** URL Strapi incorrecte ou Strapi non accessible.

**Vérifier:**
```bash
# Depuis le container Next.js
docker compose -f docker-compose.arquantix.yml exec arquantix-web wget -O- http://host.docker.internal:1337/api/global
```

**Solution:** Vérifier `NEXT_PUBLIC_STRAPI_API_URL` dans docker-compose.

### Erreur "API fetch error"

**Cause:** Strapi down ou timeout.

**Comportement attendu:** Page s'affiche avec fallbacks (gestion d'erreur dans `getHomePageData`).

---

**Dernière mise à jour:** 2026-01-01

