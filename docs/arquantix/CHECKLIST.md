# Checklist - Arquantix Vitrine + CMS

**Date:** 2026-01-01  
**Status:** 🚧 En cours de développement

---

## TL;DR

Checklists pour vérifier que l'environnement est prêt pour le développement et la production.

---

## Ce qui est vrai aujourd'hui

### Checklist Dev-Ready

Vérifier avant de commencer le développement local:

- [ ] **Docker & Docker Compose installés**
  ```bash
  docker --version
  docker compose version
  ```

- [ ] **Node.js installé** (optionnel, si développement sans Docker)
  ```bash
  node --version  # >= 18.0.0
  npm --version
  ```

- [ ] **Fichiers de configuration présents**
  - [ ] `.env.arquantix` existe (copier depuis `.env.arquantix.example` si disponible)
  - [ ] `docker-compose.arquantix.yml` existe
  - [ ] `Makefile.arquantix` existe (optionnel)

- [ ] **Secrets Strapi générés** (si `.env.arquantix` existe)
  - [ ] `CMS_APP_KEYS` contient 4 valeurs séparées par des virgules
  - [ ] `CMS_API_TOKEN_SALT` est défini
  - [ ] `CMS_ADMIN_JWT_SECRET` est défini
  - [ ] `CMS_JWT_SECRET` est défini
  - [ ] `CMS_TRANSFER_TOKEN_SALT` est défini
  
  **Générer les secrets:**
  ```bash
  # Générer un secret
  openssl rand -base64 32
  
  # Pour APP_KEYS, répéter 4 fois et séparer par des virgules
  # Exemple: key1,key2,key3,key4
  ```

- [ ] **Ports disponibles**
  ```bash
  lsof -i :3001  # Doit être vide
  lsof -i :1338  # Doit être vide
  lsof -i :5433  # Doit être vide
  ```

- [ ] **Code source présent**
  - [ ] `services/arquantix/web/` existe
  - [ ] `services/arquantix/cms/` existe
  - [ ] `services/arquantix/web/package.json` existe
  - [ ] `services/arquantix/cms/package.json` existe

- [ ] **Services démarrent correctement**
  ```bash
  make -f Makefile.arquantix arquantix-up
  # Attendre 30-60 secondes
  docker compose -f docker-compose.arquantix.yml ps
  # Tous les services doivent être "Up"
  ```

- [ ] **URLs accessibles**
  - [ ] http://localhost:3001 (Next.js) → 200 OK
  - [ ] http://localhost:1338/admin (Strapi Admin) → Page de login/création admin
  - [ ] http://localhost:1338/api (Strapi API) → JSON response

- [ ] **Strapi Admin créé**
  - [ ] Accéder à http://localhost:1338/admin
  - [ ] Créer un compte admin (premier démarrage)

- [ ] **Content Types créés** (optionnel pour démarrer, mais recommandé)
  - [ ] `global` (singleton)
  - [ ] `page` (collection)
  - [ ] `news` (collection)
  - [ ] `contactSubmission` (collection)
  - Voir CONTENT_MODEL.md pour les détails

- [ ] **Permissions API configurées** (optionnel pour démarrer, mais recommandé)
  - [ ] Aller dans Strapi Admin: Settings → Users & Permissions Plugin → Roles → Public
  - [ ] Activer: `global` (find), `page` (find, findOne), `news` (find, findOne), `contactSubmission` (create)

---

### Checklist Prod-Ready (Déploiement)

Vérifier avant de déployer en production:

- [ ] **Code prêt pour la production**
  - [ ] Pas de secrets en clair dans le code
  - [ ] Variables d'environnement documentées
  - [ ] `.env.*` dans `.gitignore`
  - [ ] Code linté (pas d'erreurs ESLint/TypeScript)

- [ ] **Build de production réussi**
  ```bash
  # Next.js
  cd services/arquantix/web
  npm run build
  # Pas d'erreurs

  # Strapi (si déployé)
  cd services/arquantix/cms
  npm run build
  # Pas d'erreurs
  ```

- [ ] **Dockerfiles optimisés**
  - [ ] Multi-stage builds (si applicable)
  - [ ] Pas de dépendances de développement en production
  - [ ] User non-root (sécurité)
  - [ ] Images de base légères (Alpine si possible)

- [ ] **Variables d'environnement production**
  - [ ] Tous les secrets sont générés (pas de valeurs par défaut)
  - [ ] `NODE_ENV=production`
  - [ ] URLs Strapi pointent vers la production
  - [ ] Base de données de production configurée (si Strapi déployé)

- [ ] **Workflow GitHub Actions configuré**
  - [ ] Workflow existe: `.github/workflows/arquantix-web-deploy.yml` (à créer)
  - [ ] Secrets GitHub configurés:
    - [ ] `AWS_ACCESS_KEY_ID`
    - [ ] `AWS_SECRET_ACCESS_KEY`
    - [ ] `AWS_REGION`
    - [ ] `ECR_REGISTRY`
    - [ ] `ECR_REPOSITORY`
  - [ ] Workflow teste le build avant push ECR
  - [ ] Workflow pousse vers le bon repo ECR

- [ ] **Infrastructure AWS prête**
  - [ ] ECR repository créé: `arquantix-web` (ou équivalent)
  - [ ] ECS cluster/service créé (si applicable)
  - [ ] ALB configuré (si applicable)
  - [ ] Domain/Route53 configuré (si applicable)
  - [ ] Certificat SSL/ACM configuré (si HTTPS)

- [ ] **Tests fonctionnels**
  - [ ] Site accessible (production URL)
  - [ ] Pages principales fonctionnent (/, /fr, /en, /news, /contact)
  - [ ] Intégration Strapi fonctionne (si Strapi en prod)
  - [ ] Formulaire de contact fonctionne (si applicable)
  - [ ] i18n fonctionne (FR/EN)

- [ ] **Monitoring & Logs**
  - [ ] CloudWatch logs configurés (si AWS)
  - [ ] Health checks configurés (si ALB/ECS)
  - [ ] Alerts configurés (optionnel)

---

## À vérifier quand ça casse

### Checklist Dev-Ready échoue

1. **Docker/Docker Compose non installé:**
   - Installer Docker Desktop (Mac/Windows) ou Docker Engine (Linux)

2. **Ports déjà utilisés:**
   - Arrêter les services utilisant les ports
   - Ou changer les ports dans `.env.arquantix` et `docker-compose.arquantix.yml`

3. **Secrets non générés:**
   - Générer avec `openssl rand -base64 32`
   - Mettre à jour `.env.arquantix`

4. **Services ne démarrent pas:**
   - Vérifier les logs: `docker compose -f docker-compose.arquantix.yml logs`
   - Vérifier les variables d'environnement
   - Vérifier les Dockerfiles

### Checklist Prod-Ready échoue

1. **Build échoue:**
   - Vérifier les erreurs de build (TypeScript, ESLint)
   - Vérifier les dépendances (package.json)
   - Vérifier les variables d'environnement requises

2. **Workflow GitHub Actions échoue:**
   - Vérifier les secrets GitHub
   - Vérifier les permissions AWS
   - Vérifier les paths dans le workflow (filtres)

3. **Infrastructure AWS manquante:**
   - Créer les ressources manquantes (ECR, ECS, ALB, etc.)
   - Vérifier les permissions IAM
   - Vérifier la région AWS

---

**Dernière mise à jour:** 2026-01-01

