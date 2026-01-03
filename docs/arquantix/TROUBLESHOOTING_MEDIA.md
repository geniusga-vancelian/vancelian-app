# Troubleshooting Médias - Next.js Local

**Date:** 2026-01-03  
**Problème:** Les fichiers médias ne sont pas servis par Next.js en local

---

## 🔍 Diagnostic

### Symptômes
- Les fichiers existent dans `public/media/`
- Les URLs `http://localhost:3000/media/...` retournent 404 ou rien
- Le site s'affiche mais sans images/logo

---

## ✅ Vérifications

### 1. Fichiers Présents

```bash
cd services/arquantix/web
ls -la public/media/logo/
ls -la public/media/hero/
```

**Attendu:**
- `arquantix.svg` (3.7 KB)
- `slide-1.jpg` (8.9 MB)
- `slide-2.jpg` (7.8 MB)

### 2. Serveur Next.js Démarré

```bash
# Vérifier si le serveur tourne
curl http://localhost:3000/

# Ou vérifier le processus
lsof -i :3000
```

**Si le serveur ne tourne pas:**
```bash
cd services/arquantix/web
npm run dev
```

### 3. Structure du Projet

Le dossier `public/` doit être à la racine du projet Next.js :

```
services/arquantix/web/
  ├── public/
  │   └── media/
  ├── src/
  ├── package.json
  └── next.config.js
```

### 4. Test avec Fichier Simple

Créer un fichier de test :
```bash
echo "test" > services/arquantix/web/public/test.txt
```

Tester :
```bash
curl http://localhost:3000/test.txt
```

**Si ça fonctionne:** Le problème est spécifique aux médias  
**Si ça ne fonctionne pas:** Le problème est avec `public/` en général

---

## 🔧 Solutions

### Solution 1: Redémarrer le Serveur

```bash
# Arrêter le serveur (Ctrl+C)
# Puis redémarrer
cd services/arquantix/web
npm run dev
```

### Solution 2: Vérifier next.config.js

Le fichier `next.config.js` ne doit pas avoir de configuration qui bloque `public/` :

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pas de config qui bloque public/
}

module.exports = nextConfig
```

### Solution 3: Vérifier les Permissions

```bash
# Vérifier les permissions
ls -la services/arquantix/web/public/media/

# Si nécessaire, corriger
chmod -R 644 services/arquantix/web/public/media/
```

### Solution 4: Nettoyer le Build

```bash
cd services/arquantix/web
rm -rf .next
npm run dev
```

### Solution 5: Vérifier Docker (si utilisé)

Si vous utilisez Docker :

```bash
# Vérifier que public/ est bien copié
docker compose -f docker-compose.arquantix.yml exec arquantix-web ls -la /app/public/media/

# Si manquant, rebuild
docker compose -f docker-compose.arquantix.yml build --no-cache arquantix-web
docker compose -f docker-compose.arquantix.yml up -d arquantix-web
```

---

## 🐛 Problèmes Courants

### Problème 1: Serveur Non Démarré

**Symptôme:** `curl http://localhost:3000/` retourne erreur de connexion

**Solution:**
```bash
cd services/arquantix/web
npm run dev
```

### Problème 2: Port Différent

**Symptôme:** Le serveur tourne sur un autre port

**Vérifier:**
```bash
# Chercher le port utilisé
lsof -i :3000
lsof -i :3001
```

**Solution:** Utiliser le bon port ou configurer dans `package.json`

### Problème 3: Cache Navigateur

**Symptôme:** Les fichiers ne se chargent pas même après correction

**Solution:**
- Vider le cache (Cmd+Shift+R / Ctrl+Shift+R)
- Navigation privée
- DevTools > Network > Disable cache

### Problème 4: Fichiers Trop Gros

**Symptôme:** Les images JPG (8.9 MB, 7.8 MB) ne se chargent pas

**Solution:**
- Vérifier la limite de taille de Next.js
- Optimiser les images (réduire la taille)
- Utiliser Next.js Image component

---

## 📋 Checklist de Diagnostic

- [ ] Fichiers présents dans `public/media/`
- [ ] Serveur Next.js démarré (`npm run dev`)
- [ ] Serveur accessible sur `http://localhost:3000/`
- [ ] Fichier test (`/test.txt`) accessible
- [ ] Permissions correctes sur les fichiers
- [ ] Pas d'erreurs dans la console Next.js
- [ ] Pas d'erreurs dans la console navigateur
- [ ] Cache navigateur vidé

---

## 🧪 Tests de Validation

### Test 1: Fichier Simple

```bash
# Créer
echo "test" > services/arquantix/web/public/test.txt

# Tester
curl http://localhost:3000/test.txt
# Attendu: "test"
```

### Test 2: Logo SVG

```bash
curl -I http://localhost:3000/media/logo/arquantix.svg
# Attendu: 200 OK, Content-Type: image/svg+xml
```

### Test 3: Image Hero

```bash
curl -I http://localhost:3000/media/hero/slide-1.jpg
# Attendu: 200 OK, Content-Type: image/jpeg
```

---

## 📝 Notes

- Next.js sert automatiquement les fichiers depuis `public/` à la racine
- Les chemins dans le code doivent être absolus (`/media/...`)
- En mode dev, les fichiers sont servis directement
- En mode production, les fichiers sont copiés dans le build

---

**Dernière mise à jour:** 2026-01-03

