# Operations — Guide Opérationnel Arquantix

**Procédures pour redémarrer et maintenir Arquantix sans erreurs**

---

## Containers et Ports

### Containers Docker

| Container | Image | Port Host | Port Container | Description |
|-----------|-------|-----------|----------------|-------------|
| `arquantix-db` | `postgres:15` | `5443` | `5432` | Base de données PostgreSQL |

**⚠️ IMPORTANT** : 
- **Port 5443** = Arquantix
- **Port 5434** = zitadel-db (base séparée, NE PAS utiliser)

### Services Locaux

| Service | Technologie | Port | Process |
|---------|------------|------|---------|
| **Web** | Next.js | `3000` | `npm run dev` |
| **API** | FastAPI | `8000` | `uvicorn main:app --reload` |

---

## Redémarrage Complet

### Checklist Pré-Redémarrage

1. **Vérifier Docker Desktop** : Doit être running
2. **Vérifier ports libres** : 3000, 8000, 5443
3. **Vérifier variables d'environnement** : `.env` files présents

### Étape 1 : Base de Données

```bash
# Vérifier que arquantix-db existe
docker ps -a | grep arquantix-db

# Si n'existe pas, créer (voir scripts/arquantix-start.sh)
# Si existe mais stopped, démarrer
docker start arquantix-db

# Attendre 5-10 secondes pour que PostgreSQL démarre
sleep 10

# Vérifier health
docker inspect arquantix-db --format '{{.State.Health.Status}}'
# Doit afficher: healthy

# Vérifier port
docker ps | grep arquantix-db | grep 5443
# Doit afficher le container
```

### Étape 2 : API (FastAPI)

```bash
cd services/arquantix/api

# Vérifier .env
cat .env | grep DATABASE_URL
# Doit contenir: localhost:5443 (pas 5434!)

# Démarrer API
python3 -m uvicorn main:app --reload --port 8000
```

**Vérification** :
```bash
curl http://localhost:8000/health
# Doit retourner: {"status":"ok","service":"arquantix-api"}
```

### Étape 3 : Web (Next.js)

```bash
cd services/arquantix/web

# Vérifier .env
cat .env | grep DATABASE_URL
# Doit contenir: localhost:5443 (pas 5434!)

# Démarrer Web
npm run dev
```

**Vérification** :
```bash
curl -I http://localhost:3000
# Doit retourner: HTTP/1.1 200 OK
```

### Étape 4 : Vérification Complète

1. **Site vitrine** : http://localhost:3000 → Doit afficher la page d'accueil
2. **Admin login** : http://localhost:3000/admin/login → Doit afficher le formulaire
3. **API docs** : http://localhost:8000/docs → Doit afficher Swagger UI

---

## Health Checks

### Base de Données

```bash
# Health check Docker
docker inspect arquantix-db --format '{{.State.Health.Status}}'

# Connexion PostgreSQL
docker exec arquantix-db pg_isready -U arquantix

# Test query
docker exec arquantix-db psql -U arquantix -d arquantix -c "SELECT 1;"
```

### API

```bash
# Health endpoint
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/
```

### Web

```bash
# Homepage
curl -I http://localhost:3000

# Admin login
curl -I http://localhost:3000/admin/login
```

---

## Détection d'Erreurs de Configuration

### Erreur : Port 5434 au lieu de 5443

**Symptôme** :
- Web retourne HTTP 500
- API erreur de connexion DB
- Logs montrent "could not connect to server"

**Diagnostic** :
```bash
# Vérifier .env files
grep -r "5434" web/.env* api/.env*
# Ne doit rien retourner (5434 est interdit)
```

**Solution** :
```bash
# Corriger .env files
# Remplacer 5434 par 5443
sed -i '' 's/5434/5443/g' web/.env
sed -i '' 's/5434/5443/g' api/.env
```

### Erreur : Base de Données Arrêtée

**Symptôme** :
- Web retourne HTTP 500
- API erreur de connexion
- Message "connection refused"

**Diagnostic** :
```bash
docker ps | grep arquantix-db
# Si vide, container est stopped
```

**Solution** :
```bash
docker start arquantix-db
# Attendre 10 secondes
docker inspect arquantix-db --format '{{.State.Health.Status}}'
# Doit afficher: healthy
```

### Erreur : Base de Données Non Healthy

**Symptôme** :
- Container running mais services ne se connectent pas

**Diagnostic** :
```bash
docker inspect arquantix-db --format '{{.State.Health.Status}}'
# Si "unhealthy" ou "starting"
```

**Solution** :
```bash
# Voir les logs
docker logs arquantix-db --tail 50

# Redémarrer
docker restart arquantix-db
# Attendre 15 secondes
```

### Erreur : Tables Manquantes

**Symptôme** :
- Web : "The table public.pages does not exist"
- API : "relation does not exist"

**Diagnostic** :
```bash
# Vérifier migrations Prisma
cd web
npx prisma migrate status

# Vérifier migrations Alembic
cd ../api
python3 -m alembic current
```

**Solution** :
```bash
# Prisma
cd web
npx prisma migrate deploy

# Alembic
cd ../api
python3 -m alembic upgrade head
```

---

## Restart Policy

### Configuration Requise

Pour éviter que `arquantix-db` s'arrête après un redémarrage système :

```bash
docker update --restart unless-stopped arquantix-db
```

**Vérifier** :
```bash
docker inspect arquantix-db --format '{{.HostConfig.RestartPolicy.Name}}'
# Doit afficher: unless-stopped
```

**Pourquoi ?** Sans cette politique, `arquantix-db` ne redémarre pas automatiquement après un redémarrage du Mac/Docker Desktop, ce qui cause des erreurs 500 sur Web et des erreurs de connexion sur API.

---

## Checklist "Site Blank / 500"

Si le site est blank ou retourne HTTP 500, vérifier dans cet ordre :

### 1. Docker Desktop

```bash
# Vérifier que Docker Desktop est running
docker ps
# Doit afficher au moins arquantix-db
```

**Si Docker Desktop n'est pas running** → Démarrer Docker Desktop, puis continuer.

### 2. Base de Données

```bash
# Vérifier container
docker ps | grep arquantix-db
# Doit afficher le container

# Vérifier health
docker inspect arquantix-db --format '{{.State.Health.Status}}'
# Doit afficher: healthy

# Vérifier port
docker ps | grep arquantix-db | grep 5443
# Doit afficher le container
```

**Si container stopped** → `docker start arquantix-db`, attendre 10s, vérifier health.

**Si unhealthy** → `docker logs arquantix-db --tail 50`, corriger le problème.

### 3. Variables d'Environnement

```bash
# Web
cd web
cat .env | grep DATABASE_URL
# Doit contenir: localhost:5443 (pas 5434!)

# API
cd ../api
cat .env | grep DATABASE_URL
# Doit contenir: localhost:5443 (pas 5434!)
```

**Si port 5434** → Corriger en 5443, redémarrer services.

### 4. Migrations

```bash
# Prisma
cd web
npx prisma migrate status
# Si "pending", appliquer: npx prisma migrate deploy

# Alembic
cd ../api
python3 -m alembic current
# Si migrations manquantes, appliquer: python3 -m alembic upgrade head
```

### 5. Services Running

```bash
# Vérifier API
curl http://localhost:8000/health
# Doit retourner: {"status":"ok"}

# Vérifier Web
curl -I http://localhost:3000
# Doit retourner: HTTP/1.1 200 OK
```

**Si services ne répondent pas** → Redémarrer API et Web.

---

## Logs

### Emplacements

| Service | Local | Docker |
|---------|-------|--------|
| **Web** | Terminal ou `/tmp/arquantix-web.log` | N/A (pas de container) |
| **API** | Terminal ou `/tmp/arquantix-api.log` | N/A (pas de container) |
| **Database** | `docker logs arquantix-db` | `docker logs arquantix-db` |

### Commandes Utiles

```bash
# Logs Web (dernières 50 lignes)
tail -n 50 /tmp/arquantix-web.log

# Logs API (dernières 50 lignes)
tail -n 50 /tmp/arquantix-api.log

# Logs DB (dernières 50 lignes)
docker logs arquantix-db --tail 50

# Suivre logs en temps réel
docker logs arquantix-db -f
```

---

## Modes de Défaillance Courants

### Mode 1 : DB Arrêtée Après Redémarrage Système

**Cause** : Restart policy non configurée

**Symptôme** : Site blank, API erreur de connexion

**Fix** :
```bash
docker start arquantix-db
docker update --restart unless-stopped arquantix-db
```

### Mode 2 : Mauvais Port DB (5434 au lieu de 5443)

**Cause** : Variables d'environnement incorrectes

**Symptôme** : Services ne se connectent pas à la DB

**Fix** :
```bash
# Corriger .env files
sed -i '' 's/5434/5443/g' web/.env
sed -i '' 's/5434/5443/g' api/.env
# Redémarrer services
```

### Mode 3 : Tables Manquantes

**Cause** : Migrations non appliquées

**Symptôme** : "The table public.pages does not exist"

**Fix** :
```bash
# Prisma
cd web && npx prisma migrate deploy

# Alembic
cd ../api && python3 -m alembic upgrade head
```

### Mode 4 : Container DB Corrompu

**Cause** : Corruption de données ou problème Docker

**Symptôme** : Container unhealthy, logs montrent erreurs PostgreSQL

**Fix** :
```bash
# Voir logs
docker logs arquantix-db --tail 100

# Si corruption, restaurer depuis backup (si disponible)
# Sinon, recréer container (⚠️ perte de données)
```

---

## Scripts Utilitaires

### Démarrage Complet

```bash
./scripts/arquantix-start.sh
```

### Vérification État

```bash
./scripts/arquantix-status.sh
```

### Arrêt

```bash
./scripts/arquantix-stop.sh
```

---

## Maintenance

### Backup Base de Données

```bash
# Backup arquantix
docker exec arquantix-db pg_dump -U arquantix arquantix > backup_arquantix_$(date +%Y%m%d).sql

# Backup arquantix_admin
docker exec arquantix-db pg_dump -U arquantix arquantix_admin > backup_admin_$(date +%Y%m%d).sql
```

### Restauration

```bash
# Restore arquantix
cat backup_arquantix_20260109.sql | docker exec -i arquantix-db psql -U arquantix arquantix

# Restore arquantix_admin
cat backup_admin_20260109.sql | docker exec -i arquantix-db psql -U arquantix arquantix_admin
```

---

## Commandes de Diagnostic

### Vérifier Connexions DB

```bash
# Depuis host
docker exec arquantix-db psql -U arquantix -d arquantix -c "SELECT COUNT(*) FROM market_data_instruments;"

# Depuis API (si running)
curl http://localhost:8000/health
```

### Vérifier Migrations

```bash
# Prisma
cd web
npx prisma migrate status

# Alembic
cd ../api
python3 -m alembic history
python3 -m alembic current
```

### Vérifier Services

```bash
# API
curl http://localhost:8000/health
curl http://localhost:8000/

# Web
curl -I http://localhost:3000
curl -I http://localhost:3000/admin/login
```

---

**Dernière mise à jour:** 2026-01-09

