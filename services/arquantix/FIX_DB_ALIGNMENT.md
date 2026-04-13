# ✅ FIX MINIMAL: Alignement DB URLs sur arquantix-db:5443

**Date**: 2026-01-08  
**Objectif**: Aligner toutes les configurations DB Arquantix sur `arquantix-db:5443` et éliminer l'usage de `zitadel-db`

---

## 📊 RÉSUMÉ DES MODIFICATIONS

### ✅ Fichiers modifiés

1. **`web/.env`**
   - ❌ Avant: `DATABASE_URL="postgresql://arquantix:arquantix@localhost:5434/arquantix_admin"`
   - ✅ Après: `DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix_admin"`
   - **Changement**: Port `5434` (zitadel-db) → `5443` (arquantix-db)

2. **`cms/.env`**
   - ❌ Avant: `DATABASE_PORT=5433`
   - ✅ Après: `DATABASE_PORT=5443`
   - **Changement**: Port `5433` (inexistant) → `5443` (arquantix-db)

3. **`api/.env`**
   - ✅ Déjà correct: `DATABASE_URL=postgresql://arquantix:arquantix@localhost:5443/arquantix`
   - **Aucun changement nécessaire**

### ✅ Fichiers non modifiés (déjà corrects)

- `api/.env.local` → `localhost:5443` (correct)
- Container Docker `arquantix-api` → `arquantix-db:5432` (correct pour réseau Docker)

---

## 🗄️ BASES DE DONNÉES DISPONIBLES

Toutes les bases suivantes existent dans `arquantix-db` (port 5443):

- ✅ `arquantix` (API principale)
- ✅ `arquantix_admin` (Web/Next.js)
- ✅ `arquantix_cms` (Strapi CMS)
- ✅ `arquantix_quant` (API quant)

---

## 🔧 CONFIGURATIONS FINALES

### Web (Next.js)
```env
DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix_admin"
```
- **Host**: `localhost` (dev local)
- **Port**: `5443` (arquantix-db)
- **Database**: `arquantix_admin`

### API (FastAPI)
```env
DATABASE_URL=postgresql://arquantix:arquantix@localhost:5443/arquantix
```
- **Host**: `localhost` (dev local)
- **Port**: `5443` (arquantix-db)
- **Database**: `arquantix`

**Note**: Le container Docker `arquantix-api` utilise `arquantix-db:5432` (correct pour réseau Docker).

### CMS (Strapi)
```env
DATABASE_CLIENT=postgres
DATABASE_HOST=localhost
DATABASE_PORT=5443
DATABASE_NAME=arquantix_cms
DATABASE_USERNAME=arquantix
DATABASE_PASSWORD=arquantix
```
- **Host**: `localhost` (dev local)
- **Port**: `5443` (arquantix-db)
- **Database**: `arquantix_cms`

---

## 🚀 COMMANDES DE REDÉMARRAGE MINIMALES

### 1. Vérifier que arquantix-db est démarré

```bash
docker ps | grep arquantix-db
```

Si le container n'est pas démarré:
```bash
docker start arquantix-db
```

Vérifier la santé:
```bash
docker exec arquantix-db pg_isready -U arquantix
```

### 2. Redémarrer Web (Next.js)

**Si Web tourne en local (npm run dev)**:
```bash
# Arrêter le processus (Ctrl+C dans le terminal)
# Puis redémarrer:
cd services/arquantix/web
npm run dev
```

**Si Web tourne dans Docker**:
```bash
docker restart arquantix-web
```

### 3. Redémarrer API (FastAPI)

**Si API tourne en local (uvicorn)**:
```bash
# Arrêter le processus (Ctrl+C dans le terminal)
# Puis redémarrer:
cd services/arquantix/api
uvicorn main:app --reload --port 8000
```

**Si API tourne dans Docker**:
```bash
docker restart arquantix-api
```

### 4. Redémarrer CMS (Strapi)

**Si CMS tourne en local (npm run develop)**:
```bash
# Arrêter le processus (Ctrl+C dans le terminal)
# Puis redémarrer:
cd services/arquantix/cms
npm run develop
```

**Note**: Strapi n'a pas de container Docker actif.

---

## ✅ VÉRIFICATIONS POST-REDÉMARRAGE

### 1. Vérifier les connexions DB

**Web**:
```bash
cd services/arquantix/web
npx prisma db pull  # Teste la connexion
```

**API**:
```bash
cd services/arquantix/api
python3 -c "from database import DATABASE_URL; print('DB:', DATABASE_URL)"
```

**CMS**:
- Vérifier les logs Strapi au démarrage
- Accéder à http://localhost:1337/admin

### 2. Vérifier que les services fonctionnent

- **Web**: http://localhost:3000 (ou port configuré)
- **API**: http://localhost:8000/docs
- **CMS**: http://localhost:1337/admin

### 3. Vérifier les logs pour erreurs DB

**Web**:
```bash
# Si en local, voir les logs dans le terminal
# Si Docker:
docker logs arquantix-web --tail 50
```

**API**:
```bash
# Si en local, voir les logs dans le terminal
# Si Docker:
docker logs arquantix-api --tail 50
```

**CMS**:
```bash
# Logs dans le terminal où Strapi tourne
```

---

## 🔍 DIAGNOSTIC EN CAS DE PROBLÈME

### Erreur: "Connection refused" ou "Cannot connect"

1. **Vérifier que arquantix-db est démarré**:
```bash
docker ps | grep arquantix-db
docker exec arquantix-db pg_isready -U arquantix
```

2. **Vérifier le port**:
```bash
lsof -i -P | grep LISTEN | grep 5443
```

3. **Vérifier les credentials**:
```bash
docker exec arquantix-db psql -U arquantix -d arquantix -c "SELECT current_database();"
```

### Erreur: "Database does not exist"

Créer la base manquante:
```bash
docker exec arquantix-db psql -U arquantix -c "CREATE DATABASE arquantix_admin OWNER arquantix;"
docker exec arquantix-db psql -U arquantix -c "CREATE DATABASE arquantix_cms OWNER arquantix;"
```

### Erreur: "Authentication failed"

Vérifier les credentials dans `.env`:
- User: `arquantix`
- Password: `arquantix`
- Database: selon le service (voir configurations ci-dessus)

---

## 📝 BACKUPS CRÉÉS

Des backups ont été créés avant modification:
- `web/.env.backup-YYYYMMDD-HHMMSS`
- `cms/.env.backup-YYYYMMDD-HHMMSS`

Pour restaurer:
```bash
cp web/.env.backup-YYYYMMDD-HHMMSS web/.env
cp cms/.env.backup-YYYYMMDD-HHMMSS cms/.env
```

---

## ✅ RÉSUMÉ

- ✅ **Web**: Port `5434` → `5443` (arquantix-db)
- ✅ **CMS**: Port `5433` → `5443` (arquantix-db)
- ✅ **API**: Déjà correct (`5443`)
- ✅ **Toutes les bases existent** dans arquantix-db
- ✅ **Aucune référence à zitadel-db** pour Arquantix

**Prochaine étape**: Redémarrer les services selon les commandes ci-dessus.





