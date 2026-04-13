# Audit — Vault Builder, Bundles & Projects Metadata System

## Executive Summary

L'audit révèle **3 systèmes distincts** de contenu produit dans la codebase, chacun avec son propre usage :

| Système | Usage actuel Flutter | Blueprint pour Exclusive Offers |
|---------|---------------------|--------------------------------|
| **Projects** (offres exclusives) | ✅ **OUI — principal** | ✅ **DIRECT — réutilisable tel quel** |
| **Vault Builder** (landing pages) | ✅ OUI (bundles crypto) | ⚠️ Partiellement réutilisable |
| **Market Data Bundles** (backtests) | ❌ NON (admin only) | ❌ Non pertinent |

**Découverte majeure** : il existe déjà un système `Projects` complet dans Prisma — avec i18n, galerie photos, cover/hero images, competitive advantages, FAQ, key information, how it works — qui est **exactement** le modèle utilisé par Flutter pour les "Offres Exclusives". Ce système est le blueprint naturel pour les `lending_pool_products`.

---

## Scope Clarification (3 systèmes)

### Système 1 — Projects (Offres Exclusives) ⭐ BLUEPRINT

| Aspect | Détail |
|--------|--------|
| **Tables Prisma** | `projects`, `project_i18n`, `project_media`, `investment_categories` |
| **Admin** | `/admin/projects/` (CRUD complet) |
| **API publique** | `GET /api/projects` |
| **Flutter** | `OffersApi.getProjects()` → `ExclusiveOfferCard` → `ExclusiveOfferDetailScreen` |
| **Actif en prod** | ✅ OUI |
| **Contenu** | Image cover, hero, galerie, titre, description, shortDescription, descriptionLinks, howItWorks, keyInformation, competitiveAdvantages, FAQ, vidéo teaser, catégorie d'investissement |
| **i18n** | ✅ OUI — table `project_i18n` avec fallback locale |
| **Médias** | Presigned URLs (R2/S3) via table `media` |

### Système 2 — Vault Builder (Landing Pages Crypto Bundles)

| Aspect | Détail |
|--------|--------|
| **Tables Prisma** | `pages`, `sections`, `section_contents`, `portfolio_product_configs` |
| **Admin** | `/admin/vault-builder` |
| **API publique** | `GET /api/mobile/flutter/vaults`, `GET /api/mobile/flutter/portfolio-products/{code}` |
| **Flutter** | `VaultBuilderApi` → `LandingPagePreviewScreen` + `ProductPreviewScreen` |
| **Actif en prod** | ✅ OUI |
| **Contenu** | Modules JSON configurables (TitlePage, Allocation, PerformanceChart, FAQ, Markdown, Carousel, etc.) |
| **i18n** | ❌ NON — locale unique `fr` |
| **Médias** | `headerMediaId`, `detailMediaId` via table `media` |

### Système 3 — Market Data Bundles (Legacy/Backtests)

| Aspect | Détail |
|--------|--------|
| **Tables SQLAlchemy** | `bundles`, `bundle_components` (API Python) |
| **Admin** | `/admin/bundles` |
| **API** | `GET /api/bundles` (admin auth only) |
| **Flutter** | ❌ NON utilisé directement |
| **Actif en prod** | Partiellement (données de marché uniquement) |
| **À réutiliser** | ❌ NON |

---

## Mobile Data Source of Truth

### Chaîne de données pour les Offres Exclusives (Flutter)

```
Admin Web (/admin/projects)
  │
  ▼
Prisma DB
  ├── projects (cover_media_id, hero_media_id, investment_category, youtube_url)
  ├── project_i18n (title, description, shortDescription, descriptionLinks,
  │                  howItWorks, keyInformation, competitiveAdvantages, faq)
  ├── project_media (galerie photos, order)
  └── media (key, url, filename, mimeType, alt)
  │
  ▼
Next.js API: GET /api/projects
  └── lib/cms/projects.ts → getLatestProjects()
      └── Résout i18n (fallback locale), presigned URLs, galerie
  │
  ▼
Flutter App
  ├── OffersApi.getProjects() → List<OfferProject>
  ├── ExclusiveOfferCard (image, title, category, progress, raised, investors, APY)
  ├── ExclusiveOfferDetailScreen (hero image, description, howItWorks, 
  │     keyInformation, competitiveAdvantages, FAQ, galerie, vidéo teaser)
  └── ExclusiveOffersCarousel (home screen, offers screen)
```

### Chaîne de données pour les Crypto Bundles (Flutter)

```
Admin Web (/admin/vault-builder)
  │
  ├─── Vault Builder (pages/sections/section_contents)
  │    └── Modules JSON (TitlePage, Allocation, PerformanceChart, etc.)
  │
  └─── Portfolio Engine Config (portfolio_product_configs)
       └── headerMediaId, detailMediaId, modules, sortOrder
  │
  ▼
Next.js API                     +  Python FastAPI
GET /api/mobile/flutter/            GET /api/portfolio-engine/
  portfolio-products/{code}           product-catalog
  vaults/{slug}                       products/{id}/chart-history
  │
  ▼
Flutter App
  ├── ProductCatalogApi → ProductCatalogItem + ProductDisplayConfig
  ├── CryptoBundlesWidget (carousel cartes)
  ├── ProductPreviewScreen → LandingPagePreviewScreen (modules)
  └── BundleInvestFlow (invest, preview, confirm)
```

---

## Entity / Table Map

### Tables utilisées par le système Projects (Offres Exclusives)

| Table Prisma | Colonnes clés | Rôle |
|-------------|---------------|------|
| `projects` | `id`, `slug`, `status`, `cover_media_id`, `hero_media_id`, `youtube_url`, `investment_category`, `competitive_advantages` (JSON) | Entité principale |
| `project_i18n` | `project_id`, `locale`, `title`, `short_description`, `description`, `description_links` (JSON), `competitive_advantages` (JSON), `how_it_works` (JSON), `key_information` (JSON), `faq` (JSON), `location`, `meta_title`, `meta_description` | Contenu localisé |
| `project_media` | `project_id`, `media_id`, `order` | Galerie photos ordonnée |
| `investment_categories` | `id`, `slug`, `label`, `image_url`, `media_id`, `sort_order` | Catégories d'offres |
| `media` | `id`, `key`, `url`, `filename`, `mime_type`, `size`, `width`, `height`, `alt` | Médias (R2/S3) |
| `article_projects` | `article_id`, `project_id` | Lien articles → projets |

### Tables utilisées par le Vault Builder (Crypto Bundles)

| Table Prisma | Colonnes clés | Rôle |
|-------------|---------------|------|
| `pages` | `id`, `slug`, `url_path`, `title`, `description`, `template` | Page CMS (template = `vault_builder`) |
| `sections` | `id`, `page_id`, `key`, `order` | Section de page (key = `vault_builder_v1`) |
| `section_contents` | `section_id`, `locale`, `status`, `data` (JSON) | Contenu DRAFT/PUBLISHED complet |
| `portfolio_product_configs` | `product_code`, `header_media_id`, `detail_media_id`, `modules` (JSON), `sort_order`, `is_published` | Config UI des produits PE |

### Tables backend Python (Portfolio Engine)

| Table SQLAlchemy | Rôle |
|-----------------|------|
| `pe_product_definitions` | Définition produit (name, product_code, product_type, risk_label, metadata JSONB) |
| `pe_portfolio_templates` | Template d'allocation (lié à un produit) |
| `pe_template_allocations` | Allocations cibles (instrument_id, target_weight) |

---

## Admin Vault Builder Flow

### Flow pour créer un Crypto Bundle

```
/admin/vault-builder
  1. Créer un produit PE (nom, code, risk, allocations)
     → POST /api/admin/portfolio-engine/bundles
     → Crée pe_product_definitions + pe_portfolio_templates + pe_template_allocations
  
  2. Configurer le contenu marketing
     → PUT /api/admin/portfolio-engine/products/{code}/config
     → Sauvegarde portfolio_product_configs (headerMediaId, detailMediaId, modules)
  
  3. Publier
     → PATCH /api/admin/portfolio-engine/bundles/{id}/visibility
     → is_public = true
```

### Flow pour créer un Projet (Offre Exclusive)

```
/admin/projects
  1. Créer le projet
     → POST /api/admin/projects
     → Crée projects (slug, investment_category)
  
  2. Ajouter le contenu i18n
     → PUT /api/admin/projects/{id}/i18n
     → Sauvegarde project_i18n (title, description, shortDescription,
        descriptionLinks, howItWorks, keyInformation, competitiveAdvantages, faq)
  
  3. Uploader cover + hero + galerie
     → POST /api/admin/media/upload
     → PUT /api/admin/projects/{id} (cover_media_id, hero_media_id)
     → POST /api/admin/projects/{id}/gallery (project_media)
  
  4. Publier
     → POST /api/admin/projects/{id}/publish
     → status = PUBLISHED
```

---

## Metadata Types

### Offres Exclusives (Projects) — Actuellement en production

| Type | Stockage | Structure | Rendu Flutter |
|------|----------|-----------|---------------|
| **Cover image** | `projects.cover_media_id` → `media` | Presigned URL R2 | `ExclusiveOfferCard.imageUrl` (fond carte) |
| **Hero image** | `projects.hero_media_id` → `media` | Presigned URL R2 | `ExclusiveOfferDetailScreen` (image 60% hauteur) |
| **Title** | `project_i18n.title` | String | Titre carte + page détail |
| **Short description** | `project_i18n.short_description` | String | Sous-titre / module infos clés |
| **Description** | `project_i18n.description` | Markdown | Page détail (bloc description) |
| **Description links** | `project_i18n.description_links` | `[{ label, url }]` | Liens cliquables dans la description |
| **How it works** | `project_i18n.how_it_works` | `{ title, content, links[] }` | Module explicatif avec markdown |
| **Key information** | `project_i18n.key_information` | `{ title, rows[{ categoryKey, label, value, showInfoIcon, infoTitle, infoContent }] }` | Tableau d'infos clés avec modales info |
| **Competitive advantages** | `project_i18n.competitive_advantages` | `{ title, rows[{ icon, iconBackgroundColor, title, description }] }` | Cards avantages avec icônes |
| **FAQ** | `project_i18n.faq` | `{ enableTagRedirect, tagRedirectLabel, items[{ articleId, articleSlug, collectionSlug, categorySlug, question, standfirst }] }` | Accordéon FAQ lié au Help Center |
| **Video teaser** | `projects.youtube_url` | URL YouTube | Bouton "Play the teaser" |
| **Photo gallery** | `project_media` (order) → `media` | Presigned URLs ordonnées | Carrousel photos |
| **Category** | `projects.investment_category` | String enum | Badge catégorie (Real estate, Energy, etc.) |
| **Location** | `project_i18n.location` | String | Localisation du projet |

### Crypto Bundles (Vault Builder) — Modules

| Module type | Contenu | Rendu Flutter |
|-------------|---------|---------------|
| `TitlePage` | `{ title, subtitle }` | Header titre/sous-titre |
| `AllocationModule` | `{ title, introText, size, slices[{ label, percentage, colorHex }] }` | Donut chart allocations |
| `PerformanceChart` | `{ title }` | Graphique performance historique |
| `KeyInformationModule` | `{ title, rows[{ label, value }] }` | Tableau infos clés |
| `FaqAccordionModule` | `{ title, items[] }` | FAQ accordéon |
| `SimpleMarkdownContentModule` | `{ moduleTitle, markdown, links[] }` | Contenu markdown |
| `CompetitiveAdvantagesModule` | `{ title, rows[{ icon, title, description }] }` | Cards avantages |
| `MarketingCardsSmallCarouselModule` | `{ items[] }` | Carrousel marketing |

---

## Media System

### Architecture

```
Upload: MediaPicker (admin) → POST /api/admin/media/upload → R2/S3
         ↓
Store:   media table (key, url, filename, mimeType, size, width, height, alt)
         ↓
Serve:   getPresignedUrl(key, ttl=3600) → URL temporaire signée (1h)
         ↓
Display: Flutter CachedNetworkImage(url)
```

### Réutilisabilité

| Aspect | Réutilisable pour Exclusive Offers ? |
|--------|--------------------------------------|
| Table `media` | ✅ OUI — générique |
| Upload via `MediaPicker` | ✅ OUI — composant admin réutilisable |
| Presigned URLs | ✅ OUI — via `getPresignedUrl()` |
| Relations FK (cover, hero, gallery) | ✅ OUI — même pattern |

---

## Backend API Mapping

### API publique Projects (Mobile)

| Endpoint | Méthode | Données retournées |
|----------|---------|-------------------|
| `GET /api/projects` | Query: `locale`, `limit` | `{ projects: [{ id, slug, title, coverUrl, category, description, shortDescription, descriptionLinks, howItWorks, keyInformation, teaserVideoUrl, hasGallery, competitiveAdvantages, faq }] }` |
| `GET /api/projects/{id}/articles` | | Articles liés au projet |
| `GET /api/investment-categories` | | Catégories avec image |

### API admin Projects

| Endpoint | Méthode | Usage |
|----------|---------|-------|
| `POST /api/admin/projects` | Création | slug, investment_category |
| `PUT /api/admin/projects/{id}` | Mise à jour | cover, hero, youtube, category |
| `PUT /api/admin/projects/{id}/i18n` | Contenu localisé | title, description, howItWorks, etc. |
| `POST /api/admin/projects/{id}/gallery` | Ajout photo | media_id, order |
| `POST /api/admin/projects/{id}/publish` | Publication | status → PUBLISHED |
| `GET /api/admin/projects/{id}/faq-options` | Options FAQ | Articles Help Center disponibles |

### API publique Product Catalog (Mobile)

| Endpoint | Méthode | Données retournées |
|----------|---------|-------------------|
| `GET /api/portfolio-engine/product-catalog` | Query: `product_type` | `{ items: [{ id, product_code, name, allocations[], risk_label, metadata }] }` |
| `GET /api/portfolio-engine/products/{id}/chart-history` | Query: `period` | `{ points[], performance_pct, constituents[] }` |
| `GET /api/mobile/flutter/portfolio-products/configs` | | `{ configs: { CODE: { headerMediaUrl, detailMediaUrl, sortOrder } } }` |

---

## Flutter Consumption

### Offres Exclusives — Composants Flutter

| Composant | Fichier | Données consommées |
|-----------|---------|-------------------|
| `ExclusiveOfferCard` | `exclusive_offer_card.dart` | `imageUrl`, `category`, `title`, `description`, `progress`, `raisedAmount`, `investorsCount`, `annualizedReturnPercent`, `targetDurationMonths`, `isLiked` |
| `ExclusiveOfferCardV2` | `exclusive_offer_card_v2.dart` | Variante avec layout différent |
| `FeaturedOfferCard` | `featured_offer_card.dart` | Card mise en avant (home) |
| `ExclusiveOffersCarousel` | `exclusive_offers_carousel.dart` | Carousel horizontal d'offres |
| `ExclusiveOfferDetailScreen` | `exclusive_offer_detail_screen.dart` | Page détail complète (~1900 lignes) : hero image, description, howItWorks, keyInformation, competitiveAdvantages, FAQ, galerie, vidéo, articles liés |
| `OffersScreen` | `offers_screen.dart` | Écran principal "Offres" avec catégories + liste |

### Crypto Bundles — Composants Flutter

| Composant | Données consommées |
|-----------|-------------------|
| `CryptoBundlesWidget` | `ProductCatalogItem` + `ProductDisplayConfig` |
| `AssetsBundleCard` | `imageUrl`, `title`, `description`, `performance24h`, `cryptoIcons` |
| `ProductPreviewScreen` | `LandingPagePayload` (modules) |
| `BundleWalletDetailScreen` | `MyBundleSummary` (positions, stats, history) |

### Contrat JSON attendu par Flutter (OfferProject)

```json
{
  "id": "string",
  "coverUrl": "https://presigned-r2-url...",
  "title": "Solar Project UAE",
  "category": "Energy",
  "shortDescription": "Rendement 8% annuel...",
  "description": "## Description du projet\n\nMarkdown complet...",
  "descriptionLinks": [{ "label": "Site officiel", "url": "https://..." }],
  "howItWorks": {
    "title": "Comment ça marche",
    "content": "Markdown...",
    "links": [{ "label": "Voir plus", "url": "..." }]
  },
  "keyInformation": {
    "title": "Informations clés",
    "rows": [{
      "categoryKey": "yield",
      "label": "Rendement annuel",
      "value": "8.0%",
      "showInfoIcon": true,
      "infoTitle": "Rendement estimé",
      "infoContent": "Ce rendement est basé sur..."
    }]
  },
  "competitiveAdvantages": {
    "title": "Pourquoi investir",
    "rows": [{
      "icon": "shield",
      "iconBackgroundColor": "#10B981",
      "title": "Garanti par actifs réels",
      "description": "Le projet est adossé à..."
    }]
  },
  "faq": {
    "enableTagRedirect": true,
    "tagRedirectLabel": "Voir toutes les questions",
    "items": [{
      "articleId": "...",
      "question": "Quand vais-je recevoir mes intérêts ?",
      "standfirst": "Les intérêts sont..."
    }]
  },
  "teaserVideoUrl": "https://youtube.com/watch?v=...",
  "hasGallery": true
}
```

---

## Reusability for Exclusive Offers

### Mapping direct : Projects → Lending Pool Products

| Champ Project (existant) | Champ LendingPoolProduct (Phase 2A.10) | Réutilisable ? |
|--------------------------|----------------------------------------|---------------|
| `projects.slug` | — (utiliser `product_id`) | ⚠️ Adapter |
| `project_i18n.title` | `lending_pool_products.title` | ✅ Direct |
| `project_i18n.short_description` | — | ✅ À ajouter |
| `project_i18n.description` | `lending_pool_products.description` | ✅ Direct |
| `projects.cover_media_id` | — | ✅ À ajouter |
| `projects.hero_media_id` | — | ✅ À ajouter |
| `project_i18n.description_links` | — | ✅ À ajouter |
| `project_i18n.how_it_works` | — | ✅ À ajouter |
| `project_i18n.key_information` | — | ✅ À ajouter |
| `project_i18n.competitive_advantages` | — | ✅ À ajouter |
| `project_i18n.faq` | — | ✅ À ajouter |
| `projects.youtube_url` | — | ✅ À ajouter |
| `project_media` (gallery) | — | ✅ À ajouter |
| `projects.investment_category` | — | ✅ À ajouter |
| — | `target_size` | 🆕 Spécifique lending |
| — | `current_raised` | 🆕 Spécifique lending |
| — | `supply_apr_bps` / `borrow_apr_bps` | 🆕 Spécifique lending |
| — | `borrower_client_id` | 🆕 Spécifique lending |
| — | `min_ticket` / `max_ticket` | 🆕 Spécifique lending |

### Ce qui est réutilisable tel quel

| Élément | Statut |
|---------|--------|
| Table `media` (images R2/S3) | ✅ Réutilisable |
| Composant `MediaPicker` (admin upload) | ✅ Réutilisable |
| Presigned URLs (`getPresignedUrl`) | ✅ Réutilisable |
| Modèle i18n (`project_i18n` pattern) | ✅ Réutilisable (créer `lending_product_i18n`) |
| Galerie photos (`project_media` pattern) | ✅ Réutilisable |
| `ExclusiveOfferCard` (Flutter) | ✅ **Déjà conçu pour ça** |
| `ExclusiveOfferDetailScreen` (Flutter) | ✅ **Déjà conçu pour ça** |
| `ExclusiveOffersCarousel` (Flutter) | ✅ **Déjà conçu pour ça** |
| Categories d'investissement | ✅ Réutilisable |

### Ce qui doit être adapté

| Élément | Adaptation nécessaire |
|---------|----------------------|
| `OfferProject` model Dart | Ajouter champs lending (APY, raised, target, investors) |
| `OffersApi` | Pointer vers les `lending_pool_products` au lieu de `projects` |
| Endpoint `GET /api/projects` | Créer `/api/lending-offers` ou enrichir `projects` |
| Admin Projects | Ajouter section "lending config" (rates, target, borrower) |

### Ce qui est spécifique aux Bundles (non réutilisable)

| Élément | Raison |
|---------|--------|
| `pe_product_definitions` | Spécifique allocation crypto |
| `pe_template_allocations` | Poids par instrument |
| Modules `AllocationModule`, `PerformanceChart` | Donut chart + courbe perf |
| `BundleInvestFlow` | Flow investissement spécifique |
| `ProductCatalogApi` | Catalog PE uniquement |

---

## Recommendations for Phase 2A.11

### Option A — Lier `lending_pool_products` à `projects` (recommandé)

```
lending_pool_products.project_id → projects.id
```

**Avantages** :
- Réutilise 100% du CMS existant (i18n, gallery, cover/hero, FAQ, etc.)
- Flutter `ExclusiveOfferDetailScreen` fonctionne déjà
- Pas de duplication de contenu marketing
- Admin Projects déjà fonctionnel

**À faire** :
1. Ajouter `project_id` FK optionnel dans `lending_pool_products`
2. Enrichir `GET /api/projects` pour inclure les données lending (APY, raised, target)
3. Adapter `OffersApi` Flutter pour merger données projet + données lending
4. Ajouter dans l'admin Projects un lien vers la config lending

### Option B — Dupliquer les champs marketing dans `lending_pool_products`

```
lending_pool_products += cover_media_id, hero_media_id, short_description, etc.
```

**Avantages** : autonomie complète, pas de dépendance
**Inconvénients** : duplication, pas d'i18n, pas de galerie, refaire l'admin

### Recommandation : **Option A**

Le système `Projects` est exactement le CMS produit dont les Exclusive Offers ont besoin. Flutter a déjà `ExclusiveOfferCard` avec `progress`, `raisedAmount`, `investorsCount`, `annualizedReturnPercent` — ces champs correspondent parfaitement aux données de `lending_pool_products`.

---

## Tableau synthétique 1 — Vault Builder vs Legacy Bundles vs Projects

| Critère | Projects (Offres) | Vault Builder (Bundles Crypto) | Market Data Bundles (Legacy) |
|---------|-------------------|-------------------------------|------------------------------|
| **Tables** | `projects`, `project_i18n`, `project_media` | `pages`, `sections`, `section_contents`, `portfolio_product_configs` | `bundles`, `bundle_components` |
| **Admin** | `/admin/projects/` | `/admin/vault-builder` | `/admin/bundles` |
| **API publique** | `GET /api/projects` | `GET /api/mobile/flutter/vaults` + `portfolio-products` | ❌ (admin only) |
| **i18n** | ✅ Complet (multi-locale) | ❌ (fr only) | ❌ |
| **Galerie photos** | ✅ (`project_media` avec order) | ❌ (single header/detail) | ❌ |
| **Flutter** | `ExclusiveOfferCard` + `DetailScreen` | `LandingPagePreviewScreen` | ❌ |
| **Adapté pour lending** | ✅ **PARFAIT** | ⚠️ Trop générique | ❌ |

## Tableau synthétique 2 — Data Path: Admin → DB → API → Flutter

| Étape | Projects (Offres Exclusives) | Vault Builder (Crypto Bundles) |
|-------|------------------------------|-------------------------------|
| **Admin** | `/admin/projects/{id}` | `/admin/vault-builder` |
| **DB Write** | `projects` + `project_i18n` + `project_media` | `pages` + `sections` + `section_contents` + `portfolio_product_configs` |
| **API Route** | `GET /api/projects` | `GET /api/mobile/flutter/portfolio-products/{code}` |
| **Service** | `lib/cms/projects.ts` → `getLatestProjects()` | `lib/cms/content.ts` + FastAPI `/api/portfolio-engine/product-catalog` |
| **Résolution** | i18n fallback + presigned URLs | JSON modules + presigned URLs |
| **Flutter API** | `OffersApi.getProjects()` | `ProductCatalogApi.getBundleCatalog()` + `getDisplayConfigs()` |
| **Flutter Model** | `OfferProject` | `ProductCatalogItem` + `ProductDisplayConfig` + `LandingPagePayload` |
| **Flutter Screen** | `ExclusiveOfferDetailScreen` (1900 lignes, hero + modules) | `ProductPreviewScreen` → `LandingPagePreviewScreen` |
