# 🚀 Guide de Démarrage Arquantix — Pas à Pas

Guide complet pour démarrer tous les services Arquantix en développement local.

---

## 📋 Prérequis

- **Docker Desktop** (démarré et fonctionnel)
- **Node.js 20+** (vérifier: `node --version`)
- **Python 3.9+** (vérifier: `python3 --version`)
- **npm** ou **pnpm** (vérifier: `npm --version`)

---

## Étape 1: Démarrer la Base de Données

### 1.1 Vérifier que Docker est démarré

```bash
docker ps
```

Si Docker n'est pas démarré, lancer Docker Desktop.

### 1.2 Démarrer arquantix-db

```bash
docker start arquantix-db
```

### 1.3 Vérifier que la DB est healthy

```bash
docker ps | grep arquantix-db
```

**Résultat attendu:**
```
95319deec9dd   postgres:15-alpine   ...   Up X seconds (healthy)   0.0.0.0:5443->5432/tcp   arquantix-db
```

### 1.4 Vérifier la connexion PostgreSQL

```bash
docker exec arquantix-db pg_isready -U arquantix
```

**Résultat attendu:**
```
/var/run/postgresql:5432 - accepting connections
```

### 1.5 ⚠️ IMPORTANT: Configurer la Restart Policy

Pour éviter que la DB s'arrête après un redémarrage système:

```bash
docker update --restart unless-stopped arquantix-db
```

**Vérifier:**
```bash
docker inspect arquantix-db --format '{{.HostConfig.RestartPolicy.Name}}'
# Doit afficher: unless-stopped
```

---

## Étape 2: Démarrer l'API (FastAPI)

### 2.1 Aller dans le répertoire API

```bash
cd services/arquantix/api
```

### 2.2 Vérifier la configuration

```bash
cat .env | grep DATABASE_URL
```

**Doit contenir:**
```
DATABASE_URL=postgresql://arquantix:arquantix@localhost:5443/arquantix
```

**⚠️ Si le port est 5434 ou 5433, corriger:**
```bash
# Éditer api/.env et changer le port en 5443
```

### 2.3 Installer les dépendances (première fois)

```bash
pip install -r requirements.txt
```

### 2.4 Démarrer l'API

```bash
python3 -m uvicorn main:app --reload --port 8000
```

**Résultat attendu:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

**URL:** http://localhost:8000/docs

---

## Étape 3: Démarrer le Web (Next.js)

### 3.1 Aller dans le répertoire Web

```bash
cd services/arquantix/web
```

### 3.2 Vérifier la configuration

```bash
cat .env | grep DATABASE_URL
```

**Doit contenir:**
```
DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix_admin"
```

**⚠️ Si le port est 5434 ou 5433, corriger:**
```bash
# Éditer web/.env et changer le port en 5443
```

### 3.3 Installer les dépendances (première fois)

```bash
npm install
```

### 3.4 Appliquer les migrations Prisma (première fois ou après changement de schéma)

```bash
npx prisma migrate deploy
# ou
npx prisma db push
```

### 3.5 Générer le client Prisma

```bash
npx prisma generate
```

### 3.6 Démarrer le serveur de développement

```bash
npm run dev
```

**Résultat attendu:**
```
✓ Ready in X seconds
○ Local:        http://localhost:3000
```

**URLs:**
- Site: http://localhost:3000
- Admin: http://localhost:3000/admin/login

---

## Étape 4: Vérifications de Santé

### 4.1 Vérifier que tous les services sont démarrés

```bash
# Database
docker ps | grep arquantix-db

# API (doit répondre)
curl http://localhost:8000/health 2>/dev/null || echo "API non accessible"

# Web (doit répondre)
curl http://localhost:3000 2>/dev/null | head -1 || echo "Web non accessible"
```

### 4.2 Vérifier les logs pour erreurs

```bash
# Logs API (si démarrée en arrière-plan)
tail -20 /tmp/arquantix-api.log

# Logs Web (si démarré en arrière-plan)
tail -20 /tmp/arquantix-web.log

# Logs DB
docker logs arquantix-db --tail 20
```

---

## Étape 5: Arrêter Tous les Services

### 5.1 Arrêter Web et API

**Si démarrés dans des terminaux:**
- Appuyer sur `Ctrl+C` dans chaque terminal

**Si démarrés en arrière-plan:**
```bash
cd services/arquantix
./stop-all.sh
```

### 5.2 Arrêter la base de données (optionnel)

```bash
docker stop arquantix-db
```

**⚠️ Note:** Il est recommandé de laisser `arquantix-db` démarré pour éviter les erreurs de connexion.

---

## 🔍 Troubleshooting

### Problème: "Connection refused" sur Web ou API

**Diagnostic:**
```bash
# Vérifier que arquantix-db est démarré
docker ps | grep arquantix-db

# Vérifier le port
docker ps | grep arquantix-db | grep 5443

# Tester la connexion
docker exec arquantix-db pg_isready -U arquantix
```

**Solution:**
```bash
docker start arquantix-db
# Attendre 5-10 secondes
```

---

### Problème: "The table public.pages does not exist"

**Solution:**
```bash
cd services/arquantix/web
npx prisma migrate deploy
npx prisma generate
```

---

### Problème: API ne démarre pas / erreur "could not translate host name"

**Diagnostic:**
```bash
# Vérifier api/.env
cat api/.env | grep DATABASE_URL
# Doit contenir: localhost:5443 (pas arquantix-db:5432 en dev local)
```

**Solution:**
```bash
# Éditer api/.env et corriger DATABASE_URL
# Puis redémarrer l'API
```

---

### Problème: Web retourne HTTP 500

**Diagnostic:**
```bash
# Vérifier les logs Web
tail -50 /tmp/arquantix-web.log | grep -i error

# Vérifier la connexion DB
docker exec arquantix-db psql -U arquantix -d arquantix_admin -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"
```

**Solutions possibles:**
1. DB arrêtée → `docker start arquantix-db`
2. Tables manquantes → `npx prisma migrate deploy` dans `web/`
3. Mauvais port → Vérifier `web/.env` (doit être 5443)

---

### Problème: Port déjà utilisé

**Diagnostic:**
```bash
lsof -i -P | grep LISTEN | grep -E "3000|8000|5443"
```

**Solutions:**
- **Port 3000 (Web):** Arrêter le processus existant ou utiliser un autre port
- **Port 8000 (API):** Arrêter le processus existant ou modifier le port dans la commande uvicorn
- **Port 5443 (DB):** Normal, c'est le port de la DB

---

## 📋 Commandes Rapides (Copier/Coller)

### Démarrer tout (Happy Path)

```bash
# 1. DB
docker start arquantix-db && sleep 5 && docker ps | grep arquantix-db

# 2. API (Terminal 1)
cd services/arquantix/api && python3 -m uvicorn main:app --reload --port 8000

# 3. Web (Terminal 2)
cd services/arquantix/web && npm run dev
```

### Diagnostic Rapide

```bash
# Vérifier DB
docker ps | grep arquantix-db && docker exec arquantix-db pg_isready -U arquantix

# Vérifier ports
lsof -i -P | grep LISTEN | grep -E "3000|8000|5443"

# Vérifier configs
echo "=== WEB ===" && cat services/arquantix/web/.env | grep DATABASE_URL
echo "=== API ===" && cat services/arquantix/api/.env | grep DATABASE_URL

# Vérifier logs
echo "=== WEB LOGS ===" && tail -10 /tmp/arquantix-web.log 2>/dev/null || echo "Pas de logs"
echo "=== API LOGS ===" && tail -10 /tmp/arquantix-api.log 2>/dev/null || echo "Pas de logs"
```

---

**Dernière mise à jour:** 2026-01-08





