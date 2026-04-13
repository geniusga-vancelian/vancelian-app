# Runbook Développement — Démarrage & Debug

**Fichiers clés**: `scripts/arquantix-start.sh`, `api/.env.local`, `web/.env`, logs

---

## 1. Démarrage local

### Script principal (recommandé)

**Fichier**: `scripts/arquantix-boot.sh` (nouveau, robuste)  
**Alternative**: `scripts/arquantix-start.sh` (ancien, toujours disponible)

**Usage** (recommandé):
```bash
cd /path/to/arquantix
./scripts/arquantix-boot.sh
# ou
make boot
```

**One-click boot**: Le script `arquantix-boot.sh` gère automatiquement:
- Vérification Docker Desktop
- Démarrage/health check de `arquantix-db` (port 5443)
- Validation des fichiers `.env` (pas de zitadel-db/5434)
- Gestion des conflits de ports (3000, 8000)
- PID files et logs (`/tmp/arquantix-*.pid`, `/tmp/arquantix-*.log`)
- Vérifications finales (health endpoints)

**Scripts disponibles**:
- `make boot` ou `./scripts/arquantix-boot.sh` - Démarre tout (DB + API + Web)
- `make stop` ou `./scripts/arquantix-stop.sh` - Arrête API + Web
- `make stop-db` ou `./scripts/arquantix-stop.sh --db` - Arrête tout + DB
- `make status` ou `./scripts/arquantix-status.sh` - Affiche le status

**Ancien script** (toujours disponible):
```bash
./scripts/arquantix-start.sh
```

**Étapes**:
1. Vérification Docker (doit être démarré)
2. Vérification/start container `arquantix-db` (health=healthy, port=5443)
3. Vérification configs `.env` (DATABASE_URL doit pointer vers `localhost:5443`)
4. Démarrage API FastAPI (`python3 -m uvicorn main:app --reload --port 8000`)
5. Démarrage Web Next.js (`npm run dev`)

**PIDs stockés**: `/tmp/arquantix-api.pid`, `/tmp/arquantix-web.pid`

**Logs**: `/tmp/arquantix-api.log`, `/tmp/arquantix-web.log`

**Référence**: `scripts/arquantix-start.sh:1-210`

### Commandes manuelles

**API**:
```bash
cd api
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload > /tmp/arquantix-api.log 2>&1 &
echo $! > /tmp/arquantix-api.pid
```

**Web**:
```bash
cd web
npm run dev > /tmp/arquantix-web.log 2>&1 &
echo $! > /tmp/arquantix-web.pid
```

**Arrêt**:
```bash
kill $(cat /tmp/arquantix-api.pid)
kill $(cat /tmp/arquantix-web.pid)
```

---

## 2. Ports

### Ports utilisés

- **3000**: Next.js Web (frontend)
- **8000**: FastAPI API (backend)
- **5443**: PostgreSQL (container `arquantix-db`, mappé depuis 5432)

**Vérification**:
```bash
curl http://localhost:3000  # Web
curl http://localhost:8000/health  # API
docker exec arquantix-db pg_isready -U arquantix  # DB
```

**Référence**: `scripts/arquantix-start.sh:94,134,161`

### Ports bloqués au reboot

**Problème**: Port 8000 ou 3000 déjà utilisé.

**Solution**:
```bash
# Trouver processus utilisant le port
lsof -i :8000
lsof -i :3000

# Tuer processus
kill -9 <PID>
```

**Référence**: Problème rencontré lors des redémarrages

---

## 3. Variables d'environnement

### API (`api/.env.local` ou `api/.env`)

**Variables clés**:
- `DATABASE_URL` - PostgreSQL connection string (format: `postgresql://user:password@host:port/database`)
  - Exemple: `postgresql://arquantix:arquantix@localhost:5443/arquantix_quant`
- `JWT_SECRET_KEY` - Secret pour JWT (défaut: `"your-secret-key-change-in-production"`)
- `CORS_ORIGINS` - Origines autorisées (défaut: `"http://localhost:3001,http://localhost:3000,http://localhost:3011"`)
- `PORT` - Port FastAPI (défaut: `8000`)

**Ordre de chargement**: `.env.local` (priorité) > `.env`

**Référence**: `api/database.py:8-11`, `api/main.py:49`, `api/auth.py:24`

### Web (`web/.env`)

**Variables clés**:
- `DATABASE_URL` - Prisma DATABASE_URL (pour CMS, non vérifié)
- `JWT_SECRET_KEY` - Doit correspondre à celui de l'API
- `AUTH_SECRET` - Fallback pour JWT_SECRET_KEY
- `NEXT_PUBLIC_*` - Variables publiques Next.js (UNKNOWN si utilisées)

**Référence**: `web/src/app/api/bundles/route.ts:25`

---

## 4. Debug

### Logs

**API**: `/tmp/arquantix-api.log`

**Web**: `/tmp/arquantix-web.log`

**DB**: `docker logs arquantix-db`

**Commandes**:
```bash
tail -f /tmp/arquantix-api.log  # Suivre logs API
tail -f /tmp/arquantix-web.log  # Suivre logs Web
docker logs -f arquantix-db      # Suivre logs DB
```

**Référence**: `scripts/arquantix-start.sh:196-199`

### Erreurs 500

**Causes communes**:
1. **`NaN` dans JSON PostgreSQL**: Conversion `NaN` → `None` avant stockage
2. **`asset_class` NOT NULL violation**: Calculer `asset_class` depuis instruments
3. **`type` CHECK violation**: Utiliser `'fixed_instruments'` au lieu de `'FIXED_WEIGHT'`
4. **Exception non gérée**: Vérifier traceback dans `/tmp/arquantix-api.log`

**Debug**:
```bash
tail -100 /tmp/arquantix-api.log | grep -A 30 "Error\|Traceback\|Exception"
```

**Référence**: Sections "Bugs majeurs rencontrés" dans `20_BACKEND_FASTAPI.md`

### Erreurs 422 (Pydantic)

**Cause**: Validation Pydantic échouée (format date invalide, type incorrect, etc.).

**Format erreur**:
```json
{
  "detail": [
    {
      "loc": ["body", "start_date"],
      "msg": "invalid date format",
      "type": "value_error.date"
    }
  ]
}
```

**Debug**: Vérifier format des données envoyées (dates `YYYY-MM-DD`, types corrects).

**Référence**: FastAPI auto-génère ces erreurs

### Erreurs 409 (Conflict)

⚠️ **UNKNOWN (needs confirmation)**: Non vérifié dans le code actuel.

**Causes possibles**: Duplicate key (symbol instrument, name bundle + asset_class).

### Erreurs 502 (Bad Gateway)

**Cause**: Backend FastAPI indisponible.

**Messages côté Next.js**:
- `"Backend is unavailable. Please ensure the FastAPI backend is running on http://localhost:8000"`
- `ECONNREFUSED`, `ETIMEDOUT`

**Debug**:
```bash
curl http://localhost:8000/health  # Vérifier API
tail /tmp/arquantix-api.log        # Vérifier erreurs API
```

**Référence**: `web/src/app/api/bundles/route.ts:68-84`

---

## 5. Checklist "après reboot"

### Ordre d'exécution

1. **Docker Desktop**: Démarré et running
2. **Container DB**: `docker start arquantix-db` (si arrêté)
3. **Vérifier DB healthy**: `docker inspect arquantix-db --format '{{.State.Health.Status}}'` → doit être `healthy`
4. **Vérifier port DB**: `docker inspect arquantix-db --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}'` → doit être `5443`
5. **Vérifier `.env`**: DATABASE_URL doit pointer vers `localhost:5443` ou `arquantix-db:5432`
6. **Démarrer API**: Via script ou manuellement
7. **Démarrer Web**: Via script ou manuellement

**Script automatique**: `./scripts/arquantix-start.sh` (fait tout automatiquement)

**Référence**: `scripts/arquantix-start.sh`

### Vérifications post-démarrage

**API**:
```bash
curl http://localhost:8000/health  # Doit retourner {"status": "ok", "service": "arquantix-api"}
curl http://localhost:8000/docs    # Doit afficher Swagger UI
```

**Web**:
```bash
curl http://localhost:3000  # Doit retourner HTML Next.js
```

**DB**:
```bash
docker exec arquantix-db psql -U arquantix -d arquantix_quant -c "SELECT COUNT(*) FROM market_data_instruments;"
```

---

## 6. Commandes utiles

### Status services

**Script**: `./scripts/arquantix-status.sh` (UNKNOWN si existe)

**Manuel**:
```bash
# API
curl http://localhost:8000/health

# Web
curl http://localhost:3000

# DB
docker exec arquantix-db pg_isready -U arquantix
```

### Arrêt services

**Script**: `./stop-all.sh` (UNKNOWN si existe)

**Manuel**:
```bash
kill $(cat /tmp/arquantix-api.pid) 2>/dev/null
kill $(cat /tmp/arquantix-web.pid) 2>/dev/null
```

### Vider cache Next.js

```bash
cd web
rm -rf .next/cache
rm -rf .next
```

**Utilisation**: Après modifications importantes (layout, erreurs persistantes).

---

## 7. Problèmes connus

### Front cassé après refactor

**Symptôme**: Erreur "The default export is not a React Component" sur `/admin/login`.

**Causes**:
1. `useSearchParams()` sans `Suspense`
2. Layout admin vide

**Fix**: Wrapper dans `<Suspense>`, layout retourne `<div>{children}</div>`, vider cache Next.js.

**Référence**: Section "Problèmes connus" dans `10_FRONTEND_NEXTJS.md`

### Routes écrasées

⚠️ **UNKNOWN (needs confirmation)**: Non vérifié dans le code actuel.

### Ports bloqués au reboot

**Symptôme**: Erreur `EADDRINUSE` au démarrage API/Web.

**Cause**: Ancien processus encore actif.

**Fix**: Tuer processus avec `lsof -i :PORT` puis `kill -9 PID`.

**Référence**: Problème rencontré lors des redémarrages

---

## 8. Migrations Alembic

### Appliquer migrations

```bash
cd api
alembic upgrade head
```

### Créer nouvelle migration

```bash
cd api
alembic revision --autogenerate -m "description"
```

### Vérifier état migrations

```bash
cd api
alembic current
alembic history
```

**Référence**: `api/alembic.ini`, `api/alembic/env.py`

---

## 9. Scripts utilitaires

### Load market data

```bash
cd api
python scripts/load_market_data.py --all  # Charge toutes les données
python scripts/load_market_data.py --update-recent  # Met à jour données récentes
python scripts/load_market_data.py --instrument-id 11  # Charge instrument spécifique
```

**Référence**: `api/scripts/load_market_data.py`

### Seed initial

```bash
cd api
python scripts/seed.py  # Crée admin user et global settings
```

**Variables**: `ADMIN_EMAIL`, `ADMIN_PASSWORD`

**Référence**: `api/scripts/seed.py`

### Diagnostic market data / backtest

**Endpoint**: `GET /api/diagnostics/market-backtest`

**Usage**: Vérifier intégrité données market data et composants backtest.

**Référence**: `api/services/diagnostics/market_backtest.py`

---

## 10. URLs de référence

**Local**:
- Web: `http://localhost:3000`
- Admin: `http://localhost:3000/admin/login`
- API Docs: `http://localhost:8000/docs`
- API Health: `http://localhost:8000/health`

**Référence**: `scripts/arquantix-start.sh:191-194`


