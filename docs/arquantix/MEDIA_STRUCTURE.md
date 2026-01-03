# Structure des Médias Arquantix

## 📁 Structure des Fichiers

Tous les médias marketing statiques sont organisés dans `public/media/` :

```
public/
  media/
    logo/
      arquantix.svg          # Logo Arquantix (SVG)
    hero/
      slide-1.jpg            # Première image du carousel
      slide-2.jpg             # Deuxième image du carousel
```

## 🔗 URLs d'Accès

Les médias sont accessibles via des chemins absolus :

- **Logo:** `/media/logo/arquantix.svg`
- **Hero Slide 1:** `/media/hero/slide-1.jpg`
- **Hero Slide 2:** `/media/hero/slide-2.jpg`

## ✅ Avantages de cette Structure

1. **Chemins absolus robustes** : `/media/...` fonctionne partout (local, dev, staging, prod)
2. **Pas de dépendance S3** : Tous les médias sont servis directement par Next.js
3. **Sensible à la casse** : Structure claire évite les problèmes Linux/Windows
4. **Organisation claire** : Séparation logo / hero / autres médias futurs

## 📝 Fichiers à Ajouter

### Logo
- **Fichier:** `public/media/logo/arquantix.svg`
- **Format:** SVG (noir, inversé en blanc via CSS `filter: invert(1)`)
- **Taille recommandée:** 203px × 44.33px (selon design Figma)

### Images Hero
- **Fichiers:** 
  - `public/media/hero/slide-1.jpg`
  - `public/media/hero/slide-2.jpg`
- **Format:** JPG (optimisé pour web)
- **Taille recommandée:** 1920px × 1080px (ou ratio 16:9)

## 🐳 Docker / Build

Le Dockerfile copie correctement le dossier `public/` :

```dockerfile
COPY --from=builder /app/public ./public
```

Les fichiers sont accessibles dans le conteneur à :
- `/app/public/media/logo/arquantix.svg`
- `/app/public/media/hero/slide-1.jpg`
- `/app/public/media/hero/slide-2.jpg`

## 🧪 Vérification

### En Local
```bash
# Vérifier que les fichiers existent
ls -la services/arquantix/web/public/media/logo/
ls -la services/arquantix/web/public/media/hero/

# Tester les URLs (après démarrage du serveur)
curl http://localhost:3000/media/logo/arquantix.svg
curl http://localhost:3000/media/hero/slide-1.jpg
```

### En Production
```bash
# Vérifier dans le conteneur ECS
# Les fichiers doivent être dans /app/public/media/...

# Tester les URLs
curl https://arquantix.com/media/logo/arquantix.svg
curl https://arquantix.com/media/hero/slide-1.jpg
```

## 🔄 Migration depuis l'Ancienne Structure

Si vous avez des fichiers dans l'ancienne structure (`/logo-arquantix.svg`, `/hero.jpg`), déplacez-les :

```bash
# Logo
mv services/arquantix/web/public/logo-arquantix.svg \
   services/arquantix/web/public/media/logo/arquantix.svg

# Images Hero
mv services/arquantix/web/public/hero.jpg \
   services/arquantix/web/public/media/hero/slide-1.jpg
mv services/arquantix/web/public/hero-2.jpg \
   services/arquantix/web/public/media/hero/slide-2.jpg
```

## 📋 Composants Mis à Jour

Tous les composants utilisent maintenant les chemins absolus :

- ✅ `Navbar.tsx` : `/media/logo/arquantix.svg`
- ✅ `Footer.tsx` : `/media/logo/arquantix.svg`
- ✅ `Hero.tsx` : `/media/hero/slide-1.jpg`, `/media/hero/slide-2.jpg`
- ✅ `page.tsx` : `/media/hero/slide-1.jpg`, `/media/hero/slide-2.jpg`

## 🚫 Contraintes Respectées

- ✅ Pas de dépendance S3
- ✅ Pas de chemins relatifs fragiles
- ✅ Pas de logique spécifique à l'environnement
- ✅ Comportement identique partout (local / dev / staging / prod)

