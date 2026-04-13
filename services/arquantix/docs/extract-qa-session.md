# Extract Questions / Réponses — session assistance

*Document généré automatiquement à partir des échanges (Arquantix — admin web, Flutter welcome, R2, Media Library, Prisma).*

---

## 1. Admin web — Login0, déconnexion, inscription

**Q :** Ajouter un mini bouton Déconnexion (navbar en haut à droite) sur la page de login, redirigeant vers une page « Login0 » avec deux boutons Login et Signup.

**R :**
- Page **`/admin/login0`** : Connexion → `/admin/login`, Inscription → `/admin/signup`.
- Page login : barre supérieure avec **Déconnexion** → `POST /api/admin/logout` puis redirection vers `/admin/login0`.
- **`middleware.ts`** et **`admin/layout.tsx`** : accès sans session pour `login0` et `signup`.
- Stub **`/admin/signup`** (message + retour vers login0) tant qu’il n’y a pas de vrai flux.

---

## 2. Page Login0 (Next.js) — fond et mise en page

**Q :** Image en arrière-plan ; navbar vide en haut ; logo Vancelian en dessous (sans titre ni boutons sur la navbar).

**R :**
- Image dans **`web/public/images/admin/login0-bg.png`** ; fond `bg-cover` + voile pour la lisibilité.
- Bandeau vide sous la status bar ; logo blanc centré sous la navbar ; carte Connexion / Inscription.

---

## 3. Flutter — écran welcome, asset `hero.png`

**Q :** L’image ne charge pas (`Asset not found` pour `assets/welcome/hero.png`) malgré hot restart.

**R :**
- Création du dossier **`assets/welcome/`** et du fichier **`hero.png`**.
- **`pubspec.yaml`** : déclarer explicitement **`assets/welcome/`** (un répertoire `assets/` seul n’inclut pas toujours les sous-dossiers).
- **`flutter pub get`** puis **rebuild complet** (pas seulement hot restart).

---

## 4. Flutter — image héro dynamique via R2 / S3

**Q :** Héberger l’image sur le media R2/S3 et l’utiliser par lien dynamique.

**R :**
- **`GET /api/mobile/flutter/welcome`** : renvoie `{ heroImageUrl }` (priorité `WELCOME_HERO_IMAGE_URL`, sinon clé R2 `WELCOME_HERO_R2_KEY`, option presignée).
- Script **`npm run upload:welcome-hero`** (upload vers R2, import dynamique après chargement `.env`).
- Flutter : fetch BFF + **`CachedNetworkImage`**, repli asset local si besoin.

---

## 5. Flutter welcome — navbar, marges logo, image toujours KO

**Q :** Navbar en haut (vide) ; logo en dessous ; marges haut/bas autour du logo ; corriger le chargement média.

**R :**
- **`SafeArea` + bandeau** `kToolbarHeight` ; **`AppSpacing.s2`** (8 px) au-dessus et en dessous du logo.
- Chaîne d’URL : **`WELCOME_HERO_DIRECT_URL`** (dart-define) → BFF → URL R2 publique par défaut (`pub-…r2.dev/.../hero.png`) si BFF injoignable (ex. téléphone sans bon `API_BASE_URL`).
- **`pubspec.yaml`** : aussi **`assets/welcome/hero.png`** en entrée explicite ; **`Image.asset`** avec **`errorBuilder`** pour éviter l’erreur en cascade.

---

## 6. Admin — Media Library bloquée, migrations / redémarrages

**Q :** Accès media ne fonctionne pas comme le reste de l’admin ; migration ou redémarrage web + API ?

**R :**
- Les **404 sur `/_next/static/chunks/...`** viennent du **cache/build Next (`.next`)**, pas du backend Python. La Media Library utilise **Next + Prisma + R2** (`/api/admin/media`), pas FastAPI.
- Action typique : **`rm -rf .next`**, relancer **`npm run dev`** (ou **`npm run dev:clean`**), rechargement forcé du navigateur.
- **Prisma** : `migrate status` peut être « up to date » ; migrations nécessaires seulement si une base n’a pas été migrée.
- Renforts code : **`credentials: 'include'`**, timeout sur le fetch liste médias.

---

## 7. Commande Prisma

**Q :** `npx prisma migrate status`

**R :** Exécution dans **`services/arquantix/web`** : 51 migrations, base PostgreSQL configurée dans `.env`, message **Database schema is up to date!** lorsque tout est appliqué.

---

## 8. Cette demande

**Q :** Faire un extract PDF de toutes ces questions-réponses.

**R :** Ce fichier Markdown source : **`docs/extract-qa-session.md`** ; le PDF livré est **`docs/extract-qa-session.pdf`** (généré par la même passe d’outillage).

---

*Fin du document.*
