# 🔍 AUDIT FOCALISÉ: arquantix-db Exit 255

**Date**: 2026-01-08  
**Container**: `arquantix-db`  
**Status initial**: `Exited (255)`  
**Status actuel**: ✅ `Up (healthy)` après `docker start`

---

## 📋 1. DÉFINITION DU CONTAINER

### Source de création
Le container `arquantix-db` est référencé dans:
- **Script**: `services/arquantix/start-all.sh` (ligne 36)
  ```bash
  docker compose --env-file .env.arquantix -f docker-compose.arquantix.yml up -d arquantix-db
  ```
- **Fichier attendu**: `docker-compose.arquantix.yml` (à la racine `vancelian-app/`)
- **Fichier .env**: `.env.arquantix` (présent à la racine)

**Note**: Le fichier `docker-compose.arquantix.yml` n'a pas été trouvé dans le repo, mais le container existe déjà avec une configuration persistante.

---

## 🔧 2. CONFIGURATION IDENTIFIÉE

### Image PostgreSQL
```yaml
Image: postgres:15-alpine
Version: PostgreSQL 15.15
Architecture: aarch64-unknown-linux-musl
```

### Variables d'environnement
```env
POSTGRES_USER=arquantix
POSTGRES_PASSWORD=arquantix
POSTGRES_DB=arquantix
PGDATA=/var/lib/postgresql/data
PG_MAJOR=15
PG_VERSION=15.15
```

### Ports
```yaml
Host: 5443 -> Container: 5432
Mapping: 0.0.0.0:5443->5432/tcp
```

### Volume
```yaml
Name: vancelian-app_arquantix-db-data
Type: Docker Volume
Mountpoint: /var/lib/docker/volumes/vancelian-app_arquantix-db-data/_data
Container Path: /var/lib/postgresql/data
Created: 2026-01-01T12:25:33Z
PG_VERSION: 15 (compatible)
```

### Healthcheck
```yaml
Test: pg_isready -U arquantix
Interval: 10s
Timeout: 5s
Retries: 5
Status actuel: healthy
```

### Network
```yaml
Network: vancelian-app_arquantix-network (bridge)
```

### Restart Policy
```yaml
Policy: no (MaximumRetryCount: 0)
⚠️ PROBLÈME: Pas de redémarrage automatique
```

---

## 🐛 3. DIAGNOSTIC: CAUSES PROBABLES EXIT 255

### Analyse des logs
Les logs ne montrent **aucune erreur fatale** avant l'arrêt:
- Dernier checkpoint normal: `2026-01-08 15:33:09 UTC`
- Container arrêté: `2026-01-08 15:48:50 UTC` (ExitCode: 255)
- Aucun message d'erreur dans les logs PostgreSQL

### Causes probables (par ordre de probabilité)

#### ✅ A) Arrêt manuel ou système (LE PLUS PROBABLE)
- **Preuve**: Pas d'erreur dans les logs, container simplement arrêté
- **Scénario**: 
  - Arrêt manuel (`docker stop arquantix-db`)
  - Redémarrage du système Docker Desktop
  - Redémarrage du Mac
- **Impact**: Aucun, le container redémarre sans problème

#### B) Restart Policy = "no"
- **Problème**: Le container n'a pas de politique de redémarrage automatique
- **Conséquence**: Si le container crash ou est arrêté, il ne redémarre pas automatiquement
- **Solution**: Modifier la restart policy (voir plan de recovery)

#### C) Problème de permissions (PEU PROBABLE)
- **Vérification**: Volume accessible, permissions correctes (UID 70 = postgres)
- **PG_VERSION**: 15 (compatible avec l'image postgres:15-alpine)
- **Conclusion**: Pas de problème de permissions ou de version

#### D) Problème réseau (PEU PROBABLE)
- **Vérification**: Network `vancelian-app_arquantix-network` existe et est actif
- **Conclusion**: Pas de problème réseau

---

## ✅ 4. VALIDATION: COMMANDES DE DIAGNOSTIC

### Commandes exécutées avec succès

```bash
# 1. Vérifier l'état du container
docker ps | grep arquantix-db
# Résultat: ✅ Up (healthy)

# 2. Vérifier la santé PostgreSQL
docker exec arquantix-db pg_isready -U arquantix
# Résultat: ✅ /var/run/postgresql:5432 - accepting connections

# 3. Tester la connexion
docker exec arquantix-db psql -U arquantix -d arquantix -c "SELECT version();"
# Résultat: ✅ PostgreSQL 15.15

# 4. Analyser les logs
docker logs arquantix-db --tail 200
# Résultat: ✅ Aucune erreur fatale, checkpoints normaux

# 5. Vérifier le volume
docker run --rm -v vancelian-app_arquantix-db-data:/data alpine cat /data/PG_VERSION
# Résultat: ✅ 15 (compatible)
```

### Relance simple (SUCCÈS)
```bash
docker start arquantix-db
# Résultat: ✅ Container démarré et healthy en 3 secondes
```

---

## 🔧 5. PLAN DE RECOVERY EN 3 NIVEAUX

### NIVEAU A: RELANCE SIMPLE (✅ TESTÉ ET FONCTIONNEL)

**Commande**:
```bash
docker start arquantix-db
```

**Vérification**:
```bash
# Attendre 5-10 secondes pour le healthcheck
docker ps | grep arquantix-db
docker exec arquantix-db pg_isready -U arquantix
```

**Résultat attendu**: Container `Up (healthy)`, PostgreSQL accepte les connexions.

**Quand utiliser**: 
- Container arrêté manuellement
- Redémarrage du système
- Pas d'erreur dans les logs

**Status**: ✅ **TESTÉ ET FONCTIONNEL**

---

### NIVEAU B: RECRÉER LE CONTAINER (NON DESTRUCTIF)

**Quand utiliser**:
- Le container ne démarre pas avec `docker start`
- Erreur de configuration détectée
- Besoin de modifier la restart policy

**Étapes**:

1. **Sauvegarder la configuration actuelle**:
```bash
docker inspect arquantix-db > /tmp/arquantix-db-backup.json
```

2. **Arrêter le container** (le volume reste intact):
```bash
docker stop arquantix-db
```

3. **Supprimer le container** (⚠️ PAS le volume):
```bash
docker rm arquantix-db
```

4. **Recréer le container avec la même configuration**:
```bash
docker run -d \
  --name arquantix-db \
  --network vancelian-app_arquantix-network \
  --restart unless-stopped \
  -p 5443:5432 \
  -e POSTGRES_USER=arquantix \
  -e POSTGRES_PASSWORD=arquantix \
  -e POSTGRES_DB=arquantix \
  -v vancelian-app_arquantix-db-data:/var/lib/postgresql/data \
  --health-cmd="pg_isready -U arquantix" \
  --health-interval=10s \
  --health-timeout=5s \
  --health-retries=5 \
  postgres:15-alpine
```

**Améliorations**:
- ✅ `--restart unless-stopped`: Redémarrage automatique
- ✅ Réutilisation du volume existant (données préservées)
- ✅ Même configuration réseau et ports

**Vérification**:
```bash
docker ps | grep arquantix-db
docker exec arquantix-db pg_isready -U arquantix
docker exec arquantix-db psql -U arquantix -d arquantix -c "\dt"
```

---

### NIVEAU C: MIGRATION/BACKUP VOLUME (DERNIER RECOURS)

**⚠️ À UTILISER UNIQUEMENT SI**:
- Le volume est corrompu
- Besoin de changer de version PostgreSQL
- Migration vers un autre host

**Étapes**:

1. **Backup du volume**:
```bash
# Créer un backup du volume
docker run --rm \
  -v vancelian-app_arquantix-db-data:/data \
  -v $(pwd):/backup \
  alpine tar czf /backup/arquantix-db-backup-$(date +%Y%m%d-%H%M%S).tar.gz -C /data .
```

2. **Backup via pg_dump** (recommandé):
```bash
# Si le container fonctionne encore
docker exec arquantix-db pg_dump -U arquantix arquantix > arquantix-db-dump-$(date +%Y%m%d-%H%M%S).sql

# Si le container ne fonctionne pas, utiliser un container temporaire
docker run --rm \
  --network vancelian-app_arquantix-network \
  -v vancelian-app_arquantix-db-data:/var/lib/postgresql/data:ro \
  postgres:15-alpine \
  pg_dump -U arquantix -h arquantix-db arquantix > backup.sql
```

3. **Restaurer depuis backup**:
```bash
# Option 1: Restaurer le volume
docker run --rm \
  -v vancelian-app_arquantix-db-data:/data \
  -v $(pwd):/backup \
  alpine tar xzf /backup/arquantix-db-backup-YYYYMMDD-HHMMSS.tar.gz -C /data

# Option 2: Restaurer depuis pg_dump
docker exec -i arquantix-db psql -U arquantix -d arquantix < backup.sql
```

---

## 📊 RÉSUMÉ ET RECOMMANDATIONS

### ✅ État actuel
- **Container**: ✅ `Up (healthy)`
- **PostgreSQL**: ✅ `15.15` - Accepte les connexions
- **Volume**: ✅ Intact, PG_VERSION 15 compatible
- **Network**: ✅ `vancelian-app_arquantix-network` actif
- **Port**: ✅ `5443` accessible

### ⚠️ Problèmes identifiés
1. **Restart Policy = "no"**: Le container ne redémarre pas automatiquement
2. **Fichier docker-compose manquant**: `docker-compose.arquantix.yml` non trouvé dans le repo

### 🔧 Actions recommandées

#### Immédiat (Optionnel)
```bash
# Le container fonctionne, aucune action urgente nécessaire
```

#### Court terme (Recommandé)
1. **Ajouter restart policy**:
```bash
docker update --restart unless-stopped arquantix-db
```

2. **Créer docker-compose.arquantix.yml** (pour faciliter la gestion):
```yaml
version: '3.8'
services:
  arquantix-db:
    image: postgres:15-alpine
    container_name: arquantix-db
    restart: unless-stopped
    ports:
      - "5443:5432"
    environment:
      POSTGRES_USER: arquantix
      POSTGRES_PASSWORD: arquantix
      POSTGRES_DB: arquantix
    volumes:
      - arquantix-db-data:/var/lib/postgresql/data
    networks:
      - arquantix-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U arquantix"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  arquantix-db-data:
    name: vancelian-app_arquantix-db-data

networks:
  arquantix-network:
    name: vancelian-app_arquantix-network
    external: true
```

#### Long terme (Optionnel)
- Automatiser le démarrage via `start-all.sh`
- Ajouter des backups automatiques
- Monitorer les logs pour détecter les arrêts inattendus

---

## 📝 COMMANDES RAPIDES

### Démarrer
```bash
docker start arquantix-db
```

### Arrêter
```bash
docker stop arquantix-db
```

### Vérifier l'état
```bash
docker ps | grep arquantix-db
docker exec arquantix-db pg_isready -U arquantix
```

### Voir les logs
```bash
docker logs arquantix-db --tail 50 -f
```

### Ajouter restart policy
```bash
docker update --restart unless-stopped arquantix-db
```

---

## ✅ CONCLUSION

**Cause racine**: Le container `arquantix-db` était simplement **arrêté** (probablement manuellement ou après redémarrage système). Aucune corruption de données, aucune erreur fatale.

**Solution immédiate**: ✅ `docker start arquantix-db` fonctionne parfaitement.

**Recommandation**: Ajouter `--restart unless-stopped` pour éviter les arrêts non désirés à l'avenir.





