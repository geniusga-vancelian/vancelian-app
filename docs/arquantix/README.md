# Documentation Arquantix

Documentation pour le projet Arquantix (Next.js + API + PostgreSQL).

## 🚀 Onboarding (1 commande)

- **[LOCAL_SETUP.md](./LOCAL_SETUP.md)** — **entrée unique** : fichiers d’env, quick start, modes Docker / Next hôte, limites (Prisma ≠ Alembic, etc.)
- **[QUICK_START.md](./QUICK_START.md)** — `make setup`, prérequis, URLs, commandes courantes

## 📚 Structure

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Architecture système, diagrammes, flux
- **[DECISIONS.md](./DECISIONS.md)** - Architectural Decision Records (ADRs)
- **[RUNBOOK.md](./RUNBOOK.md)** - Procédures opérationnelles (start/stop/reset/seed/logs)
- **[CHECKLIST.md](./CHECKLIST.md)** - Checklists (dev-ready, prod-ready)
- **[STATE.md](./STATE.md)** - État actuel, ce qui marche, TODO
- **[API.md](./API.md)** - Référence historique (Strapi retiré — voir FastAPI en prod)
- **[CONTENT_MODEL.md](./CONTENT_MODEL.md)** - Modèle de contenu, champs, exemples JSON
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Guide de déploiement (ECS, ECR, etc.)
- **[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)** - Dépannage courant
- **[LOCAL_DB_ALIGNMENT.md](./LOCAL_DB_ALIGNMENT.md)** - Alignement DB locale (API / Alembic / Prisma), `make local-db-doctor`
- **[../../services/arquantix/mobile/docs/LOCAL_IOS_AND_BFF.md](../../services/arquantix/mobile/docs/LOCAL_IOS_AND_BFF.md)** - Flutter iOS : simulateur vs iPhone, ports 3000 / 8000

## Démarrage rapide (détail)

1. [QUICK_START.md](./QUICK_START.md) — une commande : `make setup`
2. Lire [STATE.md](./STATE.md) pour comprendre l'état actuel
3. Suivre [RUNBOOK.md](./RUNBOOK.md) pour les procédures complètes
3. Consulter [ARCHITECTURE.md](./ARCHITECTURE.md) pour comprendre l'architecture
4. Référencer [DEPLOYMENT.md](./DEPLOYMENT.md) pour déployer

---

**Dernière mise à jour:** 2026-01-01

