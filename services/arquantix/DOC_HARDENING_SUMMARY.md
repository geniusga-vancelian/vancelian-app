# 📋 DOC HARDENING — Résumé des Modifications

**Date:** 2026-01-08  
**Objectif:** Supprimer Strapi, créer documentation claire, ajouter guardrails

---

## ✅ Fichiers Créés

### 1. `README.md` (Source de vérité)
- Architecture claire (3 services: DB, API, Web)
- ⚠️ Section explicite: "Strapi n'est plus utilisé"
- Configuration des variables d'environnement
- Section "Run Local — 5 minutes"
- Section "Common Failures" avec diagnostics
- Section "Hardening" (restart policy)
- Tableau des ports et bases de données

### 2. `START_ARQUANTIX.md` (Guide pas-à-pas)
- Guide complet étape par étape
- Prérequis détaillés
- Vérifications de santé
- Troubleshooting avec commandes copiables
- Commandes rapides (happy path + diagnostic)

### 3. `docs/STRAPI_DEPRECATED.md`
- Note explicite que Strapi n'est plus utilisé
- Liste des fichiers conservés pour référence

---

## 📝 Fichiers Modifiés

### 1. `START_SERVERS.md`
- ⚠️ Marqué comme **DEPRECATED** en haut du fichier
- Toutes les références à Strapi retirées
- Ports corrigés (5433 → 5443)
- Pointe vers `START_ARQUANTIX.md` et `README.md`

### 2. `start-all.sh`
- **Strapi retiré** (plus de démarrage CMS)
- **Guardrails DB ajoutés:**
  - Vérifie que `arquantix-db` est démarré et healthy
  - Vérifie la connexion PostgreSQL avant de démarrer Web/API
  - Vérifie que `DATABASE_URL` pointe vers le bon port (5443) dans `.env`
  - Affiche des messages d'erreur clairs si problème
- Utilise `python3 -m uvicorn` au lieu de `uvicorn` directement
- URLs mises à jour (CMS retiré)

### 3. `stop-all.sh`
- **Strapi retiré** (plus d'arrêt CMS)
- Processus Strapi retiré de la boucle

---

## 🚀 Commandes "Happy Path" (Copier/Coller)

### Démarrer tout Arquantix

```bash
# 1. Démarrer DB + vérifier
docker start arquantix-db && sleep 5 && docker ps | grep arquantix-db

# 2. Configurer restart policy (une seule fois)
docker update --restart unless-stopped arquantix-db

# 3. Démarrer API (Terminal 1)
cd services/arquantix/api && python3 -m uvicorn main:app --reload --port 8000

# 4. Démarrer Web (Terminal 2)
cd services/arquantix/web && npm run dev
```

**URLs:**
- Web: http://localhost:3000
- API: http://localhost:8000/docs
- Admin: http://localhost:3000/admin/login

---

## 🔍 Commande "Diagnostic" (Copier/Coller)

### Vérifier l'état complet

```bash
# 1. Vérifier DB
echo "=== DATABASE ===" && \
docker ps | grep arquantix-db && \
docker exec arquantix-db pg_isready -U arquantix && \
docker inspect arquantix-db --format 'RestartPolicy: {{.HostConfig.RestartPolicy.Name}}'

# 2. Vérifier ports
echo "" && echo "=== PORTS ===" && \
lsof -i -P | grep LISTEN | grep -E "3000|8000|5443"

# 3. Vérifier configs DB
echo "" && echo "=== CONFIGS ===" && \
echo "WEB:" && cat services/arquantix/web/.env | grep DATABASE_URL && \
echo "API:" && cat services/arquantix/api/.env | grep DATABASE_URL

# 4. Vérifier logs
echo "" && echo "=== LOGS (dernières 5 lignes) ===" && \
echo "WEB:" && tail -5 /tmp/arquantix-web.log 2>/dev/null || echo "Pas de logs Web" && \
echo "API:" && tail -5 /tmp/arquantix-api.log 2>/dev/null || echo "Pas de logs API" && \
echo "DB:" && docker logs arquantix-db --tail 5
```

---

## 📊 Tableau des Ports (Source de Vérité)

| Service | Port Host | Port Container | Container Name | Base de Données |
|---------|-----------|----------------|----------------|-----------------|
| **arquantix-db** | `5443` | `5432` | `arquantix-db` | `arquantix`, `arquantix_admin` |
| **API** | `8000` | - | - | `arquantix` |
| **Web** | `3000` | - | - | `arquantix_admin` |

**⚠️ IMPORTANT:**
- Ne pas utiliser `zitadel-db` (port 5434) pour Arquantix
- Ne pas utiliser le port 5433 (inexistant)

---

## ✅ Vérifications Post-Modification

### 1. Strapi retiré
- ✅ `start-all.sh` ne démarre plus Strapi
- ✅ `stop-all.sh` n'arrête plus Strapi
- ✅ `START_SERVERS.md` marqué comme DEPRECATED
- ✅ `README.md` indique explicitement que Strapi n'est plus utilisé

### 2. Ports alignés
- ✅ Web: `localhost:5443` (arquantix-db)
- ✅ API: `localhost:5443` (arquantix-db)
- ✅ Scripts vérifient le port avant démarrage

### 3. Guardrails DB
- ✅ `start-all.sh` vérifie que `arquantix-db` est healthy
- ✅ `start-all.sh` vérifie la connexion PostgreSQL
- ✅ `start-all.sh` vérifie que `DATABASE_URL` pointe vers 5443
- ✅ Documentation mentionne la restart policy

### 4. Documentation claire
- ✅ `README.md` = source de vérité
- ✅ `START_ARQUANTIX.md` = guide pas-à-pas
- ✅ Section "Common Failures" avec diagnostics
- ✅ Commandes copiables partout

---

## 📚 Navigation Documentation

1. **Pour démarrer rapidement:** [README.md](./README.md) → Section "Run Local — 5 minutes"
2. **Pour guide détaillé:** [START_ARQUANTIX.md](./START_ARQUANTIX.md)
3. **Pour troubleshooting:** [README.md](./README.md) → Section "Common Failures"
4. **Pour historique Strapi:** [docs/STRAPI_DEPRECATED.md](./docs/STRAPI_DEPRECATED.md)

---

## 🎯 Prochaines Étapes Recommandées

1. **Tester le démarrage:**
   ```bash
   cd services/arquantix
   ./start-all.sh --background
   ```

2. **Vérifier que tout fonctionne:**
   - Web: http://localhost:3000
   - API: http://localhost:8000/docs

3. **Configurer restart policy (une fois):**
   ```bash
   docker update --restart unless-stopped arquantix-db
   ```

---

**Dernière mise à jour:** 2026-01-08





