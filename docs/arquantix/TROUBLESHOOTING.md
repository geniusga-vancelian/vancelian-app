# Troubleshooting - Arquantix Vitrine + CMS

**Date:** 2026-01-01  
**Status:** 🚧 En cours de développement

---

## TL;DR

Guide de dépannage pour les problèmes courants avec Arquantix (Next.js + Strapi + PostgreSQL).

---

## Ce qui est vrai aujourd'hui

### Problèmes Courants

1. Services ne démarrent pas
2. Connexion à la base de données échoue
3. Next.js ne peut pas se connecter à Strapi
4. Build Docker échoue
5. Ports déjà utilisés
6. Permissions API Strapi
7. Erreurs de déploiement

---

## Dépannage Local (Docker Compose)

### Problème: Les Services Ne Démarrent Pas

**Symptômes:**
- `docker compose -f docker-compose.arquantix.yml up -d` échoue
- Containers en état `Exited` ou `Error`

**Diagnostic:**
```bash
# Vérifier les logs
docker compose -f docker-compose.arquantix.yml logs

# Vérifier le statut
docker compose -f docker-compose.arquantix.yml ps
```

**Solutions:**
1. **Ports déjà utilisés:**
   ```bash
   # Vérifier les ports
   lsof -i :3001
   lsof -i :1338
   lsof -i :5433
   
   # Arrêter les processus ou changer les ports dans .env.arquantix
   ```

2. **Variables d'environnement manquantes:**
   ```bash
   # Vérifier .env.arquantix existe
   ls -la .env.arquantix
   
   # Vérifier les variables requises
   cat .env.arquantix | grep CMS_
   ```

3. **Images Docker non construites:**
   ```bash
   # Rebuild les images
   docker compose -f docker-compose.arquantix.yml build
   ```

4. **Volumes corrompus:**
   ```bash
   # Supprimer et recréer les volumes
   docker compose -f docker-compose.arquantix.yml down -v
   docker compose -f docker-compose.arquantix.yml up -d
   ```

---

### Problème: Strapi Ne Peut Pas Se Connecter à PostgreSQL

**Symptômes:**
- Logs Strapi: `Error: connect ECONNREFUSED`
- Strapi ne démarre pas

**Diagnostic:**
```bash
# Vérifier que PostgreSQL est démarré
docker compose -f docker-compose.arquantix.yml ps arquantix-cms-db

# Vérifier les logs PostgreSQL
docker compose -f docker-compose.arquantix.yml logs arquantix-cms-db

# Tester la connexion
docker compose -f docker-compose.arquantix.yml exec arquantix-cms-db psql -U strapi -d arquantix_cms
```

**Solutions:**
1. **PostgreSQL non démarré:**
   ```bash
   # Redémarrer PostgreSQL
   docker compose -f docker-compose.arquantix.yml restart arquantix-cms-db
   ```

2. **Variables d'environnement incorrectes:**
   - Vérifier `DATABASE_HOST=arquantix-cms-db`
   - Vérifier `DATABASE_NAME`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`
   - Vérifier dans `.env.arquantix` ou `services/arquantix/cms/.env`

3. **Base de données n'existe pas:**
   ```bash
   # Créer la base de données manuellement
   docker compose -f docker-compose.arquantix.yml exec arquantix-cms-db psql -U strapi -c "CREATE DATABASE arquantix_cms;"
   ```

4. **Permissions PostgreSQL:**
   ```bash
   # Vérifier les permissions
   docker compose -f docker-compose.arquantix.yml exec arquantix-cms-db psql -U strapi -c "\du"
   ```

---

### Problème: Next.js Ne Peut Pas Se Connecter à Strapi

**Symptômes:**
- Next.js: `fetch failed` ou `ECONNREFUSED`
- Pages ne se chargent pas (contenu manquant)

**Diagnostic:**
```bash
# Vérifier que Strapi est démarré
docker compose -f docker-compose.arquantix.yml ps arquantix-cms

# Tester la connexion depuis Next.js container
docker compose -f docker-compose.arquantix.yml exec arquantix-web wget -O- http://arquantix-cms:1338/api

# Vérifier les variables d'environnement Next.js
docker compose -f docker-compose.arquantix.yml exec arquantix-web env | grep STRAPI
```

**Solutions:**
1. **Strapi non démarré:**
   ```bash
   # Redémarrer Strapi
   docker compose -f docker-compose.arquantix.yml restart arquantix-cms
   ```

2. **Variables d'environnement incorrectes:**
   - Vérifier `NEXT_PUBLIC_STRAPI_URL=http://arquantix-cms:1338`
   - Vérifier `NEXT_PUBLIC_STRAPI_API_URL=http://arquantix-cms:1338/api`
   - Vérifier dans `docker-compose.arquantix.yml` ou `.env.arquantix`

3. **Réseau Docker:**
   ```bash
   # Vérifier le réseau
   docker network ls | grep arquantix
   
   # Vérifier que les services sont sur le même réseau
   docker compose -f docker-compose.arquantix.yml ps
   ```

4. **Strapi API inaccessible:**
   ```bash
   # Tester depuis l'host
   curl http://localhost:1338/api
   
   # Vérifier les logs Strapi
   docker compose -f docker-compose.arquantix.yml logs arquantix-cms
   ```

---

### Problème: Build Docker Échoue

**Symptômes:**
- `docker build` échoue avec des erreurs
- Erreurs de dépendances (npm install)

**Diagnostic:**
```bash
# Vérifier les logs de build
docker compose -f docker-compose.arquantix.yml build --no-cache arquantix-web 2>&1 | tee build.log

# Vérifier les fichiers source
ls -la services/arquantix/web/package.json
ls -la services/arquantix/cms/package.json
```

**Solutions:**
1. **Erreurs npm install:**
   ```bash
   # Nettoyer le cache npm
   docker system prune -a
   
   # Rebuild sans cache
   docker compose -f docker-compose.arquantix.yml build --no-cache
   ```

2. **Fichiers manquants:**
   - Vérifier que `package.json` existe
   - Vérifier que `Dockerfile` est correct
   - Vérifier le contexte de build (chemin)

3. **Erreurs TypeScript (Next.js):**
   ```bash
   # Build local pour tester
   cd services/arquantix/web
   npm install
   npm run build
   ```

---

### Problème: Ports Déjà Utilisés

**Symptômes:**
- `Error: bind: address already in use`
- Containers ne démarrent pas

**Diagnostic:**
```bash
# Identifier les processus utilisant les ports
lsof -i :3001
lsof -i :1338
lsof -i :5433

# Ou
netstat -an | grep 3001
netstat -an | grep 1338
netstat -an | grep 5433
```

**Solutions:**
1. **Arrêter les processus:**
   ```bash
   # Tuer le processus (remplacer PID)
   kill -9 <PID>
   ```

2. **Changer les ports:**
   - Modifier `.env.arquantix`:
     ```
     WEB_PORT=3002
     CMS_PORT=1339
     CMS_DB_PORT=5434
     ```
   - Ou modifier `docker-compose.arquantix.yml` directement

---

### Problème: Permissions API Strapi (403 Forbidden)

**Symptômes:**
- Next.js: `403 Forbidden` lors des appels API
- Contenu non accessible

**Diagnostic:**
```bash
# Tester l'API depuis l'host
curl http://localhost:1338/api/pages
# Devrait retourner du JSON (pas 403)
```

**Solutions:**
1. **Configurer les permissions dans Strapi Admin:**
   - Aller dans http://localhost:1338/admin
   - Settings → Users & Permissions Plugin → Roles → Public
   - Activer les permissions nécessaires:
     - `global`: `find`
     - `page`: `find`, `findOne`
     - `news`: `find`, `findOne`
     - `contactSubmission`: `create`

2. **Vérifier que le Content Type existe:**
   - Aller dans Content-Type Builder
   - Vérifier que les Content Types sont créés

3. **Vérifier que le contenu est publié:**
   - Aller dans Content Manager
   - Vérifier que le contenu n'est pas en brouillon

---

## Dépannage Déploiement

### Problème: Build GitHub Actions Échoue

**Symptômes:**
- Workflow GitHub Actions échoue au build
- Erreurs Docker ou npm

**Solutions:**
1. **Vérifier les logs GitHub Actions:**
   - Aller dans Actions → Workflow run → Job → Step
   - Lire les erreurs détaillées

2. **Vérifier les paths dans le workflow:**
   - Vérifier que les paths sont corrects (`services/arquantix/web/**`)
   - Vérifier le contexte de build Docker

3. **Vérifier les secrets:**
   - Vérifier que les secrets GitHub sont configurés
   - Vérifier les permissions AWS

---

### Problème: Push ECR Échoue

**Symptômes:**
- `Error: no basic auth credentials`
- `Error: denied: AccessDenied`

**Solutions:**
1. **Vérifier les permissions AWS:**
   - Vérifier que l'utilisateur AWS a les permissions `ecr:PushImage`
   - Vérifier que le repository ECR existe

2. **Vérifier les secrets GitHub:**
   - Vérifier `AWS_ACCESS_KEY_ID` et `AWS_SECRET_ACCESS_KEY`
   - Vérifier `AWS_REGION`

---

### Problème: Déploiement ECS Échoue

**Symptômes:**
- Service ECS ne démarre pas
- Tasks en état `STOPPED`

**Diagnostic:**
```bash
# Vérifier les logs CloudWatch
aws logs tail /ecs/arquantix-web --follow

# Vérifier les tasks
aws ecs list-tasks --cluster arquantix-cluster --service-name arquantix-web
```

**Solutions:**
1. **Vérifier la Task Definition:**
   - Vérifier l'image ECR (existe, tag correct)
   - Vérifier les variables d'environnement
   - Vérifier les ports (3000)

2. **Vérifier les logs CloudWatch:**
   - Lire les erreurs dans les logs
   - Vérifier les erreurs de démarrage

3. **Vérifier les permissions:**
   - Vérifier les permissions ECS (ecs:RunTask, etc.)
   - Vérifier les security groups (port 3000 ouvert)

---

## Commandes Utiles

```bash
# Voir tous les logs
docker compose -f docker-compose.arquantix.yml logs -f

# Restart un service
docker compose -f docker-compose.arquantix.yml restart arquantix-cms

# Entrer dans un container
docker compose -f docker-compose.arquantix.yml exec arquantix-cms sh

# Nettoyer complètement
docker compose -f docker-compose.arquantix.yml down -v
docker system prune -a

# Rebuild sans cache
docker compose -f docker-compose.arquantix.yml build --no-cache

# Vérifier le réseau
docker network inspect arquantix-network
```

---

**Dernière mise à jour:** 2026-01-01

