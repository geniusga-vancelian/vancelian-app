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
# Remplace par la racine de ton dépôt (ex. clone local)
cd ~/dev/vancelian-app
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

#### Copier le template

```bash
cp .env.example .env
```

Le fichier `.env.example` sert de template avec toutes les variables nécessaires.  
Le fichier `.env` est **local uniquement** et n'est **jamais commité** dans git.

#### Variables de base

Le fichier `.env` dans `services/arquantix/web/` doit contenir au minimum :

```env
DATABASE_URL="postgresql://arquantix:arquantix@localhost:5443/arquantix_admin"
AUTH_SECRET="dev-secret-change-me"
ADMIN_SEED_EMAIL="admin@local.dev"
ADMIN_SEED_PASSWORD="ChangeMeNow123!"
NEXT_PUBLIC_BASE_URL="http://localhost:3000"
```

**Note :** Le service `arquantix-db` utilise le port **5443** (pas 5432).

#### Cloudflare R2 configuration

Pour utiliser la bibliothèque de médias, vous devez configurer les credentials Cloudflare R2.

1. **Copiez le template** : Le fichier `.env.example` contient déjà la section R2 avec des valeurs vides.

2. **Récupérez vos credentials** depuis Cloudflare Dashboard :
   - Allez sur https://dash.cloudflare.com/
   - Accédez à **R2 Object Storage**
   - Créez un bucket (ex: `arquantix-media`) si nécessaire
   - Allez dans **Manage R2 API Tokens**
   - Créez un nouveau token avec les permissions **Object Read & Write**
   - Copiez l'**Access Key ID** et le **Secret Access Key**
   - Notez l'**Endpoint S3** (format: `https://<account-id>.r2.cloudflarestorage.com`)

3. **Remplissez votre `.env` local** (jamais commité) :

```env
### Cloudflare R2 — Media storage (S3 compatible)
R2_ACCESS_KEY_ID=votre-access-key-id
R2_SECRET_ACCESS_KEY=votre-secret-access-key
R2_BUCKET_NAME=arquantix-media
R2_ENDPOINT=https://votre-account-id.r2.cloudflarestorage.com
# Optionnel — domaine public custom Cloudflare
# R2_PUBLIC_URL=https://media.arquantix.com
```

**Important :**
- Le fichier `.env` est **local uniquement** et est ignoré par git (`.gitignore`)
- Ne **jamais** commiter de vraies clés dans le repository
- Le fichier `.env.example` sert uniquement de template avec des valeurs vides

#### OpenAI Translation configuration

Pour utiliser la fonctionnalité d'auto-traduction, vous devez configurer les credentials OpenAI.

1. **Récupérez votre clé API** depuis OpenAI Dashboard :
   - Allez sur https://platform.openai.com/api-keys
   - Créez une nouvelle clé API si nécessaire
   - Copiez la clé (format: `sk-...`)

2. **Remplissez votre `.env` local** (jamais commité) :

```env
### OpenAI Translation
OPENAI_API_KEY=sk-votre-cle-api-ici
OPENAI_MODEL=gpt-4o-mini
OPENAI_TRANSLATION_TEMPERATURE=0
OPENAI_TRANSLATION_MAX_CHARS=12000
```

**Important :**
- Le fichier `.env` est **local uniquement** et est ignoré par git (`.gitignore`)
- Ne **jamais** commiter de vraies clés dans le repository
- En production (ECS), ajoutez ces variables dans vos secrets ECS/CloudFormation
- Le fichier `.env.example` contient le template avec des valeurs vides

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

Cette commande créera un utilisateur super admin avec l'email et le mot de passe définis dans `.env`, ainsi que le contenu initial (page "home" avec sections).

**Note :** Le script de seed utilise un PrismaClient vanilla (runtime Node.js uniquement, pas d'Accelerate/Edge).

## Gestion du Contenu (Phase 2)

### Éditer les Pages et Sections

1. **Liste des pages** : `/admin/pages`
   - Affiche toutes les pages du site
   - Cliquez sur "Edit" pour gérer les sections d'une page

2. **Gérer les sections** : `/admin/pages/[slug]`
   - Liste toutes les sections d'une page
   - Cliquez sur "Edit" pour éditer une section

3. **Éditer une section** : `/admin/sections/[id]`
   - Sélectionnez la locale (fr, en, ar, it)
   - Choisissez entre "Draft" et "Published"
   - Éditez le JSON du contenu
   - Actions disponibles :
     - **Save Draft** : Sauvegarde le brouillon
     - **Publish** : Publie le brouillon (écrase la version publiée)
     - **Reset Draft** : Réinitialise le brouillon depuis la version publiée
     - **Preview** : Ouvre la page en mode preview

### Mode Preview

- URL : `/preview/[slug]?locale=xx`
- Accessible uniquement si vous êtes connecté en tant qu'admin
- Affiche le contenu DRAFT pour la locale sélectionnée
- Permet de prévisualiser les changements avant publication

### Workflow de Publication

1. Éditez une section en mode "Draft"
2. Modifiez le JSON du contenu
3. Cliquez sur "Save Draft" pour sauvegarder
4. Cliquez sur "Preview" pour voir le résultat
5. Une fois satisfait, cliquez sur "Publish" pour publier
6. Le contenu publié est visible sur le site public

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
- **Pages** (`/admin/pages`) : Gestion des pages et sections
- **Media** (`/admin/media`) : Bibliothèque de médias (images, vidéos, PDF)
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

## Media Library (Phase 3)

### Configuration Cloudflare R2

La bibliothèque de médias utilise Cloudflare R2 pour le stockage des fichiers. Vous devez configurer les credentials R2 dans votre fichier `.env`.

#### Obtenir les credentials R2 depuis Cloudflare

1. **Connectez-vous à Cloudflare Dashboard** : https://dash.cloudflare.com/
2. **Accédez à R2** : R2 Object Storage dans le menu
3. **Créez un bucket** (si nécessaire) :
   - Nom : `arquantix-media` (ou votre nom préféré)
   - Région : Auto (par défaut)
4. **Créez une API Token** :
   - Allez dans "Manage R2 API Tokens"
   - Cliquez sur "Create API Token"
   - Donnez-lui un nom (ex: `arquantix-media-token`)
   - Permissions : Object Read & Write
   - TTL : Permanent (ou selon vos besoins)
   - Cliquez sur "Create API Token"
5. **Copiez les informations** :
   - `Account ID` : Trouvé dans l'URL ou dans les paramètres du bucket
   - `Access Key ID` : Depuis le token créé
   - `Secret Access Key` : Depuis le token créé (à copier immédiatement, il n'est affiché qu'une fois)

#### Configuration des variables d'environnement

Ajoutez ces variables à votre fichier `.env` :

```env
# Cloudflare R2 Storage
R2_ACCOUNT_ID=your-account-id
R2_ACCESS_KEY_ID=your-access-key-id
R2_SECRET_ACCESS_KEY=your-secret-access-key
R2_BUCKET_NAME=arquantix-media
R2_PUBLIC_URL=https://your-custom-domain.com  # Optionnel : domaine custom pour URLs publiques
# MAX_UPLOAD_MB=20  # Optionnel : limite de taille d'upload (défaut: 20MB)
```

**Note :** Si `R2_PUBLIC_URL` n'est pas défini, les URLs publiques utiliseront le format R2 par défaut : `https://pub-<account-id>.r2.dev/<key>`

### Utilisation de la Media Library

1. **Accéder à la bibliothèque** : `/admin/media`
2. **Uploader un fichier** : Cliquez sur "Upload Media" et sélectionnez un fichier
3. **Rechercher** : Utilisez la barre de recherche pour filtrer par nom de fichier ou alt text
4. **Copier l'URL** : Cliquez sur "Copy URL" pour copier l'URL publique du fichier
5. **Supprimer** : Cliquez sur l'icône de suppression pour supprimer un fichier

### Formats supportés

- **Images** : JPEG, PNG, GIF, WebP, SVG
- **Vidéos** : MP4, WebM
- **Documents** : PDF

### Intégration dans les éditeurs

Le composant `MediaPicker` peut être intégré dans les éditeurs de sections pour sélectionner des médias :

```tsx
import { MediaPicker } from '@/components/admin/MediaPicker'

// Dans votre composant
<MediaPicker
  isOpen={isPickerOpen}
  onClose={() => setIsPickerOpen(false)}
  onSelect={(media) => {
    // Mettre à jour le contenu avec media.id
  }}
  currentMediaId={currentMediaId}
/>
```

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

