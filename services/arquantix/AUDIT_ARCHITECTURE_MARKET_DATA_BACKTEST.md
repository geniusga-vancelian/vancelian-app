# AUDIT ARCHITECTURE ARQUANTIX
## Intégration Market Data (Alpha Vantage) & Backtest Multi-Assets

**Date** : 2026-01-09  
**Objectif** : Comprendre l'architecture existante pour intégrer proprement deux nouveaux modules :
1. Module Market Data (Alpha Vantage API)
2. Module Backtest multi-assets (D1 open-to-open)

**Contrainte** : Audit uniquement, aucune modification de code.

---

## A) STRUCTURE REPO & APPS

### A.1. Frontend Next.js

**Chemin** : `/web/`

**Structure** :
```
web/
├── src/
│   ├── app/                    # Next.js App Router
│   │   ├── admin/              # Routes admin (protégées)
│   │   │   ├── ai/email/       # Email Builder UI
│   │   │   ├── emails/         # Liste emails
│   │   │   └── ...
│   │   └── api/                # API Routes Next.js (server-side)
│   │       ├── admin/          # Endpoints admin (auth via cookie)
│   │       └── ai/             # Endpoints AI (proxy vers FastAPI)
│   ├── components/             # Composants React
│   │   ├── ai-email/           # Composants Email Builder
│   │   └── ...
│   ├── lib/                    # Utilitaires
│   │   ├── auth.ts             # Session management (cookies)
│   │   ├── backend.ts          # Helper pour URLs FastAPI
│   │   ├── prisma.ts           # Client Prisma
│   │   └── ...
│   └── middleware.ts           # Middleware Next.js (redirects, auth check)
├── prisma/
│   ├── schema.prisma           # Schéma Prisma (ORM)
│   └── migrations/             # Migrations Prisma
└── package.json
```

**Entry Point** : `web/src/app/layout.tsx` (App Router)

**Port** : 3000 (dev), configuré via `npm run dev`

**Source** : `web/package.json`, `web/src/app/`

### A.2. Backend FastAPI

**Chemin** : `/api/`

**Structure** :
```
api/
├── main.py                     # Entry point FastAPI
├── auth.py                     # JWT authentication
├── database.py                  # SQLAlchemy models + session
├── schemas.py                   # Pydantic schemas (request/response)
├── alembic/                    # Migrations Alembic
│   ├── env.py
│   └── versions/
├── services/                   # Modules métier
│   ├── ai_email/               # Module Email Builder
│   │   ├── routes.py           # FastAPI router
│   │   ├── schemas.py          # Pydantic EmailSpec
│   │   ├── agent.py            # OpenAI composition
│   │   └── ...
│   └── translate.py            # Module Auto-Translate
├── requirements.txt
└── alembic.ini
```

**Entry Point** : `api/main.py` (ligne 40: `app = FastAPI(...)`)

**Port** : 8000 (dev), configuré via `uvicorn main:app --reload --port 8000`

**Router Pattern** : Les modules exposent un `APIRouter` inclus dans `main.py` :
```python
from services.ai_email.routes import router as ai_email_router
app.include_router(ai_email_router)  # Préfixe: /api/ai
```

**Source** : `api/main.py` lignes 630-635

### A.3. Base de Données

**Type** : PostgreSQL

**ORM Backend** : SQLAlchemy (déclaratif)
- **Fichier** : `api/database.py`
- **Session** : `SessionLocal` (sessionmaker)
- **Models** : Classes héritant de `Base` (declarative_base)
- **Dependency** : `get_db()` (générateur pour injection FastAPI)

**ORM Frontend** : Prisma
- **Fichier** : `web/prisma/schema.prisma`
- **Client** : `web/src/lib/prisma.ts`
- **Migrations** : `web/prisma/migrations/` (SQL)

**Migrations Backend** : Alembic
- **Config** : `api/alembic.ini`
- **Env** : `api/alembic/env.py`
- **Versions** : `api/alembic/versions/`
- **Commande** : `alembic revision --autogenerate -m "message"` puis `alembic upgrade head`

**Migrations Frontend** : Prisma Migrate
- **Commande** : `npm run db:migrate` (alias pour `prisma migrate dev`)

**Connexion** :
- **Backend** : `DATABASE_URL` (env var) → `api/database.py` ligne 13-16
- **Frontend** : `DATABASE_URL` (env var) → `web/prisma/schema.prisma` ligne 7

**⚠️ IMPORTANT** : Deux bases de données distinctes peuvent être utilisées :
- Backend FastAPI : `arquantix` (port 5433 par défaut)
- Frontend Next.js : `arquantix_admin` (port 5443 par défaut)

**Source** : `api/database.py`, `web/prisma/schema.prisma`, `api/alembic/env.py`

---

## B) CONFIGURATION & ENV VARS

### B.1. Backend FastAPI

**Chargement** : `python-dotenv` via `load_dotenv()` dans `main.py` ligne 20

**Pattern** : Accès direct via `os.getenv()` (pas de Pydantic Settings centralisé)

**Variables existantes** :
```python
# api/main.py, api/auth.py, api/database.py, api/services/...
DATABASE_URL          # PostgreSQL connection string
JWT_SECRET_KEY        # Secret pour JWT (défaut: "your-secret-key-change-in-production")
CORS_ORIGINS          # Liste d'origins autorisées (défaut: localhost:3000,3001,3011)
STORAGE_BACKEND       # "local" par défaut
MEDIA_BASE_URL        # URL base pour media (défaut: localhost:8011)
OPENAI_API_KEY        # Clé OpenAI (requis pour Email Builder + Translate)
OPENAI_MODEL          # Modèle OpenAI (défaut: "gpt-4o-mini")
OPENAI_BASE_URL       # URL base OpenAI (défaut: api.openai.com/v1)
PORT                  # Port FastAPI (défaut: 8000)
```

**Exemples d'utilisation** :
- `api/main.py` ligne 49 : `os.getenv("CORS_ORIGINS", "...")`
- `api/auth.py` ligne 14 : `os.getenv("JWT_SECRET_KEY", "...")`
- `api/database.py` ligne 13 : `os.getenv("DATABASE_URL", "...")`
- `api/services/translate.py` ligne 11 : `os.getenv("OPENAI_API_KEY")`

**⚠️ GAP IDENTIFIÉ** : Pas de fichier `settings.py` centralisé avec Pydantic BaseSettings. Chaque module lit directement `os.getenv()`.

**Recommandation pour Market Data** :
```python
# Dans api/services/market_data/__init__.py ou api/services/market_data/config.py
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
MARKET_DATA_PROVIDER = os.getenv("MARKET_DATA_PROVIDER", "alphavantage")
```

**Source** : `api/main.py`, `api/auth.py`, `api/database.py`, `api/services/translate.py`

### B.2. Frontend Next.js

**Chargement** : Automatique via Next.js (fichier `.env` à la racine de `web/`)

**Pattern** : `process.env.NOM_VAR` (server-side uniquement sauf si préfixé `NEXT_PUBLIC_`)

**Variables existantes** :
```typescript
// web/src/lib/backend.ts, web/src/lib/auth.ts, web/src/app/api/...
DATABASE_URL              # PostgreSQL pour Prisma
AUTH_SECRET               # Secret pour sessions (alternative à JWT_SECRET_KEY)
JWT_SECRET_KEY            # Secret pour JWT (utilisé pour proxy FastAPI)
BACKEND_URL               # URL FastAPI backend (server-side)
NEXT_PUBLIC_BACKEND_URL   # URL FastAPI backend (client-side, optionnel)
OPENAI_API_KEY            # Clé OpenAI (server-side uniquement, jamais exposée)
NODE_ENV                  # "development" | "production"
```

**Helper Backend URL** : `web/src/lib/backend.ts`
- `getBackendBaseUrl()` : Récupère `BACKEND_URL` ou `NEXT_PUBLIC_BACKEND_URL` ou `http://localhost:8000`
- `buildBackendUrl(path)` : Construit URL complète pour FastAPI

**Exemples d'utilisation** :
- `web/src/lib/backend.ts` ligne 12 : `process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'`
- `web/src/app/api/ai/email/compose-ugg/route.ts` ligne 37 : `process.env.JWT_SECRET_KEY || process.env.AUTH_SECRET || 'dev-secret-change-me'`

**Recommandation pour Market Data** :
```typescript
// Dans web/src/lib/market-data/config.ts (si nécessaire côté frontend)
// Sinon, uniquement backend (pas besoin de NEXT_PUBLIC_)
```

**Source** : `web/src/lib/backend.ts`, `web/src/app/api/ai/email/compose-ugg/route.ts`

### B.3. Recommandations pour Ajouter ALPHAVANTAGE_API_KEY

**Backend** :
1. Ajouter dans `api/services/market_data/config.py` (nouveau fichier) :
   ```python
   import os
   ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
   MARKET_DATA_PROVIDER = os.getenv("MARKET_DATA_PROVIDER", "alphavantage")
   ```
2. Vérifier présence dans `api/services/market_data/routes.py` (endpoints) :
   ```python
   if not ALPHAVANTAGE_API_KEY:
       raise HTTPException(status_code=500, detail="ALPHAVANTAGE_API_KEY not configured")
   ```

**Frontend** : Pas nécessaire (API key jamais exposée, appels via proxy Next.js)

**Documentation** : Ajouter dans `web/README_ADMIN.md` section "Environment Variables" (ligne ~59)

**Source** : Pattern identique à `OPENAI_API_KEY` dans `api/services/translate.py` ligne 11-29

---

## C) AUTH / PERMISSIONS

### C.1. Système d'Auth Admin

**Frontend** : Session-based avec cookies HTTP-only
- **Fichier** : `web/src/lib/auth.ts`
- **Cookie** : `arq_admin_session` (httpOnly, secure en prod, sameSite: 'lax')
- **Durée** : 7 jours
- **Storage** : Table `Session` dans Prisma (PostgreSQL)
- **Validation** : `getSessionFromCookie()` dans chaque API route

**Backend** : JWT Bearer Token
- **Fichier** : `api/auth.py`
- **Secret** : `JWT_SECRET_KEY` (env var)
- **Algorithme** : HS256
- **Durée** : 24 heures (ACCESS_TOKEN_EXPIRE_MINUTES)
- **Validation** : `get_current_user()` (dependency FastAPI)

**Login Flow** :
1. Frontend : `POST /api/admin/login` → crée session Prisma → set cookie
2. Backend : `POST /auth/login` → retourne JWT token (pour appels FastAPI directs)

**Source** : `web/src/lib/auth.ts`, `api/auth.py`, `web/src/app/api/admin/login/route.ts`

### C.2. Protection des Endpoints Backend

**Pattern** : Dependency Injection FastAPI avec `Depends(get_current_user)`

**Exemple** :
```python
# api/main.py ligne 192
@app.get("/admin/global")
def get_global_admin(
    current_user: AdminUser = Depends(get_current_user),  # ← Protection
    db: Session = Depends(get_db)
):
    ...
```

**OAuth2 Scheme** : `OAuth2PasswordBearer(tokenUrl="/auth/login")` dans `api/auth.py` ligne 18

**Headers requis** : `Authorization: Bearer <JWT_TOKEN>`

**Source** : `api/auth.py` lignes 50-71, `api/main.py` lignes 192-210

### C.3. Protection des Endpoints Frontend (Next.js API Routes)

**Pattern** : Vérification session cookie dans chaque route

**Exemple** :
```typescript
// web/src/app/api/admin/pages/route.ts ligne 20
export async function GET() {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  // ... reste du code
}
```

**Middleware** : `web/src/middleware.ts` vérifie présence cookie pour routes `/admin/*` (sauf `/admin/login`)

**Source** : `web/src/middleware.ts` lignes 30-54, `web/src/app/api/admin/pages/route.ts`

### C.4. Communication Frontend → Backend

**Pattern** : Proxy via Next.js API Routes (recommandé)

**Flow** :
1. Frontend React → `fetch('/api/ai/email/compose-ugg')`
2. Next.js API Route → `fetch(buildBackendUrl('/api/ai/email/compose-ugg'), { headers: { Authorization: Bearer <JWT> } })`
3. FastAPI Backend → valide JWT via `get_current_user()`

**Exemple** : `web/src/app/api/ai/email/compose-ugg/route.ts`
- Ligne 24 : `buildBackendUrl('/api/ai/email/compose-ugg')`
- Lignes 36-42 : Création JWT depuis session cookie
- Ligne 48 : Header `Authorization: Bearer ${token}`

**CORS** : Configuré dans FastAPI (`api/main.py` lignes 47-53)
- `CORS_ORIGINS` env var (défaut: localhost:3000,3001,3011)
- `allow_credentials=True`

**⚠️ RECOMMANDATION** : Utiliser le pattern proxy Next.js (comme Email Builder) plutôt que appels directs depuis le client. Avantages :
- API keys jamais exposées au client
- CORS géré automatiquement
- Session cookie → JWT conversion centralisée

**Source** : `web/src/app/api/ai/email/compose-ugg/route.ts`, `api/main.py` lignes 47-53

### C.5. Protection pour Market Data & Backtest

**Recommandation** : Suivre le même pattern que Email Builder

**Backend FastAPI** :
```python
# api/services/market_data/routes.py
from auth import get_current_user, AdminUser

router = APIRouter(prefix="/api/market-data", tags=["market-data"])

@router.get("/symbols/{symbol}/quote")
async def get_quote(
    symbol: str,
    current_user: AdminUser = Depends(get_current_user),  # ← Protection
    db: Session = Depends(get_db)
):
    ...
```

**Frontend Next.js** :
```typescript
// web/src/app/api/market-data/quote/route.ts
export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  // Proxy vers FastAPI avec JWT
  const backendUrl = buildBackendUrl('/api/market-data/symbols/...')
  const token = jwt.sign({ sub: session.userEmail }, jwtSecret, { expiresIn: '24h' })
  // ... fetch avec Authorization header
}
```

**Source** : Pattern identique à `api/services/ai_email/routes.py` et `web/src/app/api/ai/email/compose-ugg/route.ts`

---

## D) MODULES EXISTANTS SIMILAIRES

### D.1. Email Builder (Module de Référence)

**Backend** : `api/services/ai_email/`

**Structure** :
```
api/services/ai_email/
├── routes.py              # FastAPI router (préfixe: /api/ai)
├── schemas.py             # Pydantic EmailSpec
├── schemas_ugg.py         # Pydantic EmailSpecUGG (template unique)
├── agent.py               # OpenAI composition (génère JSON)
├── agent_ugg.py           # OpenAI composition pour template UGG
├── render.py               # MJML build + compile
├── templates_mjml/         # Templates MJML hardcodés
│   ├── arquantix_ugg_v1.mjml
│   └── render_ugg.py
└── blocks/                 # Renderers de blocs MJML
```

**Router** : `api/services/ai_email/routes.py` ligne 36
```python
router = APIRouter(prefix="/api/ai", tags=["ai-email"])
```

**Endpoints** :
- `GET /api/ai/email/templates` (ligne 39)
- `POST /api/ai/email/compose` (ligne 72)
- `POST /api/ai/email/compose-ugg` (ligne 364)

**Inclusion dans main.py** : Ligne 634-635
```python
from services.ai_email.routes import router as ai_email_router
app.include_router(ai_email_router)
```

**Frontend** : `web/src/app/api/ai/email/`
- `compose-ugg/route.ts` : Proxy vers FastAPI avec JWT
- `templates/route.ts` : Liste templates (retourne uniquement arquantix_ugg_v1)

**Validation** :
- **Backend** : Pydantic (`EmailSpecUGG` avec `extra="forbid"`)
- **Frontend** : Zod (`composeEmailUGGSchema` dans `compose-ugg/route.ts` ligne 7)

**Source** : `api/services/ai_email/routes.py`, `web/src/app/api/ai/email/compose-ugg/route.ts`

### D.2. Auto-Translate

**Backend** : `api/services/translate.py`

**Structure** :
```python
# api/services/translate.py
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def translate_page_payload(source_page: Dict[str, Any], target_locale: str) -> Dict[str, Any]:
    # Appel OpenAI API
    # Retourne payload traduit
```

**Endpoint** : `api/main.py` ligne 523
```python
@app.post("/admin/pages/{page_id}/translate")
def translate_page(
    page_id: int,
    request: TranslateRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Utilise translate_page_payload()
```

**Frontend** : `web/src/app/api/admin/translate/email/route.ts`
- Traduction EmailSpec (contenu uniquement, pas structure)
- Utilise `translateText()` depuis `web/src/lib/translate/translateText.ts`

**Pattern** : Service Python standalone (pas de router dédié), appelé depuis endpoint dans `main.py`

**Source** : `api/services/translate.py`, `api/main.py` lignes 519-610, `web/src/app/api/admin/translate/email/route.ts`

### D.3. Conventions Identifiées

**Routing Backend** :
- Préfixe : `/api/<module>` (ex: `/api/ai`, `/api/market-data`)
- Tags : Nom du module (ex: `tags=["ai-email"]`, `tags=["market-data"]`)
- Router : `APIRouter(prefix="/api/...", tags=["..."])`
- Inclusion : `app.include_router(router)` dans `main.py`

**Routing Frontend** :
- Chemin : `/api/<module>/<action>/route.ts`
- Proxy pattern : Next.js route → FastAPI avec JWT
- Validation : Zod schema avant proxy

**Services** :
- Dossier : `api/services/<module_name>/`
- Structure : `routes.py` (router), `schemas.py` (Pydantic), logique métier dans fichiers séparés

**Documentation** :
- Backend : `api/docs/` (markdown)
- Frontend : `web/docs/` (markdown)
- Email Builder : `docs/email/` (documentation complète)

**Logging/Errors** :
- **Backend** : `print()` / `console.log()` (pas de logger structuré identifié)
- **Frontend** : `console.error()` dans catch blocks
- **Errors** : `HTTPException` (FastAPI), `NextResponse.json({ error: ... })` (Next.js)

**Validation** :
- **Backend** : Pydantic (`BaseModel` avec validators)
- **Frontend** : Zod (`z.object({ ... })`)

**Source** : `api/services/ai_email/routes.py`, `web/src/app/api/ai/email/compose-ugg/route.ts`, `api/services/translate.py`

### D.4. Meilleur Modèle à Recopier

**✅ RECOMMANDATION : Email Builder (`api/services/ai_email/`)**

**Raisons** :
1. Structure complète : router, schemas, services séparés
2. Pattern proxy Next.js bien documenté
3. Validation Pydantic + Zod
4. Gestion d'API keys externes (OpenAI)
5. Documentation complète dans `docs/email/`

**Structure à reproduire** :
```
api/services/market_data/
├── routes.py              # FastAPI router
├── schemas.py             # Pydantic (QuoteRequest, QuoteResponse, etc.)
├── client.py              # Client Alpha Vantage (httpx)
└── __init__.py

api/services/backtest/
├── routes.py              # FastAPI router
├── schemas.py             # Pydantic (BacktestRequest, BacktestResponse)
├── engine.py              # Moteur de backtest
├── strategies/            # Stratégies (ex: moving_average.py)
└── __init__.py
```

**Source** : `api/services/ai_email/`

---

## E) OBSERVABILITÉ & JOBS

### E.1. Background Jobs

**❌ AUCUN SYSTÈME IDENTIFIÉ**

**Recherche effectuée** :
- `celery`, `rq`, `scheduler`, `cron`, `background`, `job`, `task` : 0 résultat dans codebase
- `api/requirements.txt` : Pas de Celery/RQ
- `web/package.json` : Pas de scheduler

**Implications** :
- Pas de système de jobs asynchrones
- Pas de queue pour tâches longues
- Pas de scheduler pour tâches récurrentes

**Source** : Recherche grep, `api/requirements.txt`, `web/package.json`

### E.2. Scripts CLI Internes

**Backend** : `api/scripts/`
- `seed.py` : Seed database
- `archive_old_templates.py` : Archive templates

**Frontend** : `web/scripts/`
- `seed-email-v6-defaults.ts` : Seed email modules/templates
- `sync-r2-media.ts` : Sync media vers Cloudflare R2
- Autres scripts de seed/check

**Pattern** : Scripts standalone exécutés manuellement (`tsx scripts/...` ou `python scripts/...`)

**Source** : `api/scripts/`, `web/scripts/`

### E.3. Endpoints "Internal"

**❌ AUCUN IDENTIFIÉ**

Tous les endpoints sont soit :
- Public (`/public/*`)
- Admin protégés (`/admin/*`, `/api/ai/*`)

**Source** : `api/main.py`, `api/services/ai_email/routes.py`

### E.4. Recommandations pour Backfill & Update Quotidien

**Option 1 : Scripts CLI (Pattern Existant)**

**Backfill Historique** :
```python
# api/scripts/backfill_market_data.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.market_data.client import AlphaVantageClient
from database import SessionLocal, MarketDataQuote
from datetime import datetime, timedelta

def backfill_symbol(symbol: str, start_date: datetime, end_date: datetime):
    db = SessionLocal()
    client = AlphaVantageClient()
    # ... boucle sur dates, fetch, insert
```

**Update Quotidien** :
```python
# api/scripts/daily_market_data_update.py
# Exécuté via cron ou ECS scheduled task
```

**Avantages** :
- Simple, pas de nouvelle dépendance
- Aligné avec pattern existant (`api/scripts/seed.py`)

**Inconvénients** :
- Pas de monitoring/retry automatique
- Pas de queue pour gérer la charge

**Option 2 : Endpoint Admin + Cron Externe (Recommandé pour MVP)**

**Endpoint** :
```python
# api/services/market_data/routes.py
@router.post("/market-data/update/{symbol}")
async def trigger_update(
    symbol: str,
    current_user: AdminUser = Depends(get_current_user)
):
    # Fetch latest data, store in DB
    # Retourne status
```

**Cron** : ECS Scheduled Task ou cron système qui appelle l'endpoint avec JWT

**Avantages** :
- Monitoring via logs FastAPI
- Retry via ECS/cron
- Pas de nouvelle dépendance

**Option 3 : Celery (Pour Plus Tard)**

Si besoin de queue/retry avancé, ajouter Celery + Redis :
- `requirements.txt` : `celery[redis]==5.3.4`
- `api/celery_app.py` : Configuration Celery
- `api/tasks/market_data.py` : Tasks Celery

**⚠️ RECOMMANDATION MVP** : Option 2 (Endpoint + Cron externe)

**Source** : Pattern `api/scripts/seed.py`, `api/main.py` (endpoints)

---

## F) LIVRABLE FINAL

### F.1. Carte des Dossiers

```
services/arquantix/
├── api/                          # Backend FastAPI
│   ├── main.py                   # Entry point, CORS, routers
│   ├── auth.py                   # JWT auth
│   ├── database.py               # SQLAlchemy models
│   ├── schemas.py                # Pydantic schemas génériques
│   ├── alembic/                  # Migrations Alembic
│   │   ├── env.py
│   │   └── versions/
│   ├── services/                 # Modules métier
│   │   ├── ai_email/            # ✅ Module Email Builder (référence)
│   │   ├── translate.py         # ✅ Module Auto-Translate
│   │   ├── market_data/          # 🆕 À CRÉER
│   │   │   ├── routes.py
│   │   │   ├── schemas.py
│   │   │   ├── client.py
│   │   │   └── __init__.py
│   │   └── backtest/             # 🆕 À CRÉER
│   │       ├── routes.py
│   │       ├── schemas.py
│   │       ├── engine.py
│   │       ├── strategies/
│   │       └── __init__.py
│   └── scripts/                  # Scripts CLI
│       └── backfill_market_data.py  # 🆕 À CRÉER
│
└── web/                           # Frontend Next.js
    ├── src/
    │   ├── app/
    │   │   ├── admin/            # UI admin
    │   │   └── api/              # API Routes Next.js
    │   │       ├── admin/        # Endpoints admin (cookie auth)
    │   │       ├── ai/           # ✅ Proxy Email Builder
    │   │       ├── market-data/  # 🆕 À CRÉER (proxy)
    │   │       └── backtest/     # 🆕 À CRÉER (proxy)
    │   ├── lib/
    │   │   ├── auth.ts          # Session management
    │   │   ├── backend.ts        # Helper URLs FastAPI
    │   │   └── prisma.ts        # Client Prisma
    │   └── middleware.ts        # Redirects, auth check
    ├── prisma/
    │   ├── schema.prisma        # Schéma Prisma
    │   └── migrations/          # Migrations Prisma
    └── scripts/                  # Scripts CLI
        └── seed-market-data.ts  # 🆕 Optionnel
```

### F.2. Conventions à Respecter

#### Naming
- **Modules** : `snake_case` (ex: `market_data`, `ai_email`)
- **Routers** : `routes.py` dans chaque module
- **Schemas** : `schemas.py` (Pydantic) ou `schema.ts` (Zod)
- **Endpoints** : RESTful (`GET /api/market-data/symbols/{symbol}/quote`)

#### Routers
- **Préfixe** : `/api/<module>` (ex: `/api/market-data`)
- **Tags** : Nom du module (ex: `tags=["market-data"]`)
- **Inclusion** : `app.include_router(router)` dans `main.py` après les autres routers

#### Settings
- **Pattern** : `os.getenv("VAR_NAME", "default")` directement dans le code
- **Pas de Pydantic Settings** : Suivre pattern existant (pas de `pydantic-settings` centralisé)

#### Env Vars
- **Backend** : `.env` à la racine de `api/` (chargé via `load_dotenv()`)
- **Frontend** : `.env` à la racine de `web/` (chargé automatiquement par Next.js)
- **Documentation** : Ajouter dans `web/README_ADMIN.md` section "Environment Variables"

#### Auth
- **Backend** : `Depends(get_current_user)` sur tous les endpoints admin
- **Frontend** : `getSessionFromCookie()` dans chaque API route
- **Proxy** : Créer JWT depuis session cookie avant appel FastAPI

#### Fetch
- **Pattern** : Proxy Next.js → FastAPI avec JWT
- **Helper** : `buildBackendUrl(path)` depuis `web/src/lib/backend.ts`
- **Headers** : `Authorization: Bearer <JWT>` + `Content-Type: application/json`

### F.3. Gaps/Risques Actuels

#### Gaps Identifiés

1. **Pas de Settings Centralisé**
   - **Risque** : Duplication de `os.getenv()` dans plusieurs fichiers
   - **Impact** : Faible (pattern simple, mais pas scalable)
   - **Recommandation** : Garder pattern actuel pour cohérence

2. **Pas de Logger Structuré**
   - **Risque** : Logs difficiles à analyser en production
   - **Impact** : Moyen
   - **Recommandation** : Ajouter `structlog` ou `loguru` plus tard (pas critique MVP)

3. **Pas de Background Jobs**
   - **Risque** : Backfill/update quotidien nécessite scripts externes
   - **Impact** : Faible (solutions existent : ECS scheduled tasks, cron)
   - **Recommandation** : Endpoints admin + cron externe (Option 2 section E.4)

4. **CORS Configuré mais Large**
   - **Risque** : `allow_origins=["*"]` en dev (OK), mais vérifier en prod
   - **Impact** : Faible (dev uniquement)
   - **Recommandation** : Vérifier `CORS_ORIGINS` en production

5. **Deux Bases de Données Potentielles**
   - **Risque** : Confusion entre `arquantix` (backend) et `arquantix_admin` (frontend)
   - **Impact** : Moyen
   - **Recommandation** : Documenter clairement quelle DB pour quel usage

#### Risques Sécurité

1. **JWT Secret Key Default**
   - **Risque** : `"your-secret-key-change-in-production"` en défaut
   - **Impact** : Critique en production
   - **Recommandation** : Forcer `JWT_SECRET_KEY` en production (validation au startup)

2. **API Keys dans .env**
   - **Risque** : `.env` commité par erreur
   - **Impact** : Critique
   - **Recommandation** : Vérifier `.gitignore` (déjà fait normalement)

3. **CORS Large en Dev**
   - **Risque** : `allow_origins=["*"]` en dev
   - **Impact** : Faible (dev uniquement)
   - **Recommandation** : Restreindre en production

**Source** : `api/auth.py` ligne 14, `api/main.py` ligne 49, `api/database.py` ligne 13

### F.4. Proposition d'Intégration Market Data

#### Où Mettre le Code

**Backend** :
```
api/services/market_data/
├── __init__.py
├── routes.py              # FastAPI router (préfixe: /api/market-data)
├── schemas.py             # Pydantic (QuoteRequest, QuoteResponse, etc.)
├── client.py              # Client Alpha Vantage (httpx)
└── config.py              # Config (ALPHAVANTAGE_API_KEY)
```

**Frontend** :
```
web/src/app/api/market-data/
├── quote/route.ts         # Proxy GET /api/market-data/symbols/{symbol}/quote
├── search/route.ts        # Proxy GET /api/market-data/search?keywords=...
└── history/route.ts       # Proxy GET /api/market-data/symbols/{symbol}/history
```

**Database** :
- **Backend** : Nouveau modèle SQLAlchemy dans `api/database.py` :
  ```python
  class MarketDataQuote(Base):
      __tablename__ = "market_data_quotes"
      id = Column(Integer, primary_key=True)
      symbol = Column(String, nullable=False, index=True)
      date = Column(DateTime, nullable=False, index=True)
      open = Column(Numeric)
      high = Column(Numeric)
      low = Column(Numeric)
      close = Column(Numeric)
      volume = Column(BigInteger)
      created_at = Column(DateTime, server_default=func.now())
      __table_args__ = (UniqueConstraint('symbol', 'date'),)
  ```
- **Frontend** : Optionnel (si besoin UI admin) : Ajouter dans `web/prisma/schema.prisma`

**Source** : Pattern `api/services/ai_email/`, `api/database.py`

#### Comment Configurer Env Vars

**Backend** (`api/.env`) :
```bash
# Market Data
ALPHAVANTAGE_API_KEY=your-api-key-here
MARKET_DATA_PROVIDER=alphavantage  # Optionnel, défaut: "alphavantage"
```

**Code** (`api/services/market_data/config.py`) :
```python
import os
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
MARKET_DATA_PROVIDER = os.getenv("MARKET_DATA_PROVIDER", "alphavantage")
```

**Frontend** : Pas nécessaire (proxy Next.js)

**Documentation** : Ajouter dans `web/README_ADMIN.md` section "Environment Variables" (après ligne 113)

**Source** : Pattern `api/services/translate.py` ligne 11-13

#### Comment Protéger Endpoints

**Backend** :
```python
# api/services/market_data/routes.py
from auth import get_current_user, AdminUser
from database import get_db

router = APIRouter(prefix="/api/market-data", tags=["market-data"])

@router.get("/symbols/{symbol}/quote")
async def get_quote(
    symbol: str,
    current_user: AdminUser = Depends(get_current_user),  # ← Protection
    db: Session = Depends(get_db)
):
    if not ALPHAVANTAGE_API_KEY:
        raise HTTPException(status_code=500, detail="ALPHAVANTAGE_API_KEY not configured")
    # ... fetch Alpha Vantage, store in DB, return
```

**Frontend** :
```typescript
// web/src/app/api/market-data/quote/route.ts
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'
import jwt from 'jsonwebtoken'

export async function GET(request: NextRequest) {
  const session = await getSessionFromCookie()
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }
  
  const { searchParams } = new URL(request.url)
  const symbol = searchParams.get('symbol')
  
  const backendUrl = buildBackendUrl(`/api/market-data/symbols/${symbol}/quote`)
  const jwtSecret = process.env.JWT_SECRET_KEY || process.env.AUTH_SECRET || 'dev-secret-change-me'
  const token = jwt.sign({ sub: session.userEmail }, jwtSecret, { expiresIn: '24h' })
  
  const response = await fetch(backendUrl, {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  })
  
  return NextResponse.json(await response.json())
}
```

**Source** : Pattern identique à `api/services/ai_email/routes.py` et `web/src/app/api/ai/email/compose-ugg/route.ts`

#### Comment Versionner Univers/Instruments

**Option 1 : Table SQLAlchemy (Recommandé)**

```python
# api/database.py
class MarketDataUniverse(Base):
    __tablename__ = "market_data_universes"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)  # "SP500", "NASDAQ100", etc.
    symbols = Column(JSON, nullable=False)  # ["AAPL", "MSFT", ...]
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

class MarketDataInstrument(Base):
    __tablename__ = "market_data_instruments"
    id = Column(Integer, primary_key=True)
    symbol = Column(String, nullable=False, unique=True, index=True)
    name = Column(String, nullable=True)
    exchange = Column(String, nullable=True)
    asset_type = Column(String, nullable=True)  # "stock", "etf", "crypto", etc.
    universe_id = Column(Integer, ForeignKey("market_data_universes.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

**Endpoints** :
- `GET /api/market-data/universes` : Liste univers
- `POST /api/market-data/universes` : Créer univers
- `GET /api/market-data/instruments` : Liste instruments (filtré par universe)

**Source** : Pattern similaire à `EmailModule` dans `api/database.py` ligne 134

### F.5. Proposition d'Intégration Backtest Engine

#### Où Mettre Engine/Strategies/Drivers

**Backend** :
```
api/services/backtest/
├── __init__.py
├── routes.py              # FastAPI router (préfixe: /api/backtest)
├── schemas.py             # Pydantic (BacktestRequest, BacktestResponse)
├── engine.py              # Moteur de backtest (D1 open-to-open)
├── strategies/            # Stratégies
│   ├── __init__.py
│   ├── base.py            # BaseStrategy (abstract)
│   ├── moving_average.py  # Exemple: MA crossover
│   └── momentum.py        # Exemple: Momentum
└── drivers/               # Drivers de données
    ├── __init__.py
    └── market_data.py     # Driver qui lit depuis MarketDataQuote
```

**Frontend** :
```
web/src/app/api/backtest/
├── run/route.ts           # Proxy POST /api/backtest/run
├── results/[id]/route.ts  # Proxy GET /api/backtest/results/{id}
└── strategies/route.ts    # Proxy GET /api/backtest/strategies
```

**Source** : Structure inspirée de `api/services/ai_email/blocks/` (renderers modulaires)

#### Comment Stocker Data + Résultats

**Database** :

```python
# api/database.py
class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id = Column(String, primary_key=True)  # UUID
    name = Column(String, nullable=False)
    strategy_name = Column(String, nullable=False)  # "moving_average", etc.
    strategy_params = Column(JSON, nullable=False)  # {"window": 20, ...}
    universe_id = Column(Integer, ForeignKey("market_data_universes.id"), nullable=True)
    symbols = Column(JSON, nullable=False)  # ["AAPL", "MSFT", ...]
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)  # "PENDING", "RUNNING", "COMPLETED", "FAILED"
    results = Column(JSON, nullable=True)  # {"sharpe": 1.5, "returns": [...], ...}
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    created_by_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)

class BacktestTrade(Base):
    __tablename__ = "backtest_trades"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("backtest_runs.id"), nullable=False, index=True)
    symbol = Column(String, nullable=False)
    entry_date = Column(DateTime, nullable=False)
    exit_date = Column(DateTime, nullable=True)
    entry_price = Column(Numeric, nullable=False)
    exit_price = Column(Numeric, nullable=True)
    quantity = Column(Numeric, nullable=False)
    pnl = Column(Numeric, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
```

**Data Source** : Le moteur lit depuis `MarketDataQuote` (table créée par module Market Data)

**Source** : Pattern similaire à `Email` dans `api/database.py` ligne 517

#### Comment Gérer "Validate/Publish" (Versioning)

**Option 1 : Status Field (Simple)**

```python
# api/database.py
class BacktestRun(Base):
    ...
    status = Column(String, nullable=False)  # "DRAFT", "VALIDATED", "PUBLISHED"
    validated_at = Column(DateTime, nullable=True)
    validated_by_user_id = Column(Integer, ForeignKey("admin_users.id"), nullable=True)
```

**Endpoints** :
- `POST /api/backtest/runs/{id}/validate` : Change status DRAFT → VALIDATED
- `POST /api/backtest/runs/{id}/publish` : Change status VALIDATED → PUBLISHED

**Option 2 : Versioning Explicite (Plus Complexe)**

```python
class BacktestRunVersion(Base):
    __tablename__ = "backtest_run_versions"
    id = Column(Integer, primary_key=True)
    run_id = Column(String, ForeignKey("backtest_runs.id"), nullable=False)
    version = Column(Integer, nullable=False)  # 1, 2, 3, ...
    status = Column(String, nullable=False)  # "DRAFT", "VALIDATED", "PUBLISHED"
    results = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    __table_args__ = (UniqueConstraint('run_id', 'version'),)
```

**⚠️ RECOMMANDATION MVP** : Option 1 (Status field, comme `Email.status`)

**Source** : Pattern `Email.status` dans `api/database.py` ligne 524, `EmailStatusEnum` ligne 28

### F.6. Liste d'Actions Concrètes (TODO)

#### Priorité 1 : Setup Initial

1. **Créer structure backend Market Data**
   - [ ] Créer `api/services/market_data/__init__.py`
   - [ ] Créer `api/services/market_data/config.py` (ALPHAVANTAGE_API_KEY)
   - [ ] Créer `api/services/market_data/client.py` (AlphaVantageClient avec httpx)
   - [ ] Créer `api/services/market_data/schemas.py` (Pydantic: QuoteRequest, QuoteResponse)
   - [ ] Créer `api/services/market_data/routes.py` (router FastAPI)
   - [ ] Ajouter modèle `MarketDataQuote` dans `api/database.py`
   - [ ] Créer migration Alembic : `alembic revision --autogenerate -m "add_market_data_tables"`
   - [ ] Inclure router dans `api/main.py` : `app.include_router(market_data_router)`

2. **Créer structure frontend Market Data**
   - [ ] Créer `web/src/app/api/market-data/quote/route.ts` (proxy)
   - [ ] Créer `web/src/app/api/market-data/search/route.ts` (proxy)
   - [ ] Tester proxy avec JWT (pattern identique à `compose-ugg/route.ts`)

3. **Configurer env vars**
   - [ ] Ajouter `ALPHAVANTAGE_API_KEY` dans `api/.env`
   - [ ] Documenter dans `web/README_ADMIN.md` section "Environment Variables"

#### Priorité 2 : Backtest Engine

4. **Créer structure backend Backtest**
   - [ ] Créer `api/services/backtest/__init__.py`
   - [ ] Créer `api/services/backtest/schemas.py` (Pydantic: BacktestRequest, BacktestResponse)
   - [ ] Créer `api/services/backtest/engine.py` (moteur D1 open-to-open)
   - [ ] Créer `api/services/backtest/strategies/base.py` (BaseStrategy abstract)
   - [ ] Créer `api/services/backtest/strategies/moving_average.py` (exemple)
   - [ ] Créer `api/services/backtest/drivers/market_data.py` (lit depuis MarketDataQuote)
   - [ ] Créer `api/services/backtest/routes.py` (router FastAPI)
   - [ ] Ajouter modèles `BacktestRun`, `BacktestTrade` dans `api/database.py`
   - [ ] Créer migration Alembic : `alembic revision --autogenerate -m "add_backtest_tables"`
   - [ ] Inclure router dans `api/main.py`

5. **Créer structure frontend Backtest**
   - [ ] Créer `web/src/app/api/backtest/run/route.ts` (proxy)
   - [ ] Créer `web/src/app/api/backtest/results/[id]/route.ts` (proxy)
   - [ ] Tester proxy avec JWT

#### Priorité 3 : Scripts & Jobs

6. **Scripts CLI**
   - [ ] Créer `api/scripts/backfill_market_data.py` (backfill historique)
   - [ ] Créer `api/scripts/daily_market_data_update.py` (update quotidien)
   - [ ] Documenter dans `api/README.md`

7. **Endpoints Admin pour Jobs**
   - [ ] Ajouter `POST /api/market-data/update/{symbol}` dans `routes.py` (trigger manuel)
   - [ ] Ajouter `POST /api/market-data/backfill` dans `routes.py` (trigger backfill)

#### Priorité 4 : Documentation

8. **Documentation**
   - [ ] Créer `docs/market-data/README.md` (structure similaire à `docs/email/`)
   - [ ] Créer `docs/backtest/README.md`
   - [ ] Ajouter exemples d'utilisation dans README

#### Priorité 5 : Tests & Validation

9. **Tests**
   - [ ] Tester endpoints Market Data (quote, search)
   - [ ] Tester endpoints Backtest (run, results)
   - [ ] Tester auth (JWT, session cookie)
   - [ ] Tester proxy Next.js → FastAPI

---

## RÉSUMÉ EXÉCUTIF

### Architecture Actuelle

- **Frontend** : Next.js App Router (`web/src/app/`)
- **Backend** : FastAPI (`api/main.py`)
- **DB Backend** : SQLAlchemy + Alembic (`api/database.py`, `api/alembic/`)
- **DB Frontend** : Prisma (`web/prisma/`)
- **Auth** : Session cookies (frontend) + JWT (backend)
- **Communication** : Proxy Next.js → FastAPI avec JWT

### Modules Existants (Référence)

- **Email Builder** : `api/services/ai_email/` (✅ meilleur modèle)
- **Auto-Translate** : `api/services/translate.py` (service standalone)

### Conventions Identifiées

- **Routing** : `/api/<module>` (backend), `/api/<module>/<action>/route.ts` (frontend)
- **Auth** : `Depends(get_current_user)` (backend), `getSessionFromCookie()` (frontend)
- **Validation** : Pydantic (backend), Zod (frontend)
- **Env Vars** : `os.getenv()` direct (pas de Settings centralisé)
- **Proxy** : Next.js route → FastAPI avec JWT depuis session cookie

### Gaps Identifiés

- ❌ Pas de background jobs (utiliser endpoints + cron externe)
- ⚠️ Pas de logger structuré (ajouter plus tard)
- ⚠️ Pas de Settings centralisé (garder pattern actuel pour cohérence)

### Recommandations

1. **Suivre pattern Email Builder** (`api/services/ai_email/`)
2. **Utiliser proxy Next.js** (jamais appels directs depuis client)
3. **Endpoints + Cron externe** pour backfill/update quotidien (pas Celery MVP)
4. **Status field** pour versioning backtest (comme `Email.status`)

---

**Fin du rapport d'audit**






