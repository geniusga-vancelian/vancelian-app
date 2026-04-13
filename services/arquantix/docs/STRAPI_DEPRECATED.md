# ⚠️ Strapi n'est plus utilisé

**Date de retrait:** 2026-01-08

Strapi/CMS a été retiré du projet Arquantix. Toutes les fonctionnalités CMS sont maintenant gérées directement par Next.js via Prisma.

## 📁 Fichiers Strapi conservés (pour référence)

Les fichiers suivants dans `cms/` sont conservés pour référence historique mais ne sont **plus utilisés**:

- `cms/QUICK_START.md`
- `cms/DEVELOPMENT.md`
- `cms/SETUP.md`
- `cms/SETUP_NODE.md`
- `cms/start-strapi.sh`

## 🔄 Migration

- **Avant:** Strapi (port 1337) → Base `arquantix_cms`
- **Maintenant:** Next.js (port 3000) → Base `arquantix_admin` (Prisma)

## 📚 Documentation actuelle

Voir:
- [README.md](../README.md) - Source de vérité
- [START_ARQUANTIX.md](../START_ARQUANTIX.md) - Guide de démarrage





