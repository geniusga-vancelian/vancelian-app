# Checklist - Arquantix Vitrine + CMS

**Date:** 2026-01-01  
**Status:** 🚧 En cours de développement

> **2026** — Strapi n’est plus la stack locale de référence. Utiliser **[LOCAL_SETUP.md](./LOCAL_SETUP.md)** pour le dev-ready (Docker, ports, fichiers d’env). Les cases historiques Strapi ci‑dessous sont **obsolètes** pour le flux courant.

---

## TL;DR

Checklists pour vérifier que l'environnement est prêt pour le développement et la production.

---

## Ce qui est vrai aujourd'hui

### Checklist Dev-Ready (courant)

Suivre **[LOCAL_SETUP.md](./LOCAL_SETUP.md)** — en résumé :

- [ ] `.env.arquantix` présent ; `make setup` ou `make -f Makefile.arquantix arquantix-up`
- [ ] `make -f Makefile.arquantix local-doctor` et `local-db-doctor` sans erreur bloquante
- [ ] Web sur `http://127.0.0.1:${WEB_PORT:-3000}/fr` (ou route équivalente)
- [ ] Ports : `lsof -nP -iTCP:3000 -sTCP:LISTEN` (adapter si `WEB_PORT` différent)

### Archive — Strapi (non applicable au runtime Docker actuel)

Les points ci‑dessous concernaient un **ancien** scénario Strapi — **ne pas** les utiliser comme checklist du jour.

- [ ] ~~Secrets Strapi / ports 1338 / 3001~~ — voir LOCAL_SETUP et RUNBOOK.md

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

