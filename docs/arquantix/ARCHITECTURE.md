# Architecture — Arquantix (Next.js + API)

> **Stack active (2026) :** Next.js (site + BFF + **CMS admin Prisma**), FastAPI, PostgreSQL, Redis. **Aucun Strapi** en runtime — l’ancien CMS n’entre plus dans le périmètre opérationnel.

**Date:** 2026-02-18  
**Status:** 🚧 En cours de développement

---

## TL;DR

Architecture avec Next.js (frontend / BFF, port hôte **typique 3000** via `WEB_PORT`) + FastAPI (**8000** dans le conteneur, hôte via `API_PORT`) + PostgreSQL (hôte **typique 5443** via `DB_PORT`) + Redis. Le blog utilise le modèle **Article** (Prisma). L’API News (base `arquantix_quant`) est **dépréciée** — le front consomme `/api/blog` et `/blog/[slug]`.

---

## Ce qui est vrai aujourd'hui

### Architecture locale (Docker Compose — typ. recovery)

```
┌─────────────────────────────────────────────────────────┐
│              Réseau Compose (ex. recovery)               │
│                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Next.js  │───▶│ FastAPI  │───▶│ Postgres │          │
│  │  :WEB    │    │  :8000   │    │  :5432   │          │
│  └────┬─────┘    └────┬─────┘    └──────────┘          │
│       │               │                                  │
│       └───────────────┴──────── Redis (cache / tasks)   │
└─────────────────────────────────────────────────────────┘
```

*(Ports **hôte** : `WEB_PORT` / `API_PORT` / `DB_PORT` dans `.env.arquantix` — en pratique souvent **3000** / **8000** / **5443**. Le **3001** n’est pas le port de référence du web.)*

### Flux de données (aperçu)

1. Navigateur → Next.js (ex. `http://localhost:${WEB_PORT}`)
2. Next.js (serveur) → FastAPI (`arquantix-api:8000`) pour les routes proxy / BFF
3. Next.js (Prisma) et FastAPI → **PostgreSQL** (`arquantix-db`)
4. Redis pour besoins cache / auth selon configuration

### Composants

#### 1. Next.js Web (services/arquantix/web/)

- **Technologie:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Port hôte:** `WEB_PORT` (`.env.arquantix`) — **référence locale 3000** (mappé sur le port d’écoute du conteneur web, souvent aussi 3000)
- **Responsabilités:**
  - Rendu des pages (SSR/SSG)
  - Prisma (CMS : pages, sections, menus, articles, etc.) et BFF vers FastAPI
  - Gestion du routing i18n (FR/EN)
  - UI/UX premium sobre

#### 2. FastAPI (arquantix-api)

- **Rôle :** API métier (auth, custody, mobile, PDF, market data, etc.)
- **Port conteneur :** **8000** ; port hôte : `API_PORT` (`.env.arquantix`, souvent **8000**)

#### 3. PostgreSQL (arquantix-db)

- **Technologie:** PostgreSQL 15 (Alpine)
- **Port hôte :** **`DB_PORT`** (souvent **5443**) ; **port conteneur :** **5432**
- **Bases :**
  - `arquantix_admin` : CMS (pages, sections, articles, help, media) — utilisée par Next.js
  - `arquantix_quant` : API quant (market data, backtest, news déprécié)

### CMS admin (Pages, Menus, Footer, structure)

- **Surface admin** (`/admin/...`, Next.js) : édition des **pages** (contenu), **menu primaire**, **footer** global, et bloc **Structure du site** (arborescence `Page`).
- Données en base **`arquantix_admin`** via **Prisma** — pas de headless CMS tiers dans la stack active.
- **Lot 4 — menu ↔ arbre** : l’arborescence `Page` est la **source de vérité structurelle** ; le menu est une **couche navigation**. Onglet Menus : analyse des écarts (`GET /api/admin/menus/primary/structure-alignment`) et synchronisation **manuelle** (`POST` même route : ajout des liens manquants pour les pages `showInNav` hors home, réordonnancement optionnel). **Pas** de menu 100 % auto, **pas** de suppression des CTA / liens externes, **pas** de dérivation silencieuse.

### CMS — hiérarchie `Page` (lots 1–3, 2026-04)

- **Champs** (additifs) : `parentId`, `sortOrder`, `pageRole` (`STANDARD` | `HOME` | `PROJECTS_HUB`), `showInNav`, `isSystemPage`. Le `template` (ex. `vault_builder`) reste la vérité du rendu ; `pageRole` décrit le rôle structurel dans l’arbre.
- **API** : `GET /api/admin/site-tree` (auth admin) — arbre en **lecture seule**. Édition parent / ordre : `PATCH /api/admin/pages/[slug]/structure` (validations serveur : cycles, parent vault interdit, accueil / hub projets à la racine).
- **Menu primaire** : reste une couche distincte ; alignement **volontaire** via l’action admin (lot 4), pas de sync en tâche de fond.
- **Backfill migration** : `home` → `pageRole = HOME`, `isSystemPage = true` ; slug `projects` → `PROJECTS_HUB` ; pages `template = vault_builder` (hors `home` / `projects`) → `parentId` vers la page `slug = projects` **si** elle existe. Sinon les vaults restent à la racine de l’arbre jusqu’édition manuelle.
- **UX admin** : pas de glisser-déposer sur la structure dans le périmètre actuel ; édition par formulaire (parent + ordre + monter/descendre parmi frères).
- **Règle structurelle vault (lot 3)** : une page `template = vault_builder` **ne peut pas** être choisie comme parent ; un vault peut en revanche être enfant d’un hub non-vault (ex. `projects`). Aucune autre inférence métier sur les offres.

### Blog / Articles

Le blog public utilise **uniquement** le modèle Article (Prisma, base `arquantix_admin`) :

- **Feed :** `GET /api/blog?locale=fr&page=1&category=...` → pagination côté base
- **Détail :** `GET /blog/[slug]` → Article + ArticleBlock + ArticleBlockI18n
- **Service :** `web/src/lib/blog/articleService.ts`

L’API News (`/public/news/*`, base `arquantix_quant`) est **dépréciée** et non utilisée par le front.

### Ports et Chemins

| Service      | Port (hôte, typique) | Port (conteneur) | URL (exemple)                          |
|--------------|----------------------|------------------|----------------------------------------|
| Next.js Web  | **3000** (`WEB_PORT`) | 3000             | `http://localhost:${WEB_PORT}`         |
| FastAPI      | **8000** (`API_PORT`) | **8000**         | `http://127.0.0.1:${API_PORT}`         |
| PostgreSQL   | **5443** (`DB_PORT`)  | **5432**         | `localhost:${DB_PORT}`                 |
| Redis        | `REDIS_PORT`         | 6379             | (souvent interne au réseau Compose)    |

### Chemins API

| Endpoint                          | Méthode | Description                    |
|-----------------------------------|---------|--------------------------------|
| `/`                               | GET     | Redirige vers `/fr`            |
| `/fr`                             | GET     | Page d'accueil (FR)            |
| `/en`                             | GET     | Page d'accueil (EN)            |
| `/blog`                           | GET     | Liste des articles (feed)       |
| `/blog/[slug]`                    | GET     | Article de blog (détail)       |
| `/api/blog`                      | GET     | API feed (featured, highlighted, pagination) |
| `/fr/contact`                     | GET     | Formulaire de contact (FR)     |
| `/en/contact`                     | GET     | Formulaire de contact (EN)     |
| OpenAPI FastAPI                   | GET     | `/docs` sur l’API              |

### Observabilité

**Logs:**
- Docker : `docker compose … logs -f` (voir `.env.arquantix` pour projet / fichier)
- Service web : `… logs -f arquantix-web`

**Health Checks:**
- API : `GET /health` sur le port `API_PORT`
- PostgreSQL : healthcheck Docker (`pg_isready`)

---

## À vérifier quand ça casse

### Problèmes de Port

Si les ports sont déjà utilisés:
```bash
# Vérifier les ports (adapter selon .env.arquantix)
lsof -nP -iTCP:${WEB_PORT:-3000} -sTCP:LISTEN
lsof -nP -iTCP:${API_PORT:-8000} -sTCP:LISTEN
lsof -nP -iTCP:${DB_PORT:-5443} -sTCP:LISTEN
```

### Problèmes de connexion Next.js → API (BFF)

1. Vérifier que `arquantix-api` tourne : `docker ps` (service `arquantix-api`)
2. Vérifier `BACKEND_URL` / `BACKEND_API_URL` dans l’env du conteneur web (réseau compose : `http://arquantix-api:8000`)
3. Tester : `curl -sS http://127.0.0.1:${API_PORT:-8000}/health`

### Problèmes de connexion API / Prisma → PostgreSQL

1. Vérifier `arquantix-db` : `docker compose … ps arquantix-db`
2. Vérifier `DATABASE_URL` (même `DB_NAME` partout — voir `.env.arquantix`)
3. Logs : `docker compose … logs arquantix-db` / `arquantix-api`

### Problèmes de build

1. **Next.js build échoue :** dépendances dans `services/arquantix/web/`, `npm run lint`, variables d’environnement.
2. **API :** image Docker `services/arquantix/api` — voir Dockerfile et logs conteneur.

---

## Architecture Future (Déploiement)

> Section **vision / hors détail local** — ne pas la confondre avec les ports dev ci-dessus.

### Architecture Production (prévue)

```
┌─────────────────┐
│   CloudFront    │  (CDN + HTTPS)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ALB (AWS)      │  (Load Balancer)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ECS Fargate    │
│  ┌───────────┐  │
│  │ Next.js   │  │  (Site Vitrine)
│  └───────────┘  │
└─────────────────┘

┌─────────────────┐
│  RDS PostgreSQL │
└─────────────────┘
```

**Note :** déploiement selon pipeline ops (voir [DEPLOYMENT.md](./DEPLOYMENT.md)).

### Résolution locale Vault (web + mobile)

Le contenu éditorial Vault (`section` `vault_builder_v1`) est sélectionné par **`resolveVaultSectionContent`** (`services/arquantix/web/src/lib/cms/resolveVaultSectionContent.ts`). Même fonction pour :

- le rendu web détail offre (`getExclusiveOfferVaultPayload`) ;
- `GET /api/mobile/flutter/vaults` (liste, param optionnel `locale`) ;
- `GET /api/mobile/flutter/vaults/[slug]` (détail, `locale` + `status`).

**Fallback (mode `either`, page publique web)** : locale demandée (pub → brouillon) → locale par défaut du site (pub → brouillon) → toute locale (pub → brouillon). **Modes liste/détail mobile (statut strict)** : mêmes paliers de locale, sans mélanger les statuts ; dernier recours : statut demandé sur une autre locale.

**Titres / descriptions d’offre (page)** : `resolvePageSeoFields` / `resolvePageTitleDescriptionWithFallback` — `PageI18n` pour la locale demandée, puis locale par défaut, puis champs racine `Page` (aligné sur le reste du CMS).

### Admin Vault Builder — édition multi-locale (Lot 3)

- **Sélecteur de langue** : barre `AdminEditingLocaleBar` (même pattern que `/admin/pages`), synchronisée avec l’URL `?slug=…&editingLocale=fr|en|it`.
- **Chargement** : `GET /api/admin/vaults/[slug]?locale=` — contenu édité = `SectionContent` **DRAFT** ; la réponse inclut aussi `publishedConfig` (snapshot publié) et `localeVaultLayers` (état brouillon/publié par langue).
- **Sauvegarde brouillon** : `PUT` met à jour **uniquement le DRAFT** pour la locale (modules vault) + `PageI18n` si titre/description envoyés.
- **Publication explicite** : `POST /api/admin/vaults/[slug]/publish-locale` avec `{ locale }` — copie le DRAFT → **PUBLISHED** pour cette langue seule.
- **Complétude** : badges réutilisant `computePageLocaleCompleteness` (même grille que le CMS pages).
- **Duplication FR → EN / IT** : `POST /api/admin/vaults/[slug]/copy-locale` — copie `PageI18n` depuis le FR ; copie le JSON vault en **brouillon uniquement** pour la langue cible (ne modifie pas le publié de cette langue).
- **Aperçu** : liens vers `/{locale}/projects/{slug}` — rendu public : publié prioritaire, sinon brouillon (`resolveVaultSectionContent` mode `either`).

---

**Dernière mise à jour:** 2026-04-16

