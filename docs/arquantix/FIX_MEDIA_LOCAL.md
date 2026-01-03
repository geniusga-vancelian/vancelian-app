# Fix: Médias Non Servis en Local

**Date:** 2026-01-03  
**Problème:** Les fichiers dans `public/media/` retournent 404

---

## 🔍 Diagnostic

**Symptômes:**
- ✅ Serveur Next.js tourne (200 OK sur `/`)
- ❌ Fichiers médias retournent 404 (`/media/logo/arquantix.svg`)
- ✅ Fichiers présents dans le système de fichiers

**Cause:** Next.js n'a pas détecté les nouveaux fichiers dans `public/`

---

## ✅ Solution Rapide

### Option 1: Redémarrer le Serveur

```bash
# 1. Arrêter le serveur (Ctrl+C)

# 2. Redémarrer
cd services/arquantix/web
npm run dev
```

### Option 2: Nettoyer le Cache

```bash
cd services/arquantix/web

# Nettoyer le cache Next.js
rm -rf .next

# Redémarrer
npm run dev
```

---

## 🧪 Validation

Après redémarrage, tester :

```bash
# Logo
curl -I http://localhost:3000/media/logo/arquantix.svg
# Attendu: 200 OK

# Images Hero
curl -I http://localhost:3000/media/hero/slide-1.jpg
# Attendu: 200 OK

curl -I http://localhost:3000/media/hero/slide-2.jpg
# Attendu: 200 OK
```

---

## 📝 Notes

- Next.js en mode dev devrait détecter automatiquement les nouveaux fichiers
- Pour les fichiers volumineux (>5MB), un redémarrage peut être nécessaire
- Le cache `.next/` peut parfois bloquer la détection de nouveaux fichiers

---

**Status:** ✅ Solution identifiée - Redémarrer le serveur

