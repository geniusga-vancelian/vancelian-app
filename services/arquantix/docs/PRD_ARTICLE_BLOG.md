# PRD — Feature Article & Blog

**Version :** 1.0  
**Date :** 2026-02-18  
**Statut :** Spécification complète pour implémentation from scratch

---

## 1. Vue d'ensemble

### 1.1 Objectif

Permettre la création, l'édition, la publication et l'affichage d'articles de blog multilingues avec contenu structuré (blocs), catégories, médias et liaison aux projets.

### 1.2 Périmètre fonctionnel

| Fonctionnalité | Priorité | Description |
|----------------|----------|--------------|
| CRUD Articles | P0 | Création, lecture, mise à jour, suppression |
| Blocs de contenu | P0 | HEADING, PARAGRAPH, QUOTE, BULLET_LIST, IMAGE, VIDEO, DOCUMENT |
| i18n complet | P0 | ArticleI18n + ArticleBlockI18n par locale |
| Catégories | P0 | ArticleCategory avec i18n, liaison many-to-many |
| Feed paginé | P0 | Liste avec featured, highlighted, pagination |
| Médias | P0 | Cover, galerie, images dans blocs, documents PDF |
| Liaison Projets | P1 | Article ↔ Project (many-to-many) |
| Traduction IA | P1 | Traduction automatique Article + blocs |
| SEO | P0 | metaTitle, metaDescription, Schema.org |
| Temps de lecture | P1 | Calcul à partir des blocs texte |

### 1.3 Locales supportées

- `fr` (défaut)
- `en`
- `it`

---

## 2. Modèle de données

### 2.1 Schéma SQL (PostgreSQL)

```sql
-- Enum pour le type de bloc
CREATE TYPE "ArticleBlockType" AS ENUM (
  'HEADING',
  'PARAGRAPH',
  'QUOTE',
  'BULLET_LIST',
  'IMAGE',
  'VIDEO',
  'DOCUMENT'
);

-- Enum pour le statut
CREATE TYPE "ContentStatus" AS ENUM ('DRAFT', 'PUBLISHED');

-- Enum pour le statut de traduction
CREATE TYPE "TranslationStatus" AS ENUM ('ORIGINAL', 'MACHINE', 'APPROVED');

-- =============================================================================
-- ArticleCategory
-- =============================================================================
CREATE TABLE article_categories (
  id              TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  slug            TEXT NOT NULL UNIQUE,
  label           TEXT NOT NULL,  -- Legacy, utiliser i18n
  "order"         INT NOT NULL DEFAULT 0,
  is_active       BOOLEAN NOT NULL DEFAULT true,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_article_categories_slug ON article_categories(slug);
CREATE INDEX ix_article_categories_active_order ON article_categories(is_active, "order");

-- =============================================================================
-- ArticleCategoryI18n
-- =============================================================================
CREATE TABLE article_category_i18n (
  id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  category_id         TEXT NOT NULL REFERENCES article_categories(id) ON DELETE CASCADE,
  locale              TEXT NOT NULL,
  label               TEXT NOT NULL,
  translation_status  "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(category_id, locale)
);

CREATE INDEX ix_article_category_i18n_category ON article_category_i18n(category_id);
CREATE INDEX ix_article_category_i18n_locale ON article_category_i18n(locale);

-- =============================================================================
-- Article (table principale)
-- =============================================================================
CREATE TABLE articles (
  id                TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  slug              TEXT NOT NULL UNIQUE,
  status            "ContentStatus" NOT NULL DEFAULT 'DRAFT',
  published_at      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  cover_media_id    TEXT REFERENCES media(id) ON DELETE RESTRICT,
  gallery_media_ids  JSONB,  -- ["mediaId1", "mediaId2"] (sans cover)
  video_url         TEXT,    -- YouTube/Vimeo embed URL
  category_slugs    JSONB,   -- ["slug1", "slug2"]
  documents         JSONB,   -- [{"mediaId": "x", "title": "PDF"}]
  is_featured       BOOLEAN NOT NULL DEFAULT false,
  is_highlighted    BOOLEAN NOT NULL DEFAULT false,
  author_name       TEXT NOT NULL,
  author_role       TEXT,
  allow_comments    BOOLEAN NOT NULL DEFAULT false,
  cover_title       TEXT,
  cover_credit      TEXT,
  cover_source      TEXT
);

CREATE INDEX ix_articles_status ON articles(status);
CREATE INDEX ix_articles_published_at ON articles(published_at);
CREATE INDEX ix_articles_category_slugs ON articles USING GIN (category_slugs);  -- Pour filtrage @>

-- =============================================================================
-- ArticleI18n
-- =============================================================================
CREATE TABLE article_i18n (
  id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  article_id          TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  locale              TEXT NOT NULL,
  title               TEXT NOT NULL,
  standfirst          TEXT NOT NULL,
  meta_title          TEXT,
  meta_description    TEXT,
  cover_title         TEXT,
  translation_status  "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(article_id, locale)
);

CREATE INDEX ix_article_i18n_article ON article_i18n(article_id);

-- =============================================================================
-- ArticleBlock (structure canonique, pas de locale)
-- =============================================================================
CREATE TABLE article_blocks (
  id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  article_id   TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  "order"      INT NOT NULL DEFAULT 0,
  type         "ArticleBlockType" NOT NULL,
  data         JSONB NOT NULL,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(article_id, "order")
);

CREATE INDEX ix_article_blocks_article ON article_blocks(article_id);

-- =============================================================================
-- ArticleBlockI18n (contenu localisé par bloc)
-- =============================================================================
CREATE TABLE article_block_i18n (
  id                  TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  block_id            TEXT NOT NULL REFERENCES article_blocks(id) ON DELETE CASCADE,
  locale              TEXT NOT NULL,
  data                JSONB NOT NULL,
  translation_status  "TranslationStatus" NOT NULL DEFAULT 'ORIGINAL',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(block_id, locale)
);

CREATE INDEX ix_article_block_i18n_block ON article_block_i18n(block_id);
CREATE INDEX ix_article_block_i18n_locale ON article_block_i18n(locale);

-- =============================================================================
-- ArticleProject (liaison Article ↔ Project)
-- =============================================================================
CREATE TABLE article_projects (
  id          TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
  article_id  TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(article_id, project_id)
);

CREATE INDEX ix_article_projects_article ON article_projects(article_id);
CREATE INDEX ix_article_projects_project ON article_projects(project_id);

-- =============================================================================
-- Media (prérequis)
-- =============================================================================
-- Table media doit exister avec: id, key, url, filename, mime_type, size, width, height, alt
```

### 2.2 Structure des blocs (champ `data`)

| Type | Structure JSON | Exemple |
|------|----------------|---------|
| HEADING | `{ "text": string }` | `{"text": "Introduction"}` |
| PARAGRAPH | `{ "text": string }` | `{"text": "Contenu **markdown**..."}` |
| QUOTE | `{ "text": string, "author"?: string }` | `{"text": "Citation", "author": "Auteur"}` |
| BULLET_LIST | `{ "items": string[] }` | `{"items": ["Item 1", "Item 2"]}` |
| IMAGE | `{ "mediaId": string, "caption"?: string }` | `{"mediaId": "cuid123", "caption": "Légende"}` |
| VIDEO | `{ "url": string, "caption"?: string }` | `{"url": "https://youtube.com/watch?v=xxx", "caption": "..."}` |
| DOCUMENT | `{ "mediaId": string, "title": string }` | `{"mediaId": "cuid456", "title": "Rapport PDF"}` |

**Règles :**
- `text` : supporte Markdown (liens, gras, italique, etc.)
- `url` (VIDEO) : YouTube ou Vimeo uniquement
- `mediaId` : référence vers la table `media`

### 2.3 Contraintes métier

| Contrainte | Règle |
|------------|-------|
| Slug | Lowercase, alphanumeric + tirets uniquement, unique |
| Locale | Doit être dans la liste supportée (fr, en, it) |
| Article publié | `status = PUBLISHED` ET `published_at` non null |
| i18n requis | Au moins une entrée ArticleI18n par article (locale par défaut) |
| Blocs | `order` unique par article, ordre séquentiel (0, 1, 2...) |

---

## 3. API

### 3.1 Endpoints publics

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/blog` | Feed paginé avec featured, highlighted, articles, categories |
| GET | `/blog/[slug]` | Page article (SSR, Next.js) |

#### GET /api/blog — Paramètres

| Param | Type | Défaut | Description |
|-------|------|--------|-------------|
| locale | string | fr | Locale pour i18n |
| category | string | - | Filtre par slug de catégorie |
| page | number | 1 | Numéro de page |
| pageSize | number | 10 | Articles par page (max 50) |

#### GET /api/blog — Réponse

```json
{
  "featured": {
    "id": "string",
    "slug": "string",
    "title": "string",
    "standfirst": "string",
    "coverUrl": "string",
    "authorName": "string",
    "authorRole": "string | null",
    "publishedAt": "string | null",
    "readingTime": number,
    "categorySlugs": ["string"]
  } | null,
  "highlighted": [...],
  "articles": [...],
  "categories": [
    { "id": "string", "slug": "string", "label": "string" }
  ],
  "pagination": {
    "page": number,
    "pageSize": number,
    "total": number,
    "hasMore": boolean
  }
}
```

### 3.2 Endpoints admin (authentifiés)

| Méthode | Route | Description |
|---------|-------|-------------|
| GET | `/api/admin/articles` | Liste articles (filtres: status, locale, search) |
| POST | `/api/admin/articles` | Créer article |
| GET | `/api/admin/articles/[id]` | Détail article |
| PUT | `/api/admin/articles/[id]` | Mettre à jour article |
| DELETE | `/api/admin/articles/[id]` | Supprimer article |
| POST | `/api/admin/articles/[id]/publish` | Publier |
| POST | `/api/admin/articles/[id]/unpublish` | Dépublier |
| GET | `/api/admin/articles/[id]/blocks` | Liste blocs |
| POST | `/api/admin/articles/[id]/blocks` | Créer bloc |
| GET | `/api/admin/articles/[id]/blocks/[blockId]` | Détail bloc |
| PUT | `/api/admin/articles/[id]/blocks/[blockId]` | Mettre à jour bloc |
| DELETE | `/api/admin/articles/[id]/blocks/[blockId]` | Supprimer bloc |
| POST | `/api/admin/articles/[id]/blocks/reorder` | Réordonner blocs |
| GET | `/api/admin/articles/[id]/i18n` | Liste i18n |
| PUT | `/api/admin/articles/[id]/i18n` | Créer/MAJ i18n pour locale |
| GET | `/api/admin/articles/[id]/projects` | Projets liés |
| POST | `/api/admin/articles/[id]/projects` | Lier projet |
| DELETE | `/api/admin/articles/[id]/projects/[projectId]` | Délier projet |
| POST | `/api/admin/translate/article` | Traduction IA (source → target locale) |
| GET | `/api/admin/article-categories` | Liste catégories |
| POST | `/api/admin/article-categories` | Créer catégorie |
| ... | ... | CRUD catégories |

### 3.3 Schémas de validation (Zod)

```typescript
// Création article
const createArticleSchema = z.object({
  slug: z.string().min(1).max(60).refine(isValidSlug),
  coverMediaId: z.string().optional(),
  authorName: z.string().min(1),
  authorRole: z.string().optional().nullable(),
  allowComments: z.boolean().default(false),
})

// Création bloc
const createBlockSchema = z.object({
  type: z.nativeEnum(ArticleBlockType),
  data: z.any(),
  locale: z.string().optional(),  // Pour ArticleBlockI18n initial
})

// Mise à jour article
const updateArticleSchema = z.object({
  slug: z.string().optional(),
  status: z.enum(['DRAFT', 'PUBLISHED']).optional(),
  coverMediaId: z.string().optional().nullable(),
  galleryMediaIds: z.array(z.string()).optional().nullable(),
  videoUrl: z.string().optional().nullable(),
  categorySlugs: z.array(z.string()).optional().nullable(),
  documents: z.array(z.object({ mediaId: z.string(), title: z.string() })).optional().nullable(),
  isFeatured: z.boolean().optional(),
  isHighlighted: z.boolean().optional(),
  authorName: z.string().optional(),
  authorRole: z.string().optional().nullable(),
  coverTitle: z.string().optional().nullable(),
  coverCredit: z.string().optional().nullable(),
  coverSource: z.string().optional().nullable(),
})
```

---

## 4. Logique métier

### 4.1 Feed blog

1. **Featured** : Premier article avec `isFeatured = true` ; sinon le plus récent publié.
2. **Highlighted** : Jusqu'à 5 articles avec `isHighlighted = true`, excluant le featured.
3. **Feed** : Articles publiés, hors featured et highlighted, triés par `published_at DESC`, paginés.
4. **Filtre catégorie** : `category_slugs @> '["slug"]'::jsonb` (PostgreSQL).
5. **Pagination** : `skip = (page - 1) * pageSize`, `take = pageSize`, `count` pour total.

### 4.2 Récupération article par slug

1. Charger Article avec `slug`, `coverMedia`, `i18n` (locale), `blocks` (orderBy order).
2. Pour chaque bloc : `data = block.i18n[0]?.data ?? block.data` (fallback).
3. Résoudre les `mediaId` des blocs IMAGE/DOCUMENT → presigned URLs.
4. Charger catégories via `categorySlugs` (ArticleCategory où slug IN categorySlugs).
5. Charger ArticleProject avec Project + ProjectI18n.

### 4.3 Temps de lecture

- 220 mots/minute.
- Comptage : HEADING.text, PARAGRAPH.text (sans markdown), QUOTE.text, BULLET_LIST.items.
- IMAGE, VIDEO, DOCUMENT : 0 mot.
- Résultat : `Math.max(1, Math.ceil(totalWords / 220))` minutes.

### 4.4 Presigned URLs

- Médias stockés sur S3/R2 avec `key`.
- Pour affichage public : générer URL signée (expiration 1h) via SDK.
- Fallback : URL publique si `key` absent.

---

## 5. Pages & Routes frontend

### 5.1 Routes

| Route | Type | Description |
|-------|------|-------------|
| `/blog` | Page | Liste des articles (feed) |
| `/blog/[slug]` | Page | Détail d'un article |

### 5.2 Intégration CMS

- La page `/blog` peut être rendue via une page CMS (slug `blog`, template `blog`) avec sections : `blog_hero`, `blog_category_nav`, `blog_mosaic`, `blog_feed`.
- Si pas de page CMS : rendu par défaut avec Navigation + feed.

### 5.3 Composants requis

| Composant | Rôle |
|-----------|------|
| SectionBlogHero | En-tête avec article featured |
| SectionBlogCategoryNav | Pills de catégories |
| SectionBlogMosaic | Grille d'articles highlighted |
| SectionBlogFeed | Liste paginée avec "Load more" |
| ReadingProgress | Barre de progression lecture |
| TableOfContents | Sommaire (headings H2+) |
| ArticleCarousel | Carousel images (cover + galerie) |

---

## 6. Traduction IA

### 6.1 Entités à traduire

- **ArticleI18n** : title, standfirst, metaTitle, metaDescription, coverTitle.
- **ArticleBlockI18n** : data selon le type :
  - HEADING, PARAGRAPH, QUOTE : `text`
  - BULLET_LIST : `items[]`
  - IMAGE, VIDEO : `caption` uniquement (mediaId/url inchangés)
  - DOCUMENT : `title` uniquement

### 6.2 Flux

1. Source locale (ex: fr) → Target locale (ex: en).
2. Créer ArticleI18n pour target si absent.
3. Pour chaque bloc : créer ArticleBlockI18n pour target avec `translationStatus = MACHINE`.
4. Conserver les références (mediaId, url) inchangées.

---

## 7. SEO & Métadonnées

### 7.1 Metadata (Next.js)

```typescript
{
  title: article.i18n.metaTitle || article.i18n.title,
  description: article.i18n.metaDescription || article.i18n.standfirst,
  openGraph: {
    title, description,
    images: [{ url: coverUrl }],
    type: 'article',
    publishedTime: article.publishedAt?.toISOString(),
    authors: [article.authorName],
  },
  twitter: { card: 'summary_large_image', title, description, images: [coverUrl] },
}
```

### 7.2 Schema.org

```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "...",
  "description": "...",
  "image": "...",
  "datePublished": "...",
  "dateModified": "...",
  "author": { "@type": "Person", "name": "..." },
  "publisher": { "@type": "Organization", "name": "Arquantix" }
}
```

---

## 8. Dépendances

### 8.1 Tables prérequises

- `media` : id, key, url, filename, mimeType, size, width?, height?, alt?
- `projects` : pour ArticleProject
- `users` : pour auth admin

### 8.2 Services externes

- Stockage objet (S3/R2) pour médias.
- Presigned URL (SDK AWS/Cloudflare).
- Optionnel : OpenAI pour traduction IA.

---

## 9. Checklist d'implémentation

### Phase 1 — Base de données
- [ ] Créer enum ArticleBlockType, ContentStatus, TranslationStatus
- [ ] Créer table article_categories + article_category_i18n
- [ ] Créer table articles
- [ ] Créer table article_i18n
- [ ] Créer table article_blocks
- [ ] Créer table article_block_i18n
- [ ] Créer table article_projects
- [ ] Index GIN sur category_slugs

### Phase 2 — API
- [ ] GET /api/blog (feed)
- [ ] Service getBlogFeed (pagination, featured, highlighted, categories)
- [ ] Fonction getArticle(slug, locale)
- [ ] CRUD admin articles
- [ ] CRUD admin blocks
- [ ] CRUD admin i18n
- [ ] Gestion ArticleProject

### Phase 3 — Frontend
- [ ] Page /blog
- [ ] Page /blog/[slug]
- [ ] Composants SectionBlog*
- [ ] Admin /admin/articles
- [ ] Admin /admin/articles/[id] (éditeur blocs)

### Phase 4 — Avancé
- [ ] Traduction IA
- [ ] Presigned URLs pour médias
- [ ] Temps de lecture
- [ ] Schema.org, metadata SEO

---

## 10. Annexes

### A. Prisma Schema (référence)

Voir `web/prisma/schema.prisma` lignes 173-282 pour le schéma Prisma actuel.

### B. Format slug

- Regex : `^[a-z0-9]+(?:-[a-z0-9]+)*$`
- Exemples valides : `mon-article`, `news-2026`

### C. Ordre des blocs

- `order` : 0, 1, 2, ... (séquentiel)
- Réordonnancement : recalculer tous les `order` après déplacement.

---

## 11. Schéma Prisma complet (copie pour recréation)

```prisma
enum ArticleBlockType {
  HEADING
  PARAGRAPH
  QUOTE
  BULLET_LIST
  IMAGE
  VIDEO
  DOCUMENT
}

enum ContentStatus {
  DRAFT
  PUBLISHED
}

enum TranslationStatus {
  ORIGINAL
  MACHINE
  APPROVED
}

model ArticleCategory {
  id        String                @id @default(cuid())
  slug      String                @unique
  label     String
  order     Int                   @default(0)
  isActive  Boolean               @default(true) @map("is_active")
  createdAt DateTime              @default(now()) @map("created_at")
  updatedAt DateTime              @updatedAt @map("updated_at")
  i18n      ArticleCategoryI18n[]

  @@index([slug])
  @@index([isActive, order])
  @@map("article_categories")
}

model ArticleCategoryI18n {
  id                String            @id @default(cuid())
  categoryId        String            @map("category_id")
  locale            String
  label             String
  translationStatus TranslationStatus @default(ORIGINAL) @map("translation_status")
  createdAt         DateTime          @default(now()) @map("created_at")
  updatedAt         DateTime          @updatedAt @map("updated_at")
  category          ArticleCategory   @relation(fields: [categoryId], references: [id], onDelete: Cascade)

  @@unique([categoryId, locale])
  @@index([categoryId])
  @@index([locale])
  @@map("article_category_i18n")
}

model Article {
  id              String           @id @default(cuid())
  slug            String           @unique
  status          ContentStatus    @default(DRAFT)
  publishedAt     DateTime?        @map("published_at")
  updatedAt       DateTime         @updatedAt @map("updated_at")
  createdAt       DateTime         @default(now()) @map("created_at")
  coverMediaId    String?          @map("cover_media_id")
  galleryMediaIds Json?            @map("gallery_media_ids")
  videoUrl        String?          @map("video_url")
  categorySlugs   Json?            @map("category_slugs")
  documents       Json?
  isFeatured      Boolean          @default(false) @map("is_featured")
  isHighlighted   Boolean          @default(false) @map("is_highlighted")
  authorName      String           @map("author_name")
  authorRole      String?          @map("author_role")
  allowComments   Boolean          @default(false) @map("allow_comments")
  coverTitle      String?          @map("cover_title")
  coverCredit     String?          @map("cover_credit")
  coverSource     String?          @map("cover_source")
  blocks          ArticleBlock[]
  i18n            ArticleI18n[]
  projects        ArticleProject[]
  coverMedia      Media?           @relation("ArticleCoverMedia", fields: [coverMediaId], references: [id], onDelete: Restrict)

  @@index([status])
  @@index([publishedAt])
  @@map("articles")
}

model ArticleI18n {
  id                String            @id @default(cuid())
  articleId         String            @map("article_id")
  locale            String
  title             String
  standfirst        String
  metaTitle         String?           @map("meta_title")
  metaDescription   String?           @map("meta_description")
  coverTitle        String?          @map("cover_title")
  translationStatus TranslationStatus @default(ORIGINAL) @map("translation_status")
  updatedAt         DateTime          @updatedAt @map("updated_at")
  createdAt         DateTime          @default(now()) @map("created_at")
  article           Article           @relation(fields: [articleId], references: [id], onDelete: Cascade)

  @@unique([articleId, locale])
  @@index([articleId])
  @@map("article_i18n")
}

model ArticleBlock {
  id        String             @id @default(cuid())
  articleId String             @map("article_id")
  order     Int                @default(0)
  type      ArticleBlockType
  data      Json
  createdAt DateTime           @default(now()) @map("created_at")
  i18n      ArticleBlockI18n[]
  article   Article            @relation(fields: [articleId], references: [id], onDelete: Cascade)

  @@unique([articleId, order])
  @@index([articleId])
  @@map("article_blocks")
}

model ArticleBlockI18n {
  id                String            @id @default(cuid())
  blockId           String            @map("block_id")
  locale            String
  data              Json
  translationStatus TranslationStatus @default(ORIGINAL) @map("translation_status")
  createdAt         DateTime          @default(now()) @map("created_at")
  updatedAt         DateTime          @updatedAt @map("updated_at")
  block             ArticleBlock      @relation(fields: [blockId], references: [id], onDelete: Cascade)

  @@unique([blockId, locale])
  @@index([blockId])
  @@index([locale])
  @@map("article_block_i18n")
}

model ArticleProject {
  id        String   @id @default(cuid())
  articleId String   @map("article_id")
  projectId String   @map("project_id")
  createdAt DateTime @default(now()) @map("created_at")

  article Article @relation(fields: [articleId], references: [id], onDelete: Cascade)
  project Project @relation(fields: [projectId], references: [id], onDelete: Cascade)

  @@unique([articleId, projectId])
  @@index([projectId])
  @@index([articleId])
  @@map("article_projects")
}
```

---

## 12. Migration depuis l'existant

Si vous migrez depuis une implémentation existante :

1. **Exporter les données** : `pg_dump` ou script d'export JSON.
2. **Vérifier les types** : `gallery_media_ids` et `category_slugs` doivent être des tableaux JSON valides.
3. **Media** : S'assurer que `cover_media_id` et les `mediaId` dans les blocs référencent des médias existants.
4. **i18n** : Chaque article doit avoir au moins un ArticleI18n (locale par défaut).
5. **Blocs** : Pour chaque bloc avec contenu traduit, créer les ArticleBlockI18n correspondants.

---

**Fin du document**
