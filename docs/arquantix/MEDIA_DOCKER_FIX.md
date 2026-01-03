# Fix: Médias en Docker Local

**Date:** 2026-01-03  
**Problème:** Les médias ne s'affichent pas en local (Docker)

---

## 🔍 Diagnostic

**Symptômes:**
- Serveur Arquantix tourne en Docker sur `http://localhost:3011`
- Les fichiers médias existent localement dans `public/media/`
- Les URLs `http://localhost:3011/media/...` retournent 404

**Cause:** Les fichiers médias ne sont pas dans l'image Docker (ajoutés après le dernier build)

---

## ✅ Solutions

### Solution 1: Rebuild l'Image Docker

```bash
# Trouver le fichier docker-compose
# (généralement docker-compose.yml ou docker-compose.arquantix.yml)

# Rebuild avec les médias
docker compose build --no-cache arquantix-web

# Redémarrer
docker compose up -d arquantix-web
```

### Solution 2: Copier les Fichiers dans le Conteneur (Temporaire)

```bash
# Copier les médias dans le conteneur en cours
docker cp services/arquantix/web/public/media arquantix-web:/app/public/

# Redémarrer le conteneur
docker restart arquantix-web
```

**Note:** Cette solution est temporaire, les fichiers seront perdus au prochain restart.

### Solution 3: Attendre le Build Automatique

Les fichiers médias sont dans le repo Git. Le prochain build GitHub Actions les inclura automatiquement.

---

## 🧪 Validation

Après rebuild, tester :

```bash
# Logo
curl -I http://localhost:3011/media/logo/arquantix.svg
# Attendu: 200 OK

# Images Hero
curl -I http://localhost:3011/media/hero/slide-1.jpg
# Attendu: 200 OK

curl -I http://localhost:3011/media/hero/slide-2.jpg
# Attendu: 200 OK
```

---

## 📋 Checklist

- [ ] Fichiers médias présents localement dans `public/media/`
- [ ] Fichiers trackés par Git
- [ ] Image Docker rebuildée avec `--no-cache`
- [ ] Conteneur redémarré
- [ ] URLs testées sur `http://localhost:3011/media/...`
- [ ] Médias visibles dans le navigateur

---

## 🔄 Workflow Recommandé

1. **Ajouter les fichiers médias** dans `public/media/`
2. **Commit et push** sur GitHub
3. **GitHub Actions** build automatiquement l'image avec les médias
4. **En local:** Rebuild l'image Docker pour tester

---

**Dernière mise à jour:** 2026-01-03

