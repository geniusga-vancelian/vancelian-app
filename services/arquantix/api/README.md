# Arquantix API (FastAPI)

API REST pour Arquantix, similaire à l'architecture Vancelian.

## 🚀 Démarrage

### Mode par défaut (recommandé) : API en Docker

L’image inclut les **bibliothèques système** pour **WeasyPrint** (PDF relevés IBAN). Les templates sont dans `templates/pdf/` et sont copiés dans l’image (`COPY . .` dans le `Dockerfile`).

**Depuis la racine du dépôt** — stack complète (Postgres, Redis, **API**, CMS, Next) :

```bash
make -f Makefile.arquantix arquantix-up
# API : http://127.0.0.1:8000  —  Next (conteneur) : WEB_PORT du .env.arquantix
```

Équivalent :

```bash
docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d
```

Le service **`arquantix-api`** joint Postgres (`arquantix-db:5432`) et Redis (`arquantix-redis`) sur le réseau compose. Le BFF Next (conteneur `arquantix-web`) utilise par défaut **`BACKEND_URL=http://arquantix-api:8000`**.

**Next sur la machine hôte** (`npm run dev`) : dans `services/arquantix/web/.env.local`, fixer  
`BACKEND_URL=http://127.0.0.1:8000` pour joindre l’API exposée sur le port hôte.

### Image seule (CI / run manuel)

```bash
docker build -t arquantix-api:local -f services/arquantix/api/Dockerfile services/arquantix/api
```

Sur **GitHub Actions**, le workflow **« Arquantix API (FastAPI) - Build & push ECR »** (`.github/workflows/arquantix-api-deploy.yml`) build et pousse cette image.

### Option développement : uvicorn sur l’hôte (sans garantie PDF sur macOS)

Itération rapide sur le code Python ; **WeasyPrint** peut échouer sur macOS sans stack Homebrew complète.

```bash
cd services/arquantix/api
pip install -r requirements.txt
# macOS (tentative) : brew install pango cairo gdk-pixbuf libffi
uvicorn main:app --reload --port 8000
```

## 📋 Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/global` - Données globales (branding, socials, SEO)
- `GET /api/pages?locale=fr&slug=home` - Pages
- `GET /api/pages/{id}` - Page par ID
- `GET /api/news?locale=fr&limit=10` - Liste des news
- `GET /api/news/{id}` - News par ID
- `GET /api/news/slug/{slug}?locale=fr` - News par slug
- `POST /api/contact-submissions` - Créer une soumission de contact

## 🗄️ Base de Données

Actuellement, l'API utilise un stockage en mémoire (MVP).

Pour la production, connecter à PostgreSQL (comme `ganopa-bot`).

## 🔐 JWT `sub` (identité utilisateur)

**Invariant (sessions utilisateur access + refresh) :**

```text
JWT.sub MUST always be "au:<admin_users.id>"
Any other format is invalid and rejected.
```

Toute régression (émission ou acceptation d’un `sub` e-mail, numérique seul, etc.) casse le contrat d’identité. Voir `services/auth/jwt_user_claims.py` et `services/auth/jwt_subject_resolution.py`.

**Runtime :** les `sub` non canoniques déclenchent des logs structurés `jwt_sub_rejected` (et `logger.error` si le sujet ressemble à un ancien e-mail). Compteur process : `get_jwt_sub_resolution_metrics()["jwt_sub_rejected_count"]`.

**Post-déploiement (48–72 h) :** surveiller les 401, les échecs `/auth/refresh` et les pics de login (clients encore en vieux token).

## 🧪 Tests

Les dépendances de test (pytest + pytest-asyncio) sont **séparées** de
`requirements.txt` pour garder l'image Docker de production minimale.
Elles vivent dans `requirements-dev.txt`.

### Setup local (uvicorn hôte)

```bash
cd services/arquantix/api
pip install -r requirements.txt -r requirements-dev.txt
python -m pytest tests/ -v
```

### Setup dans le conteneur API

```bash
docker exec arquantixrecovery-arquantix-api-1 \
  pip install -r /app/requirements-dev.txt

docker exec -w /app arquantixrecovery-arquantix-api-1 \
  python3 -m pytest tests/ -v
```

### Tests Palier 2 D.2 — Mémoire long-terme assistance

```bash
docker exec -w /app arquantixrecovery-arquantix-api-1 \
  python3 -m pytest \
    tests/test_assistance_memory_unit.py \
    tests/test_assistance_memory_integration.py -v
```

→ **81 tests** (64 unit + 17 integration), ~30 s.

Doc complète : `docs/arquantix/MEMORY.md`.

## 📚 Documentation

Voir `docs/arquantix/` pour la documentation complète.

---

**Dernière mise à jour:** 2026-05-02


