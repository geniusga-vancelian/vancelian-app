# Architecture Arquantix

**Source de vérité pour l'architecture du projet Arquantix**

---

## Vue d'Ensemble

Arquantix est une application web monolithique modulaire avec séparation claire des responsabilités entre Frontend (Next.js), Backend (FastAPI), et Base de données (PostgreSQL).

### Principes Architecturaux

1. **Pas de CMS externe** : Pas de Strapi, pas de CMS tiers. Tout est géré en interne.
2. **Base PostgreSQL unique** : `arquantix` — SQLAlchemy/Alembic (API) et Prisma (Next) partagent la même base ; schéma `public` avec tables sans collision (pages legacy API → `legacy_json_pages`, voir migration Alembic 105).
3. **Ingestion manuelle** : Market Data via copier-coller HTML (contrôle total, reproductibilité)
4. **Backtests reproductibles** : Même logique peut être promue en production

---

## Frontend (Next.js)

### Responsabilités

- **Site vitrine** : Pages publiques, articles, projets
- **Admin UI** : Interface d'administration complète
- **API Routes** : Proxies vers FastAPI avec authentification JWT
- **Gestion de contenu** : CMS intégré via Prisma (pas de Strapi)

### Technologies

- **Framework** : Next.js 14.2.0 (App Router)
- **UI** : Tailwind CSS + shadcn/ui (Radix UI)
- **Charts** : Recharts
- **ORM** : Prisma 6.19.1
- **Auth** : Sessions cookies + JWT pour backend

### Structure

```
web/src/
├── app/                    # App Router
│   ├── admin/             # Pages admin
│   │   ├── market-data/   # Import Market Data
│   │   ├── backtests/     # Backtest Builder
│   │   └── emails/        # Email Builder
│   ├── api/               # API Routes (proxies)
│   └── (public)/          # Pages publiques
└── components/            # Composants React réutilisables
```

### Flux d'Authentification

1. User login → `/api/admin/login` → Crée session Prisma
2. Session cookie → `arq_admin_session` (httpOnly)
3. API Route proxy → `getSessionFromCookie()` → Extrait `userEmail`
4. JWT signing → `jwt.sign({ sub: userEmail })` → Token Bearer
5. FastAPI → `Depends(get_current_user)` → Valide JWT

---

## Backend (FastAPI)

### Responsabilités

- **REST API** : Endpoints pour toutes les fonctionnalités
- **Business Logic** : Logique métier (backtests, ingestion, emails)
- **Data Validation** : Pydantic schemas
- **Database Access** : SQLAlchemy ORM

### Technologies

- **Framework** : FastAPI 0.109.0
- **ORM** : SQLAlchemy 2.0.25
- **Migrations** : Alembic 1.13.1
- **Auth** : JWT (python-jose)

### Structure

```
api/
├── main.py                # Point d'entrée FastAPI
├── database.py            # Modèles SQLAlchemy
├── auth.py                # Authentification JWT
├── services/              # Modules métier
│   ├── market_data/       # Market Data ingestion
│   │   ├── routes.py      # Endpoints
│   │   ├── schemas.py     # Pydantic models
│   │   ├── yahoo_client.py      # Client Yahoo Finance (URL/CSV)
│   │   └── yahoo_html_parser.py  # Parser HTML table
│   ├── backtest/          # Backtest engine
│   │   ├── routes.py      # Endpoints
│   │   ├── engine.py      # Logique de backtesting
│   │   └── repository.py # Accès DB
│   ├── ai_email/          # Email Builder
│   └── diagnostics/       # Health checks
└── alembic/               # Migrations DB
```

### Modules Principaux

#### Market Data Service

- **Provider unique** : Yahoo Finance
- **Méthodes d'ingestion** :
  1. URL Yahoo Finance → Parse URL → Download CSV/JSON
  2. CSV upload → Parse CSV
  3. HTML table paste → Parse HTML (méthode principale)
- **Sécurité** : Validation, preflight checks, upsert safe

#### Backtest Service

- **Instruments** : Uniquement `provider='yahoo'` et `is_active='true'`
- **Logique** : Open-to-open convention, weekend trading rules
- **Métriques** : Sharpe, Calmar, Max Drawdown, etc.

---

## Base de Données (PostgreSQL)

### Base unique `arquantix`

**Backend (Alembic / SQLAlchemy)** — extraits :
- `market_data_*`, `backtest_*`, `pe_*`, `persons`, `registration_*`, etc.
- `legacy_json_pages` : anciennes pages JSON servies par l’API (legacy) ; le CMS vitrine utilise la table Prisma `pages`.

**CMS (Prisma / Next.js)** — extraits :
- `users`, `sessions`, `pages`, `sections`, `section_contents`, `media`, `articles`, `help_*`, `emails`, etc.

**Schéma** : `public` pour l’ensemble.

### Coexistence Alembic + Prisma

- Alembic est la source de vérité pour les migrations **métier** (tables SQLAlchemy).
- Prisma gère les migrations **CMS** ; les tables ne se chevauchent pas (sauf historique résolu par 105).
- Vérification : `make doctor-db` (même `DATABASE_URL` / même nom de base API + web).

---

## Pourquoi Yahoo HTML Ingestion ?

### Choix Intentionnel (pas un hack)

1. **Rate Limiting** : Yahoo Finance limite les requêtes API. HTML copier-coller évite ces limites.
2. **Reproductibilité** : Les données collées sont exactement ce que l'utilisateur voit. Pas de surprise.
3. **Contrôle manuel** : L'utilisateur choisit exactement quelle période importer.
4. **Robustesse** : Pas de dépendance à des APIs externes instables.

### Sécurité de l'Ingestion

- **Preflight check** : Détecte les overlaps avant import
- **Delta-only mode** : N'importe que les nouvelles dates
- **Overwrite mode** : Remplace les données existantes (avec confirmation)
- **Validation** : Parse robuste avec gestion d'erreurs

---

## Flux de Données

### Market Data Ingestion

```
User (Admin UI)
  ↓
Paste HTML table → /admin/market-data
  ↓
POST /api/market-data/yahoo/ingest-html-table (Next.js proxy)
  ↓
JWT Auth → FastAPI
  ↓
Parse HTML → Extract OHLCV bars
  ↓
Preflight check → Detect overlaps
  ↓
User choice → Delta-only / Overwrite / Abort
  ↓
Upsert bars → market_data_bars_d1
  ↓
Return summary → Chart preview
```

### Backtest Execution

```
User (Admin UI)
  ↓
Select instruments → /admin/backtests
  ↓
POST /api/backtests/run (Next.js proxy)
  ↓
JWT Auth → FastAPI
  ↓
Load bars → market_data_bars_d1
  ↓
Run backtest → Calculate NAV, metrics
  ↓
Store results → backtest_runs, backtest_metrics
  ↓
Return results → Display charts
```

---

## Contraintes Importantes

### Ne PAS Casser

1. **Open-to-open convention** : Les backtests utilisent `open` (prix d'ouverture)
2. **weekend_tradable** : Stocké comme STRING "true"/"false" (pas boolean)
3. **Unique constraint** : `(instrument_id, date)` dans `market_data_bars_d1`
4. **Provider filtering** : Backtests uniquement `provider='yahoo'`

### Ne PAS Ajouter

1. **Nouveaux providers** : Yahoo Finance uniquement
2. **CMS externe** : Pas de Strapi, pas de CMS tiers
3. **Auto-migration destructive** : Toujours demander confirmation avant drop/truncate

---

## Évolutivité

### Actuel

- Ingestion manuelle (contrôle total)
- Backtests synchrones (petits univers)
- Single instance (pas de scaling)

### Futures Possibilités

- Ingestion automatique (si nécessaire)
- Backtests asynchrones (grands univers)
- Multi-instance (si scaling nécessaire)

**Important** : Toute évolution doit respecter les contraintes existantes et être documentée.

---

---

## Architecture Base de Données

### Base active

| Base | Rôle | Technologie | Config |
|---|---|---|---|
| **`arquantix`** | Métier + CMS dans une seule base | SQLAlchemy + Prisma | `api/.env*`, `web/.env*` (`DATABASE_URL` identique) |

### Noms dépréciés (post–phase 2)

| Ancien nom | Note |
|---|---|
| `arquantix_quant` | Remplacé par `arquantix` après fusion |
| `arquantix_admin` | Idem |

### Répartition logique dans `arquantix`

- **Métier** : Portfolio Engine, custody, ledger, market data, backtests, registration, persons, etc.
- **CMS** : pages (Prisma), sections, articles, help, menus, media, users/sessions admin, emails builder
- **Legacy API pages** : table `legacy_json_pages` (pas `pages`)

### Diagnostic endpoint

`GET /api/diagnostics/db-status` retourne :
- database name, host, port
- alembic migration version
- row counts des tables cles

### Règles

1. FastAPI et Next.js utilisent **le même nom de base** (`arquantix` en local typique).
2. Nouvelles tables **métier** : migration Alembic + modèle SQLAlchemy.
3. Nouvelles tables **CMS** : migration Prisma.
4. Éviter tout nouveau nom de table en conflit entre les deux ORM ; en cas de doute, préfixer ou documenter.

---

**Dernière mise à jour :** 2026-04-01 (unification base unique)

