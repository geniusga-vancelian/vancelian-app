# Architecture - Arquantix Vitrine + CMS

**Date:** 2026-02-18  
**Status:** 🚧 En cours de développement

---

## TL;DR

Architecture avec Next.js (frontend) + FastAPI (API quant) + PostgreSQL. Le blog utilise le modèle **Article** (Prisma, base `arquantix_admin`). L’API News (base `arquantix_quant`) est **dépréciée** — le front consomme `/api/blog` et `/blog/[slug]`.

---

## Ce qui est vrai aujourd'hui

### Architecture Locale (Docker Compose)

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│                  (arquantix-network)                     │
│                                                          │
│  ┌──────────────┐         ┌──────────────┐             │
│  │  Next.js Web │────────▶│  Strapi CMS  │             │
│  │  (Port 3001) │         │  (Port 1338) │             │
│  └──────────────┘         └──────┬───────┘             │
│                                   │                      │
│                          ┌────────▼────────┐            │
│                          │  PostgreSQL     │            │
│                          │  (Port 5433)    │            │
│                          └─────────────────┘            │
└─────────────────────────────────────────────────────────┘
```

### Flux de Données

1. **Utilisateur** → `http://localhost:3001`
2. **Next.js** récupère les données depuis **Strapi API** (`http://arquantix-cms:1338/api`)
3. **Strapi** interroge **PostgreSQL** pour les données
4. **Next.js** affiche le contenu rendu

### Composants

#### 1. Next.js Web (services/arquantix/web/)

- **Technologie:** Next.js 14 (App Router), TypeScript, Tailwind CSS
- **Port:** 3001 (dev local), 3000 (container)
- **Responsabilités:**
  - Rendu des pages (SSR/SSG)
  - Intégration avec Strapi API
  - Gestion du routing i18n (FR/EN)
  - UI/UX premium sobre

#### 2. Strapi CMS (services/arquantix/cms/)

- **Technologie:** Strapi 4.18, Node.js 20, PostgreSQL
- **Port:** 1338
- **Responsabilités:**
  - Gestion du contenu (Content Types)
  - API REST pour le contenu
  - Administration du contenu (Admin UI)
  - Internationalisation (i18n FR/EN)

#### 3. PostgreSQL (arquantix-db)

- **Technologie:** PostgreSQL 15 (Alpine)
- **Port:** 5443 (host), 5432 (container)
- **Bases :**
  - `arquantix_admin` : CMS (pages, sections, articles, help, media) — utilisée par Next.js
  - `arquantix_quant` : API quant (market data, backtest, news déprécié)

### Blog / Articles

Le blog public utilise **uniquement** le modèle Article (Prisma, base `arquantix_admin`) :

- **Feed :** `GET /api/blog?locale=fr&page=1&category=...` → pagination côté base
- **Détail :** `GET /blog/[slug]` → Article + ArticleBlock + ArticleBlockI18n
- **Service :** `web/src/lib/blog/articleService.ts`

L’API News (`/public/news/*`, base `arquantix_quant`) est **dépréciée** et non utilisée par le front.

### Ports et Chemins

| Service      | Port (Host) | Port (Container) | URL                          |
|--------------|-------------|------------------|------------------------------|
| Next.js Web  | 3001        | 3000             | http://localhost:3001        |
| Strapi CMS   | 1338        | 1338             | http://localhost:1338        |
| Strapi Admin | 1338        | 1338             | http://localhost:1338/admin  |
| PostgreSQL   | 5433        | 5432             | localhost:5433               |

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
| `http://localhost:1338/api/*`     | GET/POST| API Strapi (endpoints CMS)    |
| `http://localhost:1338/admin`     | GET     | Admin UI Strapi                |

### Observabilité

**Logs:**
- Docker Compose: `docker compose -f docker-compose.arquantix.yml logs -f`
- Logs spécifiques: `docker compose -f docker-compose.arquantix.yml logs -f arquantix-web`
- Logs Strapi: Accessibles via Admin UI ou logs Docker

**Health Checks:**
- Next.js: Pas de healthcheck spécifique (retourne 200 sur n'importe quelle route)
- Strapi: `/api/health` (si configuré)
- PostgreSQL: Healthcheck Docker configuré (pg_isready)

---

## À vérifier quand ça casse

### Problèmes de Port

Si les ports sont déjà utilisés:
```bash
# Vérifier les ports
lsof -i :3001
lsof -i :1338
lsof -i :5433

# Ajuster dans docker-compose.arquantix.yml ou .env.arquantix
```

### Problèmes de Connexion Next.js → Strapi

1. Vérifier que Strapi est démarré: `docker ps | grep arquantix-cms`
2. Vérifier les variables d'environnement: `NEXT_PUBLIC_STRAPI_URL`, `NEXT_PUBLIC_STRAPI_API_URL`
3. Vérifier le réseau Docker: Les services doivent être sur le même réseau (`arquantix-network`)

### Problèmes de Connexion Strapi → PostgreSQL

1. Vérifier que PostgreSQL est démarré: `docker ps | grep arquantix-cms-db`
2. Vérifier les variables d'environnement: `DATABASE_HOST`, `DATABASE_NAME`, etc.
3. Vérifier les logs: `docker compose -f docker-compose.arquantix.yml logs arquantix-cms-db`

### Problèmes de Build

1. **Next.js build échoue:**
   - Vérifier les dépendances: `npm install` dans `services/arquantix/web/`
   - Vérifier TypeScript: `npm run lint`
   - Vérifier les variables d'environnement

2. **Strapi build échoue:**
   - Vérifier les dépendances: `npm install` dans `services/arquantix/cms/`
   - Vérifier la configuration: `config/database.js`, etc.

---

## Architecture Future (Déploiement)

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
│  RDS PostgreSQL │  (Optionnel: si Strapi en prod)
└─────────────────┘
```

**Note:** Strapi reste en développement local pour le moment. Déploiement Strapi optionnel (voir DEPLOYMENT.md).

---

**Dernière mise à jour:** 2026-01-01

