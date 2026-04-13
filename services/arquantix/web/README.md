# Arquantix Web (Next.js)

Site vitrine Arquantix construit avec Next.js 14, TypeScript, Tailwind CSS, et intégration Strapi CMS.

## 🚀 Démarrage Rapide

### Avec Docker Compose (recommandé)

Depuis la racine du repo:

```bash
# Créer .env.arquantix si nécessaire
cp .env.arquantix.example .env.arquantix
# Éditer .env.arquantix avec vos valeurs

# Démarrer tous les services
make -f Makefile.arquantix arquantix-up

# Ou directement
docker compose -f docker-compose.arquantix.yml up -d
```

Le site sera accessible sur: http://localhost:3001

### Développement Local (sans Docker)

```bash
cd services/arquantix/web

# Installer les dépendances
npm install

# Créer .env.local (optionnel)
echo "NEXT_PUBLIC_STRAPI_URL=http://localhost:1338" > .env.local
echo "NEXT_PUBLIC_STRAPI_API_URL=http://localhost:1338/api" >> .env.local

# Démarrer le serveur de développement
npm run dev
```

Le site sera accessible sur: http://localhost:3000 (ou port configuré)

## 📋 Configuration

### Variables d'Environnement

- `NEXT_PUBLIC_STRAPI_URL`: URL de base du CMS Strapi (ex: http://localhost:1338)
- `NEXT_PUBLIC_STRAPI_API_URL`: URL de l'API Strapi (ex: http://localhost:1338/api)

En production, ces variables doivent être configurées dans l'environnement de déploiement.

## 🗺️ Routes

- `/` → Redirige vers `/fr`
- `/fr` → Page d'accueil (FR)
- `/en` → Page d'accueil (EN)
- `/fr/news` → Liste des actualités (FR)
- `/en/news` → Liste des actualités (EN)
- `/fr/news/[slug]` → Article de news (FR)
- `/en/news/[slug]` → Article de news (EN)
- `/fr/contact` → Formulaire de contact (FR)
- `/en/contact` → Formulaire de contact (EN)

## 🔌 Intégration Strapi

Le client Strapi est défini dans `lib/strapi.ts`.

Exemple d'utilisation:

```typescript
import { strapi } from '@/lib/strapi'

// Récupérer une page
const response = await strapi.get('/pages', {
  'filters[slug][$eq]': 'home',
  'filters[locale][$eq]': 'fr',
  populate: '*'
})

// Récupérer les news
const news = await strapi.get('/news', {
  'filters[locale][$eq]': 'fr',
  'pagination[limit]': 10,
  sort: 'publishedAt:desc',
  populate: '*'
})

// Soumettre un formulaire de contact
await strapi.post('/contact-submissions', {
  name: 'John Doe',
  email: 'john@example.com',
  message: 'Hello!'
})
```

## 🎨 Styling

Le projet utilise Tailwind CSS pour le styling.

Configuration dans `tailwind.config.ts`.

Styles globaux dans `src/styles/globals.css`.

## 🏗️ Structure

```
src/
├── app/              # App Router (Next.js 14)
│   ├── fr/          # Routes françaises
│   ├── en/          # Routes anglaises
│   ├── layout.tsx   # Layout racine
│   └── page.tsx     # Page d'accueil (redirection)
├── components/       # Composants React réutilisables
├── lib/             # Utilitaires (client Strapi, helpers)
└── styles/          # Styles globaux
```

## 🔨 Build & Déploiement

### Build de Production

```bash
npm run build
```

### Démarrage en Production

```bash
npm start
```

### Docker

Le Dockerfile est configuré pour une production optimisée avec:
- Multi-stage build
- Standalone output (Next.js)
- User non-root pour la sécurité

## 📚 Documentation

- [Next.js Documentation](https://nextjs.org/docs)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [TypeScript](https://www.typescriptlang.org/docs)

## 🐛 Dépannage

### Erreur de connexion à Strapi

Vérifier que:
1. Strapi est démarré et accessible
2. `NEXT_PUBLIC_STRAPI_URL` et `NEXT_PUBLIC_STRAPI_API_URL` sont correctement configurés
3. Les permissions API sont configurées dans Strapi

### Erreur de build

```bash
# Nettoyer le cache
rm -rf .next node_modules
npm install
npm run build
```

### Port déjà utilisé

En développement, Next.js utilise le port 3000 par défaut. Pour changer:
```bash
npm run dev -- -p 3001
```

---

**Dernière mise à jour:** 2026-01-01

