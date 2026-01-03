# Configuration Médias en Local - Arquantix

**Date:** 2026-01-03  
**Objectif:** S'assurer que les médias fonctionnent correctement en local

---

## 📁 Structure des Médias

Les médias sont organisés dans `public/media/` :

```
public/
  media/
    logo/
      arquantix.svg          (3.7 KB)
    hero/
      slide-1.jpg            (8.9 MB)
      slide-2.jpg            (7.8 MB)
```

---

## ✅ Vérification Git

Les fichiers médias sont trackés par Git :
- **Commit:** `6cd3536f` - "Add media assets: logo and hero carousel images"
- **Fichiers trackés:**
  - `services/arquantix/web/public/media/hero/slide-1.jpg`
  - `services/arquantix/web/public/media/hero/slide-2.jpg`
  - `services/arquantix/web/public/media/logo/arquantix.svg`

---

## 🔍 Vérification en Local

### 1. Vérifier que les fichiers existent

```bash
cd services/arquantix/web
ls -lh public/media/hero/
ls -lh public/media/logo/
```

**Attendu:**
- `slide-1.jpg` (8.9 MB)
- `slide-2.jpg` (7.8 MB)
- `arquantix.svg` (3.7 KB)

### 2. Vérifier que le serveur Next.js tourne

```bash
npm run dev
# ou
docker compose -f docker-compose.arquantix.yml up arquantix-web
```

### 3. Tester les URLs

Ouvrir dans le navigateur :
- `http://localhost:3000/media/logo/arquantix.svg`
- `http://localhost:3000/media/hero/slide-1.jpg`
- `http://localhost:3000/media/hero/slide-2.jpg`

**Attendu:** Les fichiers doivent s'afficher/télécharger.

### 4. Vérifier la page principale

Ouvrir :
- `http://localhost:3000/`

**Vérifier:**
- Le logo s'affiche dans la Navbar
- Le logo s'affiche dans le Footer
- Le carousel Hero affiche les images

---

## 🐛 Problèmes Courants

### Les médias ne s'affichent pas

**Cause 1: Fichiers manquants**
```bash
# Vérifier que les fichiers existent
ls -la services/arquantix/web/public/media/hero/
ls -la services/arquantix/web/public/media/logo/

# Si manquants, récupérer depuis Git
git checkout HEAD -- services/arquantix/web/public/media/
```

**Cause 2: Serveur Next.js non démarré**
```bash
# Démarrer le serveur
cd services/arquantix/web
npm run dev
```

**Cause 3: Cache du navigateur**
- Vider le cache (Cmd+Shift+R sur Mac, Ctrl+Shift+R sur Windows)
- Ouvrir en navigation privée

**Cause 4: Chemins incorrects dans le code**
```bash
# Vérifier les chemins utilisés
grep -r "media/hero\|media/logo" services/arquantix/web/src/
```

**Attendu:**
- `/media/logo/arquantix.svg`
- `/media/hero/slide-1.jpg`
- `/media/hero/slide-2.jpg`

---

## 📋 Checklist de Vérification

- [ ] Fichiers médias présents dans `public/media/`
- [ ] Serveur Next.js démarré
- [ ] URLs directes fonctionnent (`/media/...`)
- [ ] Logo visible dans Navbar
- [ ] Logo visible dans Footer
- [ ] Images carousel visibles dans Hero
- [ ] Aucune erreur 404 dans la console navigateur

---

## 🔄 Synchronisation avec le Repo

Si les fichiers médias ne sont pas à jour :

```bash
# Récupérer depuis Git
git pull origin main

# Vérifier que les fichiers sont présents
ls -la services/arquantix/web/public/media/hero/
ls -la services/arquantix/web/public/media/logo/
```

---

## 📝 Notes

- Les fichiers médias sont trackés par Git (pas de .gitignore)
- Les images hero sont volumineuses (8.9 MB et 7.8 MB) mais sous la limite GitHub (100 MB)
- Les chemins sont absolus (`/media/...`) pour fonctionner partout (local, dev, prod)

---

**Dernière mise à jour:** 2026-01-03

