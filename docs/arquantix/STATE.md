# State - Arquantix Vitrine + CMS

**Date:** 2026-01-01  
**Status:** 🚧 En cours de création

---

## TL;DR

Ajout d'un site vitrine Arquantix (Next.js) + CMS (Strapi) dans le repo existant `vancelian-app`, en suivant les patterns existants (`services/`), sans casser l'existant.

---

## Ce qui est vrai aujourd'hui

### Structure du Repository Existante

**Analyse effectuée le:** 2026-01-01

```
vancelian-app/
├── services/              # Services backend/frontend
│   ├── ganopa-bot/       # Service Telegram bot (Python/FastAPI)
│   └── arquantix/        # Services Arquantix
│       └── coming-soon/  # Page "Coming Soon" statique (S3/CloudFront)
├── agent/                # Agent IA (Python)
├── agent_gateway/        # Gateway Telegram → GitHub Actions (Python/FastAPI)
├── docs/                 # Documentation globale
├── product/              # Product specs, brainstorms
├── scripts/              # Scripts utilitaires
├── .github/workflows/    # GitHub Actions workflows
├── Dockerfile            # (à la racine, usage non clair)
├── main.py               # (à la racine, usage non clair)
└── requirements.txt      # (à la racine, Python)
```

### Observations Clés

1. **Pattern de services:**
   - Les services sont organisés dans `services/`
   - Chaque service a son propre Dockerfile
   - Pas de docker-compose.yml à la racine
   - Pas de monorepo tool (Nx/Turborepo/pnpm workspaces)

2. **Technologies existantes:**
   - Python (FastAPI) pour les services backend
   - Docker pour la containerisation
   - GitHub Actions pour CI/CD
   - AWS ECS/ECR pour le déploiement

3. **Services Arquantix existants:**
   - `services/arquantix/coming-soon/` existe déjà
   - Workflow GitHub Actions: `arquantix-push-to-ecr.yml`
   - Infrastructure AWS: S3 + CloudFront + Route53

4. **Documentation:**
   - Documentation globale dans `docs/`
   - Documentation spécifique par service dans le dossier du service

### Décision d'Emplacement

**Emplacement choisi:** `services/arquantix/`

**Structure à créer:**
```
services/arquantix/
├── coming-soon/          # ✅ Existant (page statique)
├── web/                  # 🆕 Site vitrine Next.js
│   ├── Dockerfile
│   ├── package.json
│   ├── next.config.js
│   ├── src/
│   └── ...
└── cms/                  # 🆕 CMS Strapi
    ├── Dockerfile
    ├── package.json
    ├── config/
    ├── src/
    └── ...
```

**Documentation:** `docs/arquantix/`

**Raisons:**
1. ✅ Cohérent avec le pattern existant (`services/`)
2. ✅ Regroupe tous les services Arquantix ensemble
3. ✅ N'interfère pas avec les autres services
4. ✅ Documentation dans `docs/arquantix/` (cohérent avec `docs/` global)

### Ports Choisis

Pour éviter les conflits avec les services existants:

- **Next.js Web:** `3001` (évite conflit avec 3000 si utilisé ailleurs)
- **Strapi CMS:** `1338` (évite conflit avec 1337 si utilisé ailleurs)
- **Postgres CMS:** `5433` (évite conflit avec 5432 si utilisé ailleurs)

---

## À vérifier quand ça casse

### Conflits de Ports

Si les ports 3001, 1338, ou 5433 sont déjà utilisés:
- Vérifier: `lsof -i :3001`, `lsof -i :1338`, `lsof -i :5433`
- Ajuster dans `docker-compose.arquantix.yml`

### Conflits avec l'Existant

1. **Si docker-compose.yml existe déjà à la racine:**
   - Utiliser `docker-compose.arquantix.yml` séparé
   - Ou utiliser `docker compose -f docker-compose.arquantix.yml`

2. **Si package.json existe à la racine:**
   - Ne pas créer de monorepo tool
   - Garder les package.json indépendants dans chaque service

3. **Si les workflows GitHub Actions échouent:**
   - Vérifier les paths filters dans les workflows
   - S'assurer que `services/arquantix/**` est inclus

---

## TODO / État Actuel

### ✅ Fait

- [x] Analyse de la structure existante
- [x] Décision d'emplacement (`services/arquantix/web/` et `services/arquantix/cms/`)
- [x] Documentation initiale (ce fichier)

### ✅ Fait

- [x] Création de la structure de base
- [x] Configuration Docker Compose
- [x] Initialisation Strapi (structure de base, config)
- [x] Initialisation Next.js avec routes de base
- [x] Scripts de développement (Makefile)
- [x] Documentation complète
- [x] Workflow GitHub Actions pour déploiement

### 🚧 En Cours / À Faire

- [ ] Tests locaux (docker compose up)
- [ ] Créer les Content Types via Strapi Admin UI
- [ ] Seed script Strapi (étendre scripts/seed.js)
- [ ] Intégration complète Next.js ↔ Strapi (utiliser le client strapi.ts)
- [ ] Déploiement en production (ECR/ECS)

---

## Prochaines Étapes

1. Créer la structure de base (`services/arquantix/web/` et `services/arquantix/cms/`)
2. Configurer `docker-compose.arquantix.yml`
3. Initialiser Strapi avec les Content Types requis
4. Initialiser Next.js avec la structure de base
5. Créer les scripts de développement
6. Documenter l'architecture et les runbooks
7. Tester localement
8. Préparer le déploiement

---

**Dernière mise à jour:** 2026-01-01

