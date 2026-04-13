# Architectural Decision Records (ADRs) - Arquantix

**Date:** 2026-01-01  
**Status:** 🚧 En cours de développement

---

## TL;DR

Décisions architecturales pour le projet Arquantix, documentées selon le format ADR.

---

## Format ADR

Chaque ADR suit ce format:

```
## ADR-XXX: Titre

**Date:** YYYY-MM-DD  
**Status:** ✅ Adopté | 🚧 En cours | ❌ Rejeté | 🔄 Remplacé par ADR-YYY

### Contexte
Pourquoi cette décision est nécessaire.

### Décision
La décision prise.

### Conséquences
- Positives
- Négatives
- Alternatives considérées
```

---

## Ce qui est vrai aujourd'hui

### ADR-001: Structure Monorepo dans services/

**Date:** 2026-01-01  
**Status:** ✅ Adopté

**Contexte:**
Le repo `vancelian-app` existe déjà avec une structure `services/` pour organiser les services (ganopa-bot, arquantix/coming-soon). Il faut intégrer le nouveau site vitrine et CMS sans casser l'existant.

**Décision:**
Placer le site vitrine et CMS dans `services/arquantix/`:
- `services/arquantix/web/` (Next.js)
- `services/arquantix/cms/` (Strapi)
- `services/arquantix/coming-soon/` (existant, page statique)

**Conséquences:**
- ✅ Cohérent avec la structure existante
- ✅ Regroupe tous les services Arquantix ensemble
- ✅ N'interfère pas avec les autres services (ganopa-bot, etc.)
- ✅ Documentation dans `docs/arquantix/` (cohérent avec `docs/` global)

---

### ADR-002: Docker Compose Séparé (docker-compose.arquantix.yml)

**Date:** 2026-01-01  
**Status:** ✅ Adopté

**Contexte:**
Le repo n'a pas de `docker-compose.yml` à la racine. Pour éviter de casser l'existant et garder l'isolation, il faut un fichier Compose séparé pour Arquantix.

**Décision:**
Créer `docker-compose.arquantix.yml` à la racine, spécifique à Arquantix, avec ses propres services, volumes, et réseau.

**Conséquences:**
- ✅ N'interfère pas avec d'autres services (si un docker-compose.yml est ajouté plus tard)
- ✅ Isolation claire des services Arquantix
- ✅ Facile à démarrer/arrêter indépendamment
- ⚠️ Nécessite de spécifier `-f docker-compose.arquantix.yml` (atténué avec Makefile)

---

### ADR-003: Next.js 14 App Router

**Date:** 2026-01-01  
**Status:** ✅ Adopté

**Contexte:**
Besoin d'un framework React moderne pour le site vitrine, avec support SSR/SSG, routing, et i18n.

**Décision:**
Utiliser Next.js 14 avec App Router (pas Pages Router) pour:
- Routing moderne (dossiers)
- Server Components par défaut
- Meilleure performance
- Support TypeScript natif

**Conséquences:**
- ✅ Framework moderne et performant
- ✅ Excellent support TypeScript
- ✅ SSR/SSG intégré
- ✅ Routing simple (dossiers)
- ⚠️ App Router est relativement nouveau (mais stable dans Next.js 14)

---

### ADR-004: Strapi CMS (Headless)

**Date:** 2026-01-01  
**Status:** ✅ Adopté

**Contexte:**
Besoin d'un CMS pour gérer le contenu (pages, news, contact) avec i18n (FR/EN), sans avoir à modifier le code pour chaque changement de contenu.

**Décision:**
Utiliser Strapi 4.18 comme CMS headless:
- Open-source, auto-hébergé
- API REST native
- Plugin i18n intégré
- Interface d'administration moderne
- Extensible (plugins, customizations)

**Conséquences:**
- ✅ Flexibilité pour créer des Content Types personnalisés
- ✅ i18n intégré (FR/EN)
- ✅ API REST standard
- ✅ Auto-hébergé (pas de dépendance externe)
- ⚠️ Nécessite une base de données (PostgreSQL)
- ⚠️ Nécessite de déployer/maintenir Strapi (mais optionnel en prod pour le moment)

---

### ADR-005: PostgreSQL pour Strapi

**Date:** 2026-01-01  
**Status:** ✅ Adopté

**Contexte:**
Strapi nécessite une base de données. SQLite est simple mais pas adapté pour la production. PostgreSQL est robuste, standard, et supporté par Strapi.

**Décision:**
Utiliser PostgreSQL 15 (Alpine) comme base de données pour Strapi, même en développement local (pas SQLite).

**Conséquences:**
- ✅ Base de données robuste et standard
- ✅ Même stack dev/prod (pas de différences SQLite/Postgres)
- ✅ Support avancé (JSON, relations, etc.)
- ⚠️ Nécessite un container Docker (mais géré par Compose)
- ⚠️ Légèrement plus lourd que SQLite (mais acceptable)

---

### ADR-006: Ports Personnalisés (3001, 1338, 5433)

**Date:** 2026-01-01  
**Status:** ✅ Adopté

**Contexte:**
Les ports par défaut (3000, 1337, 5432) peuvent être utilisés par d'autres services. Il faut éviter les conflits.

**Décision:**
Utiliser des ports personnalisés:
- Next.js Web: 3001 (host) / 3000 (container)
- Strapi CMS: 1338 (host) / 1338 (container)
- PostgreSQL: 5433 (host) / 5432 (container)

**Conséquences:**
- ✅ Évite les conflits de ports avec d'autres services
- ✅ Facilement identifiable (ports Arquantix)
- ⚠️ Nécessite de se souvenir des ports (documenté dans README)

---

### ADR-007: Pas de Monorepo Tool (Nx/Turborepo/pnpm workspaces)

**Date:** 2026-01-01  
**Status:** ✅ Adopté

**Contexte:**
Le repo n'utilise pas de monorepo tool actuellement. Ajouter Nx/Turborepo/pnpm workspaces serait un changement architectural majeur.

**Décision:**
Ne pas introduire de monorepo tool. Garder les `package.json` indépendants dans chaque service. Utiliser Docker Compose pour orchestrer les services.

**Conséquences:**
- ✅ Pas de changement architectural majeur
- ✅ Simplicité (pas de configuration supplémentaire)
- ✅ Chaque service reste indépendant
- ⚠️ Pas de partage de dépendances (mais acceptable pour 2 services)
- ⚠️ Pas de build parallèle optimisé (mais Docker Compose gère bien)

---

### ADR-008: Strapi en Dev Local Uniquement (pour le moment)

**Date:** 2026-01-01  
**Status:** ✅ Adopté

**Contexte:**
Strapi nécessite une base de données et une infrastructure pour fonctionner en production. Pour le MVP, on peut se concentrer sur le déploiement du site vitrine (Next.js).

**Décision:**
Déployer uniquement Next.js en production pour le moment. Strapi reste en développement local. Le contenu peut être statique/généré au build, ou Strapi peut être déployé plus tard si nécessaire.

**Conséquences:**
- ✅ Déploiement simplifié (un seul service: Next.js)
- ✅ Moins d'infrastructure à gérer (pas de DB/Strapi en prod)
- ✅ Focus sur le MVP (site vitrine)
- ⚠️ Pas de CMS en prod (mais acceptable pour MVP)
- 🔄 Peut être changé plus tard (ADR futur: déployer Strapi en prod)

---

## À vérifier quand ça casse

### Si une décision doit être revue

1. **ADR-008 (Strapi en dev uniquement):**
   - Si besoin de CMS en prod, voir DEPLOYMENT.md pour les options
   - Créer un nouvel ADR pour documenter la décision de déployer Strapi

2. **ADR-007 (Pas de monorepo tool):**
   - Si le nombre de services augmente, considérer Nx/Turborepo
   - Créer un nouvel ADR pour documenter le passage à un monorepo tool

---

**Dernière mise à jour:** 2026-01-01

