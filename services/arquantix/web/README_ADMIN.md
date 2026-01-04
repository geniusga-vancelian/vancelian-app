# Arquantix CMS - Setup Admin

Ce document décrit comment configurer et utiliser le CMS admin d'Arquantix.

## Prérequis

- Node.js 18+
- PostgreSQL (local ou distant)
- Variables d'environnement configurées (voir `.env.example`)

## Installation

### 1. Démarrer PostgreSQL (Docker)

Le service PostgreSQL `arquantix-db` existe déjà dans votre environnement Docker.

Vérifier qu'il est démarré :

```bash
cd /Users/gael/Library/CloudStorage/OneDrive-Vancelian/Documents/vancelian-app
docker compose ps arquantix-db
```

Si le service n'est pas démarré, le démarrer avec :

```bash
docker compose -f docker-compose.arquantix.yml up -d arquantix-db
```

Le service utilise :
- **Port :** 5443 (host) -> 5432 (container)
- **User :** arquantix
- **Password :** arquantix
- **Database :** arquantix

### 2. Installer les dépendances

```bash
cd services/arquantix/web
npm install
```

### 3. Configurer les variables d'environnement

Le fichier `.env` dans `services/arquantix/web/` doit contenir :

```env
DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix_admin"
AUTH_SECRET="dev-secret-change-me"
ADMIN_SEED_EMAIL="admin@local.dev"
ADMIN_SEED_PASSWORD="ChangeMeNow123!"
NEXT_PUBLIC_BASE_URL="http://localhost:3000"
```

**Note :** Le service `arquantix-db` utilise le port **5443** (pas 5432).

### 4. Générer le client Prisma

```bash
npm run db:generate
```

**Note :** Ce projet utilise Prisma v6.x pour la stabilité et la compatibilité avec PrismaClient vanilla (sans adapter/accelerate requis par v7).

### 5. Exécuter les migrations

```bash
npm run db:migrate
```

Cette commande créera les tables `users` et `sessions` dans votre base de données.

### 6. Créer le super admin

```bash
npm run db:seed
```

Cette commande créera un utilisateur super admin avec l'email et le mot de passe définis dans `.env`.

**Note :** Le script de seed utilise un PrismaClient vanilla (runtime Node.js uniquement, pas d'Accelerate/Edge).

## Utilisation

### Démarrer le serveur de développement

```bash
npm run dev
```

Le site sera accessible sur `http://localhost:3000`.

### Accéder à l'admin

1. Allez sur `http://localhost:3000/admin/login`
2. Connectez-vous avec les identifiants du super admin créé par le seed :
   - Email : `admin@local.dev` (par défaut)
   - Password : `ChangeMeNow123!` (par défaut)

### Structure de l'admin

- **Dashboard** (`/admin`) : Vue d'ensemble
- **Pages** (`/admin/pages`) : Gestion des pages (à venir)
- **Media** (`/admin/media`) : Gestion des médias (à venir)
- **Settings** (`/admin/settings`) : Paramètres (à venir)

## Commandes disponibles

- `npm run dev` : Démarrer le serveur de développement
- `npm run build` : Builder pour la production
- `npm run start` : Démarrer le serveur de production
- `npm run db:migrate` : Exécuter les migrations Prisma
- `npm run db:seed` : Créer le super admin
- `npm run db:generate` : Régénérer le client Prisma
- `npm run db:studio` : Ouvrir Prisma Studio (GUI pour la DB)

## Architecture

### Authentification

- Sessions stockées en base de données (table `sessions`)
- Cookie httpOnly : `arq_admin_session`
- Durée de session : 7 jours
- Hash de mot de passe : bcrypt (10 rounds)

### Sécurité

- Toutes les routes `/admin/*` sont protégées (sauf `/admin/login`)
- Middleware vérifie la session avant d'autoriser l'accès
- Cookies sécurisés en production (`secure: true`)
- Validation des inputs avec Zod

### Base de données

- **User** : Utilisateurs admin
  - `id` : CUID
  - `email` : Unique
  - `passwordHash` : Hash bcrypt
  - `role` : SUPER_ADMIN | ADMIN
  - `createdAt` : Timestamp

- **Session** : Sessions actives
  - `id` : CUID
  - `userId` : Foreign key vers User
  - `token` : Token unique (32 bytes hex)
  - `expiresAt` : Date d'expiration
  - `createdAt` : Timestamp

## Développement

### Ajouter une nouvelle route admin

1. Créer la page dans `src/app/admin/ma-route/page.tsx`
2. Le middleware protégera automatiquement la route
3. Utiliser `getSessionFromCookie()` pour récupérer l'utilisateur connecté

### Ajouter une nouvelle API

1. Créer la route dans `src/app/api/admin/ma-route/route.ts`
2. Vérifier la session avec `getSessionFromCookie()`
3. Retourner `401` si non authentifié

## Dépannage

### "Not authenticated" après connexion

- Vérifier que le cookie est bien défini (DevTools > Application > Cookies)
- Vérifier que `AUTH_SECRET` est défini dans `.env`
- Vérifier les logs du serveur pour les erreurs

### Migration échoue

- Vérifier que PostgreSQL est démarré
- Vérifier que `DATABASE_URL` est correct
- Vérifier que la base de données existe

### Seed échoue

- Vérifier que `ADMIN_SEED_EMAIL` et `ADMIN_SEED_PASSWORD` sont définis
- Vérifier que la migration a bien été exécutée
- Vérifier qu'un utilisateur avec cet email n'existe pas déjà

