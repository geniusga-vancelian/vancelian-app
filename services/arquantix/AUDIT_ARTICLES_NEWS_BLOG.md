# Audit : Système d'articles, news et blog — Architecture Backend & Base de données

**Date :** 2026-02-18  
**Périmètre :** Arquantix — Articles, News, Blog

---

## 1. Synthèse exécutive

Le projet Arquantix dispose de **deux systèmes d’articles/news distincts** qui coexistent sans être unifiés :

| Système | Base de données | Utilisé par | Statut |
|---------|-----------------|-------------|--------|
| **News** (API FastAPI) | `arquantix_quant` | Non utilisé par le front | Orphelin |
| **Article** (Web Prisma) | `arquantix_admin` | Blog public + Admin | Actif |
| **HelpArticle** (Web Prisma) | `arquantix_admin` | Help Center | Actif |

Le blog public (`/blog`, `/blog/[slug]`) repose uniquement sur le modèle **Article** (Prisma). Le modèle **News** de l’API n’est pas consommé par le front.

---

## 2. Architecture actuelle

### 2.1 Vue d’ensemble des bases de données

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    arquantix-db (PostgreSQL, port 5443)                   │
├─────────────────────────────────────────────────────────────────────────┤
│  arquantix_quant (API)              │  arquantix_admin (Web)           │
│  ─────────────────────────           │  ─────────────────────────       │
│  • news                              │  • articles                       │
│  • pages                             │  • article_blocks                 │
│  • global_settings                   │  • article_block_i18n              │
│  • admin_users                       │  • article_i18n                   │
│  • market_data_*                     │  • article_categories            │
│  • backtest_*                        │  • help_articles                  │
│  • ...                               │  • pages, sections, media, ...    │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Flux de données du blog

```
Utilisateur → /blog ou /blog/[slug]
                    │
                    ▼
            Next.js (Web)
                    │
                    ├── GET /api/blog (liste, featured, highlighted)
                    └── Prisma → arquantix_admin.articles
```

L’API FastAPI (`/public/news/*`) n’est pas appelée par le front pour le blog.

---

## 3. Audit détaillé par système

### 3.1 News (API FastAPI) — Base `arquantix_quant`

#### Modèle (`api/database.py`)

```python
class News(Base):
    __tablename__ = "news"
    id = Column(Integer, primary_key=True)
    slug = Column(String(255), nullable=False)
    locale = Column(String(10), nullable=False, default="fr")
    title = Column(String(500), nullable=False)
    excerpt = Column(Text, nullable=True)
    content_markdown = Column(Text, nullable=True)
    cover_image_url = Column(String(1000), nullable=True)
    status = Column(SQLEnum(StatusEnum), nullable=False)
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), ...)
```

#### Points forts

- Schéma simple et lisible
- Index `ix_news_slug_locale` (slug, locale) unique
- i18n via lignes dupliquées (slug+locale)
- CRUD admin complet
- Endpoints publics : `GET /public/news/{locale}`, `GET /public/news/{locale}/{slug}`

#### Points faibles

- **Non utilisé** : le front ne consomme pas ces endpoints
- Contenu en Markdown uniquement (pas de blocs riches)
- `cover_image_url` : URL brute, pas de gestion centralisée des médias
- Pas de champs de traduction (source_page_id, translation_status) comme pour `Page`
- Pas de catégories, pas de lien avec des projets

#### Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/public/news/{locale}` | Liste des news publiées |
| GET | `/public/news/{locale}/{slug}` | Détail d’une news |
| GET | `/admin/news` | Liste admin (React Admin) |
| POST | `/admin/news` | Création |
| GET | `/admin/news/{id}` | Détail admin |
| PUT | `/admin/news/{id}` | Mise à jour |
| DELETE | `/admin/news/{id}` | Suppression |

---

### 3.2 Article (Web Prisma) — Base `arquantix_admin`

#### Modèles (`web/prisma/schema.prisma`)

```
Article
├── ArticleI18n (title, standfirst, metaTitle, metaDescription par locale)
├── ArticleBlock (structure : type, order, data)
│   └── ArticleBlockI18n (contenu par locale)
├── ArticleProject (liaison projets)
└── ArticleCategory (via categorySlugs JSON)
```

#### Points forts

- Modèle riche : blocs (HEADING, PARAGRAPH, QUOTE, BULLET_LIST, IMAGE, VIDEO, DOCUMENT)
- i18n complet : ArticleI18n + ArticleBlockI18n
- Catégories via `ArticleCategory` + `categorySlugs`
- Liaison avec projets (`ArticleProject`)
- Gestion des médias via `Media` (cover, gallery, presigned URLs)
- Traduction IA : `/api/admin/translate/article`
- SEO : metaTitle, metaDescription, Schema.org

#### Points faibles

- `categorySlugs` en JSON : pas de FK, filtrage manuel
- `galleryMediaIds` et `documents` en JSON : structure peu typée
- Pagination du feed : `take: 100` puis slice en mémoire (non scalable)
- Pas d’index dédié pour `categorySlugs` (requêtes JSON)

#### Index existants

- `articles`: status, publishedAt
- `article_blocks`: articleId
- `article_block_i18n`: blockId, locale

---

### 3.3 HelpArticle (Web Prisma) — Base `arquantix_admin`

Système séparé pour le Help Center :

- `HelpCollection` → `HelpCategory` → `HelpArticle`
- `HelpArticleBlock` avec `locale` directement (pas de table I18n séparée)
- Modèle plus simple, adapté à la doc d’aide

---

## 4. Problèmes d’architecture identifiés

### 4.1 Duplication News vs Article

| Critère | News (API) | Article (Web) |
|---------|------------|---------------|
| Base | arquantix_quant | arquantix_admin |
| Contenu | Markdown plat | Blocs structurés |
| i18n | Lignes par locale | Tables I18n |
| Médias | URL brute | Media + presigned |
| Utilisation | Aucune | Blog public |

**Recommandation :** Décider d’un seul système. Si le blog reste sur Article (Prisma), envisager la dépréciation ou la suppression de News (API).

### 4.2 Séparation des bases

- **arquantix_quant** : quant, backtest, market data, news, pages (legacy)
- **arquantix_admin** : CMS (pages, sections, articles, help, media)

Les `pages` existent dans les deux bases (API et Web). La doc indique que le Web utilise `arquantix_admin` pour le CMS.

### 4.3 Performance du feed blog

```typescript
// web/src/app/api/blog/route.ts
const allFeedArticles = await prisma.article.findMany({
  where: { status: ContentStatus.PUBLISHED },
  take: 100,  // ⚠️ Limite arbitraire
  ...
})
// Puis filtrage en mémoire par catégorie
// Puis slice pour pagination
```

- Pas de pagination côté base
- Filtrage par `categorySlugs` (JSON) en mémoire
- Risque de surcharge avec beaucoup d’articles

---

## 5. Qualité du code

### 5.1 Points positifs

- Validation Zod sur les API admin
- Gestion des presigned URLs pour S3/R2
- Fallback i18n : `block.i18n[0]?.data || block.data`
- Schema.org pour le SEO
- Traduction des blocs (ArticleBlockI18n) en place

### 5.2 Points d’attention

- `(article as any).categorySlugs` : cast `any` répété
- Parsing manuel de `categorySlugs` (string vs array) à plusieurs endroits
- Pas de couche service dédiée : logique dans les routes

---

## 6. Recommandations

### Priorité haute

1. **Clarifier le rôle de News (API)**  
   - Soit l’intégrer au front (ex. page `/news`), soit le déprécier et documenter.

2. **Pagination côté base pour le feed blog**  
   - Utiliser `skip`/`take` Prisma avec `cursor` ou `offset`  
   - Filtrer par catégorie dans la clause `where` si possible

### Priorité moyenne

3. **Typage de `categorySlugs`**  
   - Créer une table de liaison `ArticleCategoryLink` ou utiliser un type Prisma plus strict

4. **Index pour les requêtes fréquentes**  
   - Index GIN sur `categorySlugs` si on garde le JSON  
   - Ou migration vers une table de liaison

### Priorité basse

5. **Refactorisation**  
   - Extraire la logique article dans un module `lib/blog/` ou `services/article/`

6. **Documentation**  
   - Mettre à jour ARCHITECTURE.md pour refléter l’usage réel (Article vs News)

---

## 7. Schéma récapitulatif des tables

### arquantix_quant (API)

```
news
├── id (PK)
├── slug, locale (unique)
├── title, excerpt, content_markdown
├── cover_image_url
├── status, published_at, updated_at
```

### arquantix_admin (Web)

```
articles
├── id, slug (unique)
├── status, published_at, cover_media_id
├── category_slugs (JSON), gallery_media_ids (JSON)
├── author_name, author_role, is_featured, is_highlighted
└── documents (JSON)

article_i18n
├── article_id, locale (unique)
├── title, standfirst, meta_title, meta_description
└── translation_status

article_blocks
├── id, article_id, order (unique)
├── type (enum), data (JSON)
└── article_block_i18n (block_id, locale, data)

article_categories
├── id, slug, label, order, is_active
└── article_category_i18n
```

---

## 8. Corrections appliquées (2026-02-18)

### ✅ Pagination côté base
- **Fichier :** `web/src/lib/blog/articleService.ts`
- Pagination via `skip`/`take` Prisma au lieu de `take: 100` + slice
- `count()` pour le total et `hasMore` correct

### ✅ Filtrage par catégorie
- Requête SQL brute PostgreSQL (`@>` JSONB) pour le filtrage par catégorie
- Évite les limites de Prisma sur les champs JSON

### ✅ Couche service
- `web/src/lib/blog/articleService.ts` : logique centralisée
- `parseCategorySlugs()` : helper réutilisable
- Route API simplifiée

### ✅ News API dépréciée
- Endpoints `/public/news/*` et `/admin/news/*` marqués `deprecated=True`
- Swagger affiche les avertissements de dépréciation

### Recommandation restante
- **Index GIN** sur `category_slugs` pour optimiser les requêtes avec filtre catégorie (migration Prisma)

---

**Dernière mise à jour :** 2026-02-18
