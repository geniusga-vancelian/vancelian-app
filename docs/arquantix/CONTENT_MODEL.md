# Content Model - Arquantix CMS (Strapi)

**Date:** 2026-01-01  
**Status:** 🚧 En cours de développement

---

## TL;DR

Modèle de contenu Strapi pour Arquantix: Content Types, champs, exemples JSON.

---

## Ce qui est vrai aujourd'hui

### Content Types Requis

1. **global** (singleton)
2. **page** (collection)
3. **news** (collection)
4. **contactSubmission** (collection)

---

## 1. Global (Singleton)

**Type:** Singleton  
**Localisation:** Non (pas de i18n)  
**Description:** Données globales (branding, socials, SEO)

### Champs

| Nom          | Type      | Requis | Description              |
|--------------|-----------|--------|--------------------------|
| `branding`   | JSON      | Oui    | Informations de branding |
| `socials`    | JSON      | Non    | Réseaux sociaux          |
| `seo`        | JSON      | Non    | SEO par défaut           |

### Structure JSON

**branding:**
```json
{
  "logo": "/uploads/logo.png",
  "name": "Arquantix",
  "tagline": "Votre tagline ici"
}
```

**socials:**
```json
{
  "twitter": "https://twitter.com/arquantix",
  "linkedin": "https://linkedin.com/company/arquantix",
  "github": "https://github.com/arquantix"
}
```

**seo:**
```json
{
  "defaultTitle": "Arquantix",
  "defaultDescription": "Description par défaut pour le SEO",
  "defaultImage": "/uploads/og-image.png"
}
```

### Exemple Complet

```json
{
  "data": {
    "id": 1,
    "attributes": {
      "branding": {
        "logo": "/uploads/logo.png",
        "name": "Arquantix",
        "tagline": "Innovation Technology"
      },
      "socials": {
        "twitter": "https://twitter.com/arquantix",
        "linkedin": "https://linkedin.com/company/arquantix"
      },
      "seo": {
        "defaultTitle": "Arquantix",
        "defaultDescription": "Arquantix - Innovation Technology"
      }
    }
  }
}
```

---

## 2. Page (Collection)

**Type:** Collection  
**Localisation:** Oui (fr, en)  
**Description:** Pages du site (home, about, etc.)

### Champs

| Nom          | Type          | Requis | Unique | Description                    |
|--------------|---------------|--------|--------|--------------------------------|
| `slug`       | UID           | Oui    | Oui    | Slug de la page (ex: home)     |
| `title`      | Text          | Oui    | Non    | Titre de la page               |
| `sections`   | Dynamic Zone  | Non    | Non    | Sections dynamiques            |
| `seo`        | JSON          | Non    | Non    | SEO spécifique à la page       |
| `locale`     | Enum (i18n)   | Oui    | Non    | Locale (fr, en)                |

### Sections (Dynamic Zone)

Les sections peuvent être de différents types:

- **Hero Section** (component `sections.hero`)
  - `title` (Text)
  - `subtitle` (Text)
  - `image` (Media)
  - `ctaText` (Text)
  - `ctaLink` (Text)

- **Text Section** (component `sections.text`)
  - `title` (Text)
  - `content` (RichText)
  - `image` (Media, optionnel)

- **Features Section** (component `sections.features`)
  - `title` (Text)
  - `features` (Repeatable component)
    - `title` (Text)
    - `description` (Text)
    - `icon` (Media, optionnel)

### Exemple Complet

```json
{
  "data": {
    "id": 1,
    "attributes": {
      "slug": "home",
      "title": "Accueil",
      "locale": "fr",
      "sections": [
        {
          "__component": "sections.hero",
          "title": "Bienvenue sur Arquantix",
          "subtitle": "Innovation Technology",
          "image": {
            "data": {
              "id": 1,
              "attributes": {
                "url": "/uploads/hero.jpg"
              }
            }
          },
          "ctaText": "En savoir plus",
          "ctaLink": "/fr/about"
        },
        {
          "__component": "sections.text",
          "title": "À propos",
          "content": "<p>Contenu de la section...</p>"
        }
      ],
      "seo": {
        "title": "Arquantix - Accueil",
        "description": "Page d'accueil Arquantix"
      }
    }
  }
}
```

---

## 3. News (Collection)

**Type:** Collection  
**Localisation:** Oui (fr, en)  
**Description:** Articles de news/actualités

### Champs

| Nom           | Type          | Requis | Unique | Description                      |
|---------------|---------------|--------|--------|----------------------------------|
| `title`       | Text          | Oui    | Non    | Titre de l'article               |
| `slug`        | UID           | Oui    | Oui    | Slug de l'article                |
| `excerpt`     | Text          | Non    | Non    | Résumé/extrait                   |
| `content`     | RichText      | Oui    | Non    | Contenu de l'article             |
| `coverImage`  | Media         | Non    | Non    | Image de couverture              |
| `publishedAt` | DateTime      | Non    | Non    | Date de publication              |
| `locale`      | Enum (i18n)   | Oui    | Non    | Locale (fr, en)                  |

### Exemple Complet

```json
{
  "data": {
    "id": 1,
    "attributes": {
      "title": "Nouvelle fonctionnalité disponible",
      "slug": "nouvelle-fonctionnalite-disponible",
      "excerpt": "Nous sommes ravis d'annoncer une nouvelle fonctionnalité...",
      "content": "<p>Contenu complet de l'article...</p>",
      "coverImage": {
        "data": {
          "id": 1,
          "attributes": {
            "url": "/uploads/news-cover.jpg",
            "alternativeText": "Cover image"
          }
        }
      },
      "publishedAt": "2026-01-01T00:00:00.000Z",
      "locale": "fr"
    }
  }
}
```

---

## 4. ContactSubmission (Collection)

**Type:** Collection  
**Localisation:** Non (pas de i18n)  
**Description:** Soumissions du formulaire de contact

### Champs

| Nom          | Type     | Requis | Unique | Description                    |
|--------------|----------|--------|--------|--------------------------------|
| `name`       | Text     | Oui    | Non    | Nom du contact                 |
| `email`      | Email    | Oui    | Non    | Email du contact               |
| `message`    | Text     | Oui    | Non    | Message                        |
| `createdAt`  | DateTime | Auto   | Non    | Date de création (auto)        |

### Exemple Complet

```json
{
  "data": {
    "id": 1,
    "attributes": {
      "name": "John Doe",
      "email": "john@example.com",
      "message": "Bonjour, je suis intéressé par...",
      "createdAt": "2026-01-01T12:00:00.000Z"
    }
  }
}
```

### Permissions

- **Public:** `create` uniquement
- **Admin:** `find`, `findOne`, `create`, `update`, `delete`

---

## Création des Content Types

### Via Strapi Admin UI

1. Démarrer Strapi: `npm run develop` (ou via Docker)
2. Accéder à http://localhost:1338/admin
3. Créer un compte admin (si premier démarrage)
4. Aller dans "Content-Type Builder"
5. Créer chaque Content Type selon les spécifications ci-dessus

### Ordre Recommandé

1. **global** (singleton)
2. **page** (collection, avec i18n activé)
3. **news** (collection, avec i18n activé)
4. **contactSubmission** (collection, sans i18n)

### Activation i18n

Pour activer i18n sur un Content Type:
1. Créer le Content Type
2. Cliquer sur "Configure the view"
3. Activer "Localization"
4. Sélectionner les locales (fr, en)

---

## Permissions

Configurer les permissions dans:
- Settings → Users & Permissions Plugin → Roles → Public

**Permissions recommandées:**

| Content Type        | Permissions                    |
|---------------------|--------------------------------|
| `global`            | `find`                         |
| `page`              | `find`, `findOne`              |
| `news`              | `find`, `findOne`              |
| `contactSubmission` | `create` uniquement            |

---

## À vérifier quand ça casse

### Content Type n'apparaît pas dans l'API

1. Vérifier que le Content Type est créé dans Content-Type Builder
2. Vérifier que le Content Type est publié (pas en brouillon)
3. Vérifier les permissions dans Settings → Users & Permissions Plugin

### Erreur de validation

1. Vérifier que les champs requis sont remplis
2. Vérifier les types de champs (Text vs RichText, etc.)
3. Vérifier les contraintes (unique, required)

### i18n ne fonctionne pas

1. Vérifier que i18n est activé sur le Content Type
2. Vérifier que les locales (fr, en) sont sélectionnées
3. Vérifier que le contenu est créé pour chaque locale

---

**Dernière mise à jour:** 2026-01-01

