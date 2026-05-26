# Arquantix Web (Next.js)

Site vitrine Arquantix : Next.js 14, TypeScript, Tailwind CSS, **Prisma** sur PostgreSQL, BFF vers l’API FastAPI. **Strapi n’est plus utilisé** ; `src/lib/strapi.ts` est un **stub** (pas d’appel réseau CMS).

## 🚀 Démarrage Rapide

### Avec Docker Compose (recommandé)

Depuis la racine du repo :

```bash
# Configurer .env.arquantix (COMPOSE_PROJECT_NAME, ARQUANTIX_COMPOSE_FILE, DB_*, ports…)

make -f Makefile.arquantix arquantix-up
# ou
make -f Makefile.arquantix arquantix-recovery-up
```

Le site est exposé sur le port **`WEB_PORT`** (souvent **3000**) : `http://localhost:${WEB_PORT}`.

### Développement local (sans Docker)

```bash
cd services/arquantix/web
npm install
# Configurer .env.local (DATABASE_URL, BACKEND_*, etc.) — aligné sur .env.arquantix
npm run dev
```

## 📋 Configuration

### Variables d'environnement

Principales : `DATABASE_URL` (Prisma), `BACKEND_URL` / `NEXT_PUBLIC_*` vers l’API — voir `.env.arquantix` et la doc [LOCAL_ENV_RUNBOOK.md](../../../docs/arquantix/LOCAL_ENV_RUNBOOK.md). **Pas de variables Strapi** requises.

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

## 🔌 Ancien module `strapi` (stub)

`lib/strapi.ts` exporte un **stub** (méthodes vides / données par défaut) pour éviter de casser d’anciens imports. Le contenu éditable passe par **Prisma** (pages, sections, blog, etc.) et les routes **FastAPI** pour le métier.

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
├── lib/             # Utilitaires (backend URL, Prisma, auth, stub strapi, …)
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

### Erreur de connexion à l’API / à la base

Vérifier que la stack Docker est up, que `DATABASE_URL` et `BACKEND_*` sont alignés sur `.env.arquantix`, et que `curl http://127.0.0.1:${API_PORT}/health` répond **200**.

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

**Dernière mise à jour:** 2026-05-26 (deploy DS portal + dashboard)

