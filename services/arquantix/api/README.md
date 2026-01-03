# Arquantix API (FastAPI)

API REST pour Arquantix, similaire à l'architecture Vancelian.

## 🚀 Démarrage

### Avec Docker Compose

```bash
# Depuis la racine du repo
make -f Makefile.arquantix arquantix-up

# Ou directement
docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-api
```

L'API sera accessible sur: http://localhost:8001

### Développement Local

```bash
cd services/arquantix/api

# Installer les dépendances
pip install -r requirements.txt

# Démarrer l'API
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

## 📚 Documentation

Voir `docs/arquantix/` pour la documentation complète.

---

**Dernière mise à jour:** 2026-01-01


