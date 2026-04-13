# API - Arquantix CMS (Strapi)

**Date:** 2026-01-01  
**Status:** 🚧 En cours de développement

---

## TL;DR

Documentation des endpoints Strapi utilisés par le site vitrine Next.js.

---

## Ce qui est vrai aujourd'hui

### Base URL

- **Développement local:** `http://localhost:1338/api` ou `http://arquantix-cms:1338/api` (depuis Docker)
- **Production:** `https://cms.arquantix.com/api` (si Strapi déployé en prod)

### Format de Réponse

Tous les endpoints retournent des réponses au format Strapi:

```json
{
  "data": {
    "id": 1,
    "attributes": {
      // ... champs du Content Type
    }
  },
  "meta": {
    "pagination": {
      // ... si collection
    }
  }
}
```

Pour les collections:

```json
{
  "data": [
    {
      "id": 1,
      "attributes": { /* ... */ }
    },
    {
      "id": 2,
      "attributes": { /* ... */ }
    }
  ],
  "meta": {
    "pagination": {
      "page": 1,
      "pageSize": 25,
      "pageCount": 1,
      "total": 2
    }
  }
}
```

---

## Endpoints

### 1. Global (Singleton)

**Endpoint:** `GET /api/global`

**Description:** Récupère les données globales (branding, socials, SEO)

**Paramètres de Query:**
- `populate=*` (optionnel): Inclure les relations

**Exemple de requête:**
```typescript
const response = await strapi.get('/global', {
  populate: '*'
})
```

**Exemple de réponse:**
```json
{
  "data": {
    "id": 1,
    "attributes": {
      "branding": {
        "logo": "/uploads/logo.png",
        "name": "Arquantix"
      },
      "socials": {
        "twitter": "https://twitter.com/arquantix",
        "linkedin": "https://linkedin.com/company/arquantix"
      },
      "seo": {
        "defaultTitle": "Arquantix",
        "defaultDescription": "Arquantix description"
      }
    }
  }
}
```

---

### 2. Pages (Collection)

**Endpoint:** `GET /api/pages`

**Description:** Récupère les pages (avec filtres)

**Paramètres de Query:**
- `filters[slug][$eq]=home` (requis): Filtrer par slug
- `filters[locale][$eq]=fr` (requis): Filtrer par locale (fr, en)
- `populate=*` (optionnel): Inclure les relations (sections, images, etc.)

**Exemple de requête:**
```typescript
const response = await strapi.get('/pages', {
  'filters[slug][$eq]': 'home',
  'filters[locale][$eq]': 'fr',
  populate: '*'
})
```

**Endpoint:** `GET /api/pages/:id`

**Description:** Récupère une page par ID

**Paramètres de Query:**
- `populate=*` (optionnel): Inclure les relations

---

### 3. News (Collection)

**Endpoint:** `GET /api/news`

**Description:** Récupère les articles de news (liste)

**Paramètres de Query:**
- `filters[locale][$eq]=fr` (requis): Filtrer par locale (fr, en)
- `pagination[limit]=10` (optionnel): Nombre d'articles (défaut: 25)
- `pagination[page]=1` (optionnel): Page (défaut: 1)
- `sort=publishedAt:desc` (optionnel): Tri (défaut: createdAt:desc)
- `populate=*` (optionnel): Inclure les relations (coverImage, etc.)

**Exemple de requête:**
```typescript
const response = await strapi.get('/news', {
  'filters[locale][$eq]': 'fr',
  'pagination[limit]': 10,
  sort: 'publishedAt:desc',
  populate: '*'
})
```

**Endpoint:** `GET /api/news/:id`

**Description:** Récupère un article par ID

**Paramètres de Query:**
- `populate=*` (optionnel): Inclure les relations

**Endpoint:** `GET /api/news?filters[slug][$eq]=article-slug`

**Description:** Récupère un article par slug

**Paramètres de Query:**
- `filters[slug][$eq]=article-slug` (requis): Slug de l'article
- `filters[locale][$eq]=fr` (requis): Locale
- `populate=*` (optionnel): Inclure les relations

---

### 4. Contact Submissions (Collection)

**Endpoint:** `POST /api/contact-submissions`

**Description:** Crée une nouvelle soumission de contact

**Body:**
```json
{
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "message": "Hello, I'm interested in..."
  }
}
```

**Exemple de requête:**
```typescript
const response = await strapi.post('/contact-submissions', {
  name: 'John Doe',
  email: 'john@example.com',
  message: 'Hello!'
})
```

**Permissions:**
- Public: `create` uniquement
- Admin: `find`, `findOne`, `create`, `update`, `delete`

---

## Utilisation dans Next.js

Le client Strapi est défini dans `services/arquantix/web/lib/strapi.ts`.

**Exemple d'utilisation:**

```typescript
import { strapi } from '@/lib/strapi'

// Récupérer la page d'accueil
const homePage = await strapi.get('/pages', {
  'filters[slug][$eq]': 'home',
  'filters[locale][$eq]': 'fr',
  populate: '*'
})

// Récupérer les news
const news = await strapi.get('/news', {
  'filters[locale][$eq]': 'fr',
  'pagination[limit]': 10,
  sort: 'publishedAt:desc',
  populate: '*'
})

// Soumettre un formulaire de contact
await strapi.post('/contact-submissions', {
  name: 'John Doe',
  email: 'john@example.com',
  message: 'Hello!'
})
```

---

## Permissions

Les permissions sont configurées dans Strapi Admin:
- Settings → Users & Permissions Plugin → Roles → Public

**Permissions recommandées pour Public:**

| Content Type        | Permissions                    |
|---------------------|--------------------------------|
| `global`            | `find`                         |
| `page`              | `find`, `findOne`              |
| `news`              | `find`, `findOne`              |
| `contactSubmission` | `create` uniquement            |

---

## À vérifier quand ça casse

### Erreur 403 (Forbidden)

1. Vérifier les permissions dans Strapi Admin:
   - Settings → Users & Permissions Plugin → Roles → Public
   - Activer les permissions nécessaires

2. Vérifier que l'endpoint existe:
   - Aller dans Strapi Admin: Content-Type Builder
   - Vérifier que le Content Type existe et est publié

### Erreur 404 (Not Found)

1. Vérifier que le Content Type existe:
   - Aller dans Strapi Admin: Content-Type Builder
   - Vérifier le nom de l'endpoint (pluriel: `/api/pages`, pas `/api/page`)

2. Vérifier que le contenu existe:
   - Aller dans Strapi Admin: Content Manager
   - Vérifier qu'il y a du contenu créé

### Erreur de connexion

1. Vérifier que Strapi est démarré:
   ```bash
   docker compose -f docker-compose.arquantix.yml ps arquantix-cms
   ```

2. Vérifier les variables d'environnement:
   - `NEXT_PUBLIC_STRAPI_URL`
   - `NEXT_PUBLIC_STRAPI_API_URL`

3. Tester la connexion:
   ```bash
   curl http://localhost:1338/api
   ```

---

**Dernière mise à jour:** 2026-01-01

