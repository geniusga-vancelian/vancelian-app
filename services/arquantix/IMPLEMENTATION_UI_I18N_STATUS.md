# Statut d'implémentation - UI I18N

## ✅ Phase 1: Audit - TERMINÉ
- Rapport d'audit créé: `AUDIT_UI_I18N.md`
- Éléments identifiés:
  - Menu principal (MenuItem.label) - Type B
  - Catégories blog (ArticleCategory.label) - Type B
  - Footer - Déjà localisé (Type C)
  - Navigation fallback - Hardcodé (Type A, optionnel)

## ✅ Phase 2: Data Model - TERMINÉ
- Modèles Prisma créés:
  - `MenuItemI18n` avec `label`, `locale`, `translationStatus`
  - `ArticleCategoryI18n` avec `label`, `locale`, `translationStatus`
- Migration appliquée (tables créées)
- Data migration: Labels existants copiés vers i18n pour locale `fr`
- Enum `TranslationEntityType` étendu: `MENU_ITEM`, `ARTICLE_CATEGORY`
- Prisma Client régénéré

## 🔄 Phase 3: API - EN COURS
À faire:
1. Mettre à jour `getPrimaryMenu()` pour résoudre labels par locale
2. Mettre à jour `/api/admin/menus/primary` pour inclure i18n
3. Mettre à jour `/api/admin/menus/primary/items` pour CRUD i18n
4. Mettre à jour `/api/admin/article-categories` pour inclure i18n
5. Mettre à jour `/api/blog` pour inclure labels i18n catégories
6. Créer `/api/admin/menus/primary/items/[id]/i18n` (GET/PUT)
7. Créer `/api/admin/article-categories/[id]/i18n` (GET/PUT)

## ⏳ Phase 4: Admin UI - EN ATTENTE
À faire:
1. Mettre à jour `/admin/pages/menu` pour éditer labels i18n
2. Créer `/admin/articles/categories` pour gérer catégories
3. Ajouter auto-translate pour menu items
4. Ajouter auto-translate pour article categories
5. Créer endpoints translate:
   - `/api/admin/translate/menu-item`
   - `/api/admin/translate/article-category`

## ⏳ Phase 5: Front - EN ATTENTE
À faire:
1. Mettre à jour `Navigation.tsx` pour utiliser labels i18n
2. Mettre à jour `/blog/page.tsx` pour utiliser labels i18n catégories
3. S'assurer que changement de langue déclenche re-fetch

## ⏳ Phase 6: Tests - EN ATTENTE
À faire:
1. Tests manuels: menu + catégories changent avec locale
2. Tests auto-translate
3. Tests fallback (locale manquante → fr → base label)

---

## Fichiers modifiés jusqu'à présent

### Schema & Migration
- `web/prisma/schema.prisma` - Ajout MenuItemI18n, ArticleCategoryI18n
- `web/prisma/migrations/20260106120000_add_menu_item_and_category_i18n/migration.sql`

### Documentation
- `AUDIT_UI_I18N.md` - Rapport d'audit complet
- `IMPLEMENTATION_UI_I18N_STATUS.md` - Ce fichier

---

## Prochaines étapes immédiates

1. **Helper function pour résoudre labels i18n**
   - Créer `web/src/lib/i18n/resolveLabel.ts`
   - Fonction: `resolveLabel(entity, locale, fallbackLocale = 'fr')`

2. **Mettre à jour getPrimaryMenu()**
   - Inclure `i18n` dans la requête Prisma
   - Résoudre `label` par locale demandée

3. **Mettre à jour APIs admin**
   - Inclure i18n dans les réponses
   - Créer endpoints CRUD i18n









