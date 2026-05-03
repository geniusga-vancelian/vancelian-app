# Dossier `cms/` — **non utilisé** (Strapi retiré)

Le service Docker **`arquantix-cms`** (Strapi) a été **supprimé** du dépôt (`docker-compose.arquantix-recovery.yml` et `docker-compose.arquantix.yml`). Le contenu applicatif passe par **Next.js + Prisma** ; le fichier `services/arquantix/web/src/lib/strapi.ts` est un **stub** sans appel réseau vers un CMS.

## Statut

| Option | Description |
|--------|-------------|
| **A. Suppression** | Supprimer tout le dossier `services/arquantix/cms/` quand vous n’avez plus besoin d’historique local. |
| **B. Archivage** | Déplacer le dossier vers un emplacement hors repo (ex. archive interne) si vous devez conserver des fichiers. |

Ne pas supprimer sans validation équipe : des scripts ou docs externes peuvent encore y faire référence.

## Voir aussi

- `services/arquantix/docs/STRAPI_DEPRECATED.md`
- `docs/arquantix/RUNBOOK.md` — stack locale (db, redis, api, web)
