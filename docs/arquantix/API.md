# API — documentation historique (Strapi)

**Statut : déprécié (2026)** — Le CMS **Strapi** n’est **plus** utilisé en runtime. Les routes métier exposées au produit passent par l’**API FastAPI** (`services/arquantix/api`), pas par Strapi.

## À utiliser à la place

| Sujet | Emplacement |
|-------|-------------|
| API HTTP (app, admin, mobile, PDF, etc.) | `services/arquantix/api` — OpenAPI : `http://127.0.0.1:${API_PORT:-8000}/docs` |
| Contenu / pages côté web | Prisma + tables PostgreSQL partagées avec l’API — voir `services/arquantix/web` |
| Ancien client Strapi côté Next | `services/arquantix/web/src/lib/strapi.ts` — **stub** (pas d’appel CMS) |

## Ancienne documentation Strapi

L’historique détaillé des endpoints Strapi a été retiré pour éviter la confusion. Pour toute référence archivistique, voir l’historique Git avant cette page.

**Dernière mise à jour :** 2026-04-13
