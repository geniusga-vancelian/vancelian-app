# Spécification — Stack complet Arquantix

**Objectif :** documenter l’ensemble du stack pour recréer un projet from scratch, plus propre, avec les mêmes fondamentaux.

**Date :** 2026-02-25

---

## 1. Vue d’ensemble

| Couche | Techno principale | Rôle |
|--------|-------------------|------|
| **Site vitrine + Admin** | Next.js 14 (App Router) | Frontend, API routes, CMS admin, blog public |
| **Base de données** | PostgreSQL | Données métier (Prisma pour le web) |
| **Stockage fichiers** | R2 / S3-compatible | Médias (images, PDF) avec URLs signées |
| **API métier (optionnelle)** | FastAPI (Python) | Quant, market data, backtest, JWT |
| **App mobile** | Flutter (Dart) | Consommation API blog / news |

---

## 2. Stack technique détaillé

### 2.1 Next.js (web)

- **Runtime :** Node.js 20+
- **Framework :** Next.js 14.x, App Router
- **Langage :** TypeScript 5.x
- **Styles :** Tailwind CSS 3.x, PostCSS, Autoprefixer
- **UI :** Radix UI (primitives), Lucide (icons), composants custom (shadcn-style)
- **ORM / DB :** Prisma 6.x, client généré, migrations
- **Validation :** Zod 4.x
- **Auth :** Session par cookie (token en DB), bcrypt pour les mots de passe, pas de NextAuth
- **Rendu :** SSR par défaut, pas de static export global

**Dépendances notables :**
- `@prisma/client`, `prisma`
- `@aws-sdk/client-s3`, `@aws-sdk/s3-request-presigner` (R2)
- `bcryptjs`, `jsonwebtoken`
- `zod`, `clsx`, `tailwind-merge`, `class-variance-authority`
- `react-markdown`, `sharp`, `sonner`, `recharts`, `lightweight-charts`, etc.

**Ports :**
- Dev : 3001 (`next dev -p 3001`) ou 3000
- Container / prod : 3000 (`PORT=3000`)

**Variables d’environnement (web) :**
- `DATABASE_URL` — PostgreSQL (Prisma)
- `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_PUBLIC_URL` (optionnel)
- `JWT_SECRET_KEY` ou `AUTH_SECRET` — sessions / JWT
- `NEXT_PUBLIC_BASE_URL` — URL du site (SSR fetch)
- `BACKEND_URL` ou `NEXT_PUBLIC_BACKEND_URL` — API FastAPI (optionnel)
- `MAX_UPLOAD_MB` — limite upload médias (défaut 20)
- `ADMIN_SEED_EMAIL`, `ADMIN_SEED_PASSWORD` — seed premier admin

---

### 2.2 Base de données (PostgreSQL)

- **Moteur :** PostgreSQL 15+
- **Bases :**
  - `arquantix_admin` — utilisée par Next.js (Prisma) : CMS, blog, pages, médias, help, menus, emails
  - `arquantix_quant` — optionnelle, pour l’API Python (market data, backtest, etc.)
- **Accès web :** Prisma uniquement (pas de Strapi en prod dans la spec actuelle)
- **Migrations :** `prisma migrate dev` / `prisma migrate deploy`

**Modèles principaux (Prisma) :**
- **Auth / users :** `User`, `Session` (token, expiration)
- **CMS :** `Page`, `Section`, `SectionContent` (locale, status DRAFT/PUBLISHED, data JSON)
- **Médias :** `Media` (key, url, filename, mimeType, size, width, height, alt)
- **Blog :** `Article`, `ArticleI18n`, `ArticleBlock`, `ArticleBlockI18n`, `ArticleCategory`, `ArticleCategoryI18n`, `ArticleProject`
- **Projets :** `Project`, `ProjectI18n`, `ProjectMedia`
- **Menus :** `Menu`, `MenuI18n`, `MenuItem`, `MenuItemI18n` (lien page ou externalUrl)
- **Help :** `HelpCollection`, `HelpCategory`, `HelpArticle` + i18n et blocs
- **Emails :** `Email`, `EmailI18n`, `EmailModule`, `EmailTemplateEntity`, etc.
- **Traduction :** `TranslationLog`, `AppSettings` (locales, glossaire)
- **Enums :** `ContentStatus` (DRAFT, PUBLISHED), `TranslationStatus`, `ArticleBlockType` (HEADING, PARAGRAPH, QUOTE, BULLET_LIST, IMAGE, VIDEO, DOCUMENT), `UserRole`, etc.

**Conventions :**
- IDs : `cuid()` (Prisma)
- i18n : tables dédiées `*I18n` avec `locale` + `translationStatus`
- Contenu structuré : blocs avec `type` + `data` (JSON), ordre numérique
- Index sur `slug`, `locale`, `status`, `publishedAt`, clés étrangères

---

### 2.3 Stockage (R2 / S3)

- **API :** S3-compatible (AWS SDK v3)
- **Usage :** upload médias (admin), URLs signées (1h) pour lecture
- **Config :** `R2_*` ou équivalent S3 (endpoint, credentials, bucket, URL publique optionnelle)
- **Fallback :** possible stockage local pour dev (fichiers sur disque)

---

### 2.4 API Python (FastAPI) — optionnelle

- **Runtime :** Python 3.11+
- **Framework :** FastAPI 0.109+, Uvicorn
- **ORM :** SQLAlchemy 2.x, Alembic
- **DB :** PostgreSQL (psycopg2-binary)
- **Auth :** JWT (python-jose, passlib bcrypt)
- **Usage :** market data, backtest, bundles, diagnostics, AI (email, jurisdiction, strategy chat), persons, onboarding, AML, chatbot épargne, etc.
- **CORS :** origines autorisées (ex. localhost:3000, 3001, 3011)
- **Port typique :** 8000

**Variables d’environnement (API) :**
- `DATABASE_URL` (ou équivalent pour la base quant)
- `STORAGE_BACKEND`, `MEDIA_BASE_URL`
- Secret JWT aligné avec le web si partage de tokens

---

### 2.5 App mobile (Flutter)

- **SDK :** Flutter 3.x, Dart >= 3.2
- **Packages :** `http`, `cached_network_image`, `intl`, `url_launcher`
- **Cible :** Android, iOS, Web (Chrome)
- **Config :** URL API en `String.fromEnvironment('API_BASE_URL')` ou script (ex. `API_BASE_URL=http://10.0.2.2:3001` pour l’émulateur Android)
- **Endpoints consommés :** `GET /api/blog`, `GET /api/blog/[slug]?locale=fr`

**Conventions :**
- Modèles Dart : `ArticlePreview`, `ArticleDetail`, `ArticleBlock`, catégories, documents
- Locale dates : `initializeDateFormatting('fr_FR', null)` au démarrage (intl)
- Raccourcis shell : script `go.sh` / `run-android.sh`, aliases (`arq`, `arq-emu`, `arq-chrome`)

---

## 3. Internationalisation (i18n)

- **Locales supportées :** `fr` (défaut), `en`, `it`
- **Stockage :** tables `*I18n` par entité (label, title, description, etc.) + `translationStatus` (ORIGINAL, MACHINE, APPROVED)
- **Frontend :** locale via cookie ou segment d’URL (ex. `/fr`, `/en`), `getLocaleOrDefault()`
- **API blog :** paramètre `?locale=fr`
- **Traduction IA :** workflows dédiés (article, catégorie, section, etc.) avec logs dans `TranslationLog`

---

## 4. Authentification (web)

- **Mécanisme :** session par cookie HTTP-only
- **Nom du cookie :** `arq_admin_session`
- **Durée :** 7 jours
- **Stockage :** table `Session` (token, userId, expiresAt)
- **Mots de passe :** bcrypt (10 rounds)
- **Protection routes admin :** middleware ou `getSessionFromCookie()` dans les API routes
- **Pas de JWT côté navigateur** pour l’admin ; JWT utilisé pour certaines API métier (Python ou proxy Next.js)

---

## 5. Structure des contenus

### 5.1 Pages CMS

- **Page** : slug, urlPath, template (ex. homepage, blog), themeColor
- **Section** : key, order, schemaVersion
- **SectionContent** : locale, status (DRAFT / PUBLISHED), data (JSON), translationStatus
- Rendu : composants par type de section (SectionRenderer + library de sections)

### 5.2 Blog / Articles

- **Article** : slug, status, publishedAt, coverMediaId, galleryMediaIds (JSON), videoUrl, categorySlugs (JSON), documents (JSON), isFeatured, isHighlighted, authorName, authorRole, coverTitle, coverCredit, coverSource
- **ArticleI18n** : title, standfirst, metaTitle, metaDescription, coverTitle
- **ArticleBlock** : order, type (HEADING, PARAGRAPH, QUOTE, BULLET_LIST, IMAGE, VIDEO, DOCUMENT), data (JSON)
- **ArticleBlockI18n** : data (JSON) par locale
- **ArticleCategory** : slug, label, order, isActive + i18n
- Feed : pagination côté DB, featured / highlighted / liste, filtrage par catégorie (JSONB)
- Service dédié : `getBlogFeed()`, `getArticleBySlug()` (presigned URLs pour médias)

### 5.3 Menus

- **Menu** : key (ex. primary)
- **MenuItem** : label, type (LINK, BUTTON), order, pageId ou externalUrl, buttonStyle, buttonAction
- i18n pour label par locale
- Résolution : page → urlPath pour les liens internes

### 5.4 Help Center

- **HelpCollection** → **HelpCategory** → **HelpArticle**
- Blocs par article (type + data), statut DRAFT/PUBLISHED, recherche full-text possible côté API

---

## 6. API publiques (Next.js)

- `GET /api/blog` — feed (featured, highlighted, articles, categories, pagination)
- `GET /api/blog/[slug]?locale=fr` — détail article (pour Flutter / autres clients)
- Pages publiques : `/`, `/[locale]`, `/blog`, `/blog/[slug]`, etc.
- Admin : préfixe `/admin` et routes sous `/api/admin/*` (protégées par session)

---

## 7. Déploiement

- **Next.js :** Docker (Dockerfile multi-stage), image sur ECR, ECS Fargate, ALB, port 3000
- **Front public :** CloudFront (HTTPS) → ALB → ECS
- **Variables :** injectées via task definition (DATABASE_URL, R2_*, JWT_SECRET_KEY, NEXT_PUBLIC_BASE_URL, etc.)
- **Migrations :** exécutées en CI/CD ou au démarrage du task (selon stratégie retenue)
- **Strapi :** non requis dans cette spec (tout passe par Prisma + Next.js)

---

## 8. Checklist projet from scratch (même fondamentaux)

### Backend / données
- [ ] PostgreSQL créé (ex. `arquantix_admin`)
- [ ] Projet Next.js 14 (App Router), TypeScript
- [ ] Prisma : schema (User, Session, Page, Section, SectionContent, Media, Article, ArticleI18n, ArticleBlock, ArticleBlockI18n, ArticleCategory, Menu, MenuItem, etc.), migrations
- [ ] Variables d’environnement (DATABASE_URL, R2_*, JWT/AUTH secret, NEXT_PUBLIC_BASE_URL)
- [ ] Seed : au moins un User admin + Session si besoin

### Auth
- [ ] Modèle Session + cookie `arq_admin_session`, durée 7 jours
- [ ] bcrypt pour hash password, création/suppression de session
- [ ] `getSessionFromCookie()` utilisé dans les routes admin
- [ ] Middleware ou HOF pour protéger `/admin` et `/api/admin/*`

### CMS / Contenu
- [ ] Modèle Page / Section / SectionContent (locale, status, data JSON)
- [ ] Modèle Media (key, url, mimeType, size, etc.) + intégration R2/S3 (upload + presigned URL)
- [ ] Modèle Article + i18n + blocs (types HEADING, PARAGRAPH, QUOTE, BULLET_LIST, IMAGE, VIDEO, DOCUMENT)
- [ ] Catégories d’articles (slug, i18n), liaison Article ↔ Category (slug array ou table de liaison)
- [ ] Service blog : getBlogFeed (pagination, featured, highlighted, catégorie), getArticleBySlug
- [ ] API : GET /api/blog, GET /api/blog/[slug]
- [ ] Menus : Menu, MenuItem (pageId, externalUrl), i18n, résolution d’URL

### i18n
- [ ] Locales : fr (défaut), en, it
- [ ] Tables *I18n + translationStatus
- [ ] Config centrale (supportedLocales, getLocaleOrDefault)
- [ ] Cookie ou URL pour la locale courante

### Frontend
- [ ] Tailwind + Radix (ou équivalent) + design system
- [ ] Rendu des sections CMS (mapper type → composant)
- [ ] Pages : accueil, blog (liste + détail), admin (login, pages, sections, articles, médias)
- [ ] Gestion des erreurs et états de chargement

### Mobile (optionnel)
- [ ] Projet Flutter (Dart 3.2+)
- [ ] Modèles ArticlePreview, ArticleDetail, blocs
- [ ] Client HTTP vers GET /api/blog et GET /api/blog/[slug]
- [ ] Config API_BASE_URL (localhost / 10.0.2.2 / prod)
- [ ] initializeDateFormatting('fr_FR') si usage de DateFormat avec locale
- [ ] Scripts / aliases pour lancer sur émulateur et Chrome

### Infra / Dev
- [ ] Docker Compose (optionnel) : web + postgres (+ API Python si besoin)
- [ ] .env.example avec toutes les variables documentées
- [ ] README : install, migrations, seed, dev (npm run dev -p 3001), build, variables
- [ ] Déploiement : Dockerfile Next.js, ECR, ECS, ALB, CloudFront (ou équivalent)

---

## 9. Fichiers de référence (chemins typiques)

- **Config locales :** `web/src/config/locales.ts`
- **Auth :** `web/src/lib/auth.ts`, `web/src/middleware.ts`
- **Prisma :** `web/prisma/schema.prisma`, `web/src/lib/prisma.ts`
- **Blog service :** `web/src/lib/blog/articleService.ts`, `web/src/lib/blog/readingTime.ts`
- **Storage :** `web/src/lib/storage/storageClient.ts`
- **API blog :** `web/src/app/api/blog/route.ts`, `web/src/app/api/blog/[slug]/route.ts`
- **Flutter :** `mobile/lib/`, `mobile/pubspec.yaml`, `mobile/run-android.sh`, `mobile/go.sh`

---

## 10. Versions recommandées (snapshot)

| Composant | Version |
|-----------|---------|
| Node.js | 20 LTS |
| Next.js | 14.2.x |
| React | 18.3.x |
| Prisma | 6.x |
| TypeScript | 5.x |
| Tailwind | 3.4.x |
| PostgreSQL | 15+ |
| Flutter | 3.x (Dart 3.2+) |
| Python (API) | 3.11+ |
| FastAPI | 0.109.x |

---

*Ce document sert de base pour un nouveau projet “from scratch” en gardant les mêmes choix (Next.js + Prisma + PostgreSQL + R2 + session cookie + i18n + blog avec blocs + Flutter optionnel).*
