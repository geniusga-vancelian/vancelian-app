# Audit Architecture Backend & Base de données — Vue Architecte

**Date :** 2026-02-18  
**Périmètre :** Arquantix — Backend (FastAPI), Base de données, Intégration Web

---

## 1. Synthèse exécutive

L’architecture actuelle repose sur **deux bases PostgreSQL distinctes** et **deux backends** (FastAPI + Next.js API Routes) qui se chevauchent partiellement. On observe une **duplication de concepts** (pages, articles/news), des **sources de vérité multiples** et une **séparation des responsabilités floue**.

| Critère | Évaluation | Commentaire |
|---------|------------|-------------|
| Cohérence des modèles | ⚠️ Moyen | Duplication Page, News vs Article |
| Séparation des bases | ✅ Correct | arquantix_quant vs arquantix_admin |
| Couche service API | ⚠️ Moyen | Logique dans main.py, routers hétérogènes |
| Migrations | ⚠️ À surveiller | Alembic + Prisma en parallèle |
| Intégrité référentielle | ⚠️ Moyen | JSON, FK manquantes (bundle_id, etc.) |

---

## 2. Vue d’ensemble des bases de données

### 2.1 Topologie

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         arquantix-db (PostgreSQL 15, port 5443)                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  arquantix_quant (API FastAPI)              arquantix_admin (Web Prisma)        │
│  ═══════════════════════════════            ═══════════════════════════════     │
│                                                                                 │
│  CMS / Vitrine (legacy)                     CMS / Vitrine (actif)              │
│  ├── global_settings                        ├── pages (slug, urlPath, template) │
│  ├── pages (slug+locale, sections_json)     ├── sections → section_contents     │
│  ├── news (déprécié)                        ├── media                            │
│  ├── contact_submissions                    ├── menu_items, menus               │
│  └── admin_users                            │                                    │
│                                             Blog / Articles                      │
│  Quant / Finance                            ├── articles, article_blocks         │
│  ├── market_data_instruments                ├── article_i18n, article_block_i18n │
│  ├── market_data_bars_d1                    ├── article_categories               │
│  ├── bundles, bundle_components             ├── article_projects                │
│  ├── backtest_runs, backtest_*              │                                    │
│  ├── field_definitions                      Help Center                         │
│  │                                          ├── help_collections                │
│  Persons / Onboarding                       ├── help_categories                  │
│  ├── persons (profile_json JSONB)           ├── help_articles, help_article_*   │
│  ├── audit_events                           │                                    │
│  ├── documents                              Auth / Users                         │
│  ├── jurisdiction_configs                   ├── users (cuid)                     │
│  │                                          ├── sessions                         │
│  Chatbot / IA                               │                                    │
│  ├── chatbot_sessions                      Email                                │
│  ├── chatbot_profiles                       ├── emails, email_i18n               │
│  ├── chatbot_conversation_turns             ├── email_modules                    │
│  ├── chatbot_audit_events                   ├── email_template_entities          │
│  ├── chatbot_portfolio_proposals            │                                    │
│  └── chatbot_prompt_versions                Autres                               │
│                                             ├── app_settings                    │
│                                             ├── translation_logs                │
│                                             └── projects, project_i18n           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Flux de données par domaine

| Domaine | Source de vérité | Consommateur |
|---------|------------------|--------------|
| Pages CMS | arquantix_admin (Prisma) | Web via getPageSections() |
| Articles / Blog | arquantix_admin (Prisma) | Web via /api/blog, /blog/[slug] |
| Contact | arquantix_quant (API) | Web via api.submitContact() |
| Global settings | arquantix_quant (API) | Web api.getGlobal() — usage limité |
| News | arquantix_quant (API) | Déprécié, non utilisé |
| Market data | arquantix_quant | API /api/market-data |
| Backtest | arquantix_quant | API /api/backtests |
| Persons | arquantix_quant | API /api/persons |
| Chatbot | arquantix_quant | API /api/chatbot |

---

## 3. Audit Backend (FastAPI)

### 3.1 Structure des routes

```
main.py (monolithique)
├── /auth/login
├── /public/* (global, pages, news, contact)
├── /admin/* (global, pages, news, contact-submissions, uploads, translate)
└── Routers inclus (sans préfixe commun)
    ├── /api/diagnostics
    ├── /api/market-data
    ├── /api/backtests
    ├── /api/bundles
    ├── /api/ai/*
    ├── /api/persons
    ├── /api/jurisdiction-configs
    ├── /api/field-definitions
    ├── /api/chatbot
    ├── /api/finance/strategy-chat
    └── /api/admin/migrations
```

**Problèmes :**

1. **Incohérence de préfixes** : `/public/`, `/admin/` vs `/api/` selon les modules.
2. **Routes vitrine dans main.py** : logique CMS (pages, news) mélangée avec auth, alors que le Web utilise Prisma pour les pages.
3. **Pas de versioning** : aucune convention `/v1/` ou `/v2/`.

### 3.2 Modèles SQLAlchemy (database.py)

| Modèle | Tables | Remarques |
|--------|--------|-----------|
| GlobalSettings | 1 | Singleton implicite |
| Page | 1 | Dupliqué avec Web (structure différente) |
| News | 1 | Déprécié, orphelin |
| ContactSubmission | 1 | Utilisé par Web |
| AdminUser | 1 | Auth API (JWT) |
| MarketData* | 4 | Bien structuré, FK cohérentes |
| Backtest* | 4 | bundle_id en String(36) sans FK |
| Person, AuditEvent, Document | 3 | JSONB, GIN index |
| JurisdictionConfig | 1 | UniqueConstraint OK |
| Chatbot* | 6 | Modèle cohérent |

**Points faibles :**

- **Boolean en String** : `is_active`, `weekend_tradable`, `allow_weekend_trading` stockés en `"true"`/`"false"` au lieu de `BOOLEAN`.
- **bundle_id** : `BacktestRun.bundle_id` en String sans FK vers `bundles.id`.
- **created_by_user_id** : Integer sans FK (isolation volontaire).
- **Pas de soft delete** : Suppressions physiques uniquement.

### 3.3 Migrations Alembic

- 26 fichiers de migration, historique complexe (merge heads, réparations).
- Migrations manuelles (`apply_migration_013.py`, etc.) en plus d’Alembic.
- Risque de divergence entre `database.py` et l’état réel de la base.

---

## 4. Audit Base de données (Prisma — arquantix_admin)

### 4.1 Modèles principaux

| Domaine | Modèles | Qualité |
|---------|---------|---------|
| Auth | User, Session | ✅ Cuid, FK |
| CMS | Page, Section, SectionContent | ✅ Structure normalisée |
| Blog | Article, ArticleI18n, ArticleBlock, ArticleBlockI18n | ✅ i18n complet |
| Help | HelpCollection, HelpCategory, HelpArticle, HelpArticleBlock | ✅ Hiérarchie claire |
| Media | Media | ✅ Centralisé |
| Projects | Project, ProjectI18n, ProjectMedia | ✅ |
| Menu | Menu, MenuItem, MenuI18n, MenuItemI18n | ✅ |
| Email | Email, EmailModule, EmailTemplateEntity | ✅ Modulaire |

### 4.2 Points faibles

1. **Article.categorySlugs** : JSON array, pas de FK vers ArticleCategory. Filtrage par raw SQL (`@>`).
2. **Article.galleryMediaIds** : JSON array, pas de table de liaison.
3. **Article.documents** : JSON `[{mediaId, title}]`, pas de modèle dédié.
4. **HelpArticleBlock** : `locale` sur le bloc (différent d’ArticleBlock + ArticleBlockI18n).
5. **AppSettings.supported_locales** : JSON string, pas de table de config.
6. **Pas d’index GIN** sur `category_slugs` pour les requêtes de filtrage.

### 4.3 Cohérence des clés

- **Article** : `cuid` (string).
- **API** : `Integer` auto-increment pour la plupart des tables.
- Pas de synchronisation entre les deux bases.

---

## 5. Problèmes d’architecture identifiés

### 5.1 Duplication et sources de vérité multiples

| Concept | API (arquantix_quant) | Web (arquantix_admin) | Conflit |
|---------|------------------------|------------------------|---------|
| Pages | Page (slug+locale, sections_json) | Page (slug, sections relationnelles) | Structure différente, deux modèles |
| Articles | News (markdown, déprécié) | Article (blocs, i18n) | Un seul utilisé (Article) |
| Admin auth | AdminUser (API JWT) | User + Session (Prisma, cookie) | Deux systèmes d’auth |

### 5.2 Flux hybrides

- **Contact** : Web → API `/public/contact` → arquantix_quant.
- **Pages** : Web → Prisma → arquantix_admin (pas d’appel API pour le CMS).
- **Global** : `api.getGlobal()` existe mais `/app/page.tsx` (home) n’utilise que Prisma.
- **News** : API disponible mais dépréciée ; le blog utilise Article (Prisma).

### 5.3 Configuration des URLs

- `api.ts` : `NEXT_PUBLIC_API_URL` (défaut 8011).
- `backend.ts` : `BACKEND_URL` (défaut 8000).
- Risque de confusion et d’appels vers le mauvais port.

---

## 6. Recommandations

### Priorité haute

1. **Clarifier la stratégie CMS**
   - Choisir une seule source pour les pages : soit tout Prisma (arquantix_admin), soit tout API.
   - Si Prisma : déprécier ou supprimer les endpoints `/public/pages`, `/admin/pages` de l’API.

2. **Unifier la configuration backend**
   - Une seule variable (`NEXT_PUBLIC_BACKEND_URL` ou `BACKEND_URL`) pour l’API FastAPI.
   - Supprimer ou aligner `NEXT_PUBLIC_API_URL` avec le port réel (8000).

3. **Documenter les flux**
   - Matrice : domaine → base → API/Prisma → consommateurs.
   - Mettre à jour ARCHITECTURE.md avec ce schéma.

### Priorité moyenne

4. **Normaliser les types en base**
   - Remplacer les colonnes `String` "true"/"false" par `BOOLEAN` (migration Alembic).

5. **Renforcer l’intégrité référentielle**
   - `BacktestRun.bundle_id` : FK vers `bundles.id` ou champ dédié documenté.
   - `Article.categorySlugs` : envisager une table `article_category_links` si les performances le justifient.

6. **Index de performance**
   - Index GIN sur `articles.category_slugs` pour les requêtes `@>`.

### Priorité basse

7. **Versioning API**
   - Introduire `/api/v1/` pour les routes métier.

8. **Refactoriser main.py**
   - Extraire les routes vitrine dans un router dédié (`/public`, `/admin`).

9. **Consolidation des migrations**
   - Nettoyer l’historique Alembic (squash si possible).
   - Éviter les scripts de migration manuels en dehors d’Alembic.

---

## 7. Schéma des dépendances (résumé)

```
                    ┌──────────────────┐
                    │   Next.js Web    │
                    │   (port 3000)    │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────┐  ┌───────────────┐  ┌─────────────────┐
│ Next.js API     │  │ Prisma        │  │ FastAPI         │
│ Routes          │  │ (direct)      │  │ (port 8000)     │
│ /api/*          │  │               │  │                 │
└────────┬────────┘  └───────┬───────┘  └────────┬────────┘
         │                   │                   │
         │                   │                   │
         ▼                   ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│              arquantix_admin (Prisma)                    │
│  pages, sections, articles, help, media, menus, etc.    │
└─────────────────────────────────────────────────────────┘
                                    │
                                    │  contact, persons,
                                    │  backtest, market-data,
         ┌──────────────────────────┘  chatbot, etc.
         ▼
┌─────────────────────────────────────────────────────────┐
│              arquantix_quant (SQLAlchemy)                │
│  contact_submissions, persons, backtest, market_data,   │
│  chatbot, admin_users, news (deprecated), pages (legacy) │
└─────────────────────────────────────────────────────────┘
```

---

**Dernière mise à jour :** 2026-02-18
