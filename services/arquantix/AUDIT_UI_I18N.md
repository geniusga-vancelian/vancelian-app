# Audit UI I18N - Éléments d'interface non localisés

**Date**: 2026-01-06  
**Objectif**: Identifier tous les éléments d'interface utilisateur (UI) qui ne sont pas localisés et nécessitent une traduction multi-locale.

---

## 1. MENU PRINCIPAL (Primary Menu)

### État actuel
- **Modèle DB**: `MenuItem` (Prisma)
- **Champ**: `label String` (non localisé)
- **Localisation**: ❌ Non localisé
- **Fichiers concernés**:
  - `web/prisma/schema.prisma:280` - `MenuItem.label String`
  - `web/src/lib/menu/getPrimaryMenu.ts` - Récupération du menu
  - `web/src/app/api/admin/menus/primary/route.ts` - API admin
  - `web/src/app/api/admin/menus/primary/items/route.ts` - CRUD items
  - `web/src/components/sections/Navigation.tsx` - Affichage navbar

### Classification
**Type B**: Stored in DB but not localized (needs `MenuItemI18n` table)

### Recommandation
Créer `MenuItemI18n` avec:
- `id`, `menuItemId`, `locale`, `label`, `translationStatus`
- `@@unique([menuItemId, locale])`
- Migration: copier `MenuItem.label` existant vers `MenuItemI18n` pour locale `fr`

---

## 2. CATÉGORIES DE BLOG (Article Categories)

### État actuel
- **Modèle DB**: `ArticleCategory` (Prisma)
- **Champ**: `label String` (non localisé)
- **Localisation**: ❌ Non localisé
- **Fichiers concernés**:
  - `web/prisma/schema.prisma:175` - `ArticleCategory.label String`
  - `web/src/app/api/admin/article-categories/route.ts` - API admin
  - `web/src/app/api/blog/route.ts:31` - API public blog
  - `web/src/app/blog/page.tsx` - Affichage catégories (multiple usages)
  - `web/src/app/admin/articles/[id]/page.tsx` - Admin article editor

### Classification
**Type B**: Stored in DB but not localized (needs `ArticleCategoryI18n` table)

### Recommandation
Créer `ArticleCategoryI18n` avec:
- `id`, `categoryId`, `locale`, `label`, `translationStatus`
- `@@unique([categoryId, locale])`
- Migration: copier `ArticleCategory.label` existant vers `ArticleCategoryI18n` pour locale `fr`
- **Note**: Le `slug` reste stable (non traduit)

---

## 3. FOOTER (Section Footer)

### État actuel
- **Modèle**: Section CMS (`SectionContent.data`)
- **Champs**: `copyright`, `links[]` (avec `label`, `href`, `category`)
- **Localisation**: ✅ Déjà localisé via `SectionContent.locale`
- **Fichiers concernés**:
  - `web/src/components/sections/Footer.tsx` - Composant footer
  - `web/src/lib/sections/library.ts:178` - Définition section footer
  - `web/src/app/api/admin/pages/route.ts:104` - Seed avec copyright hardcodé

### Classification
**Type C**: Stored in DB already localized but UI may not be using locale correctly

### Recommandation
✅ **Déjà localisé** - Vérifier que le footer utilise bien `SectionContent` avec la bonne locale. Le copyright hardcodé dans le seed doit être remplacé par du contenu CMS.

---

## 4. NAVIGATION FALLBACK

### État actuel
- **Localisation**: Hardcodé dans le code
- **Fichiers concernés**:
  - `web/src/components/sections/Navigation.tsx:20-24` - Fallback menu items hardcodés

```typescript
const fallbackMenuItems: MenuItem[] = [
  { id: 'home', label: 'Home', urlPath: '/' },
]
```

### Classification
**Type A**: Hardcoded in code (needs DB or dictionary i18n)

### Recommandation
✅ **Déjà géré** - Le fallback n'est utilisé que si le menu DB est vide. Une fois le menu DB créé, ce fallback ne sera plus utilisé. Pas d'action nécessaire si le menu DB est toujours présent.

---

## 5. SECTION LIBRARY CATEGORIES (Admin)

### État actuel
- **Localisation**: Hardcodé dans le code
- **Fichiers concernés**:
  - `web/src/components/admin/SectionLibraryModal.tsx:86-91` - Catégories hardcodées

```typescript
const categories = [
  { value: 'ALL' as const, label: 'All Categories' },
  { value: SectionCategory.LAYOUT, label: 'Layout' },
  { value: SectionCategory.CONTENT, label: 'Content' },
  { value: SectionCategory.PROJECTS, label: 'Projects' },
  { value: SectionCategory.BLOG, label: 'Blog' },
]
```

### Classification
**Type A**: Hardcoded in code (admin-only UI)

### Recommandation
⚠️ **Optionnel** - Interface admin uniquement. Peut rester en anglais ou être traduit via un dictionnaire simple. Priorité basse.

---

## 6. AUTRES ÉLÉMENTS POTENTIELS

### Labels de formulaire admin
- Tous les labels de formulaires admin (`label`, `placeholder`, etc.)
- **Classification**: Type A (admin-only)
- **Recommandation**: Optionnel, priorité basse

### Messages d'erreur/succès
- Toasts, messages de validation
- **Classification**: Type A
- **Recommandation**: Optionnel, peut utiliser un dictionnaire i18n simple

---

## RÉSUMÉ DES ACTIONS REQUISES

### Priorité HAUTE (Phase 2)
1. ✅ **MenuItemI18n** - Créer modèle + migration
2. ✅ **ArticleCategoryI18n** - Créer modèle + migration

### Priorité MOYENNE (Phase 3-4)
3. ✅ Mettre à jour APIs pour retourner labels localisés
4. ✅ Créer interfaces admin pour éditer i18n
5. ✅ Ajouter auto-translate pour menu + categories

### Priorité BASSE (Optionnel)
6. ⚠️ Footer copyright hardcodé dans seed (remplacer par CMS)
7. ⚠️ Section Library categories (admin-only, optionnel)
8. ⚠️ Labels formulaires admin (optionnel)

---

## FICHIERS À MODIFIER

### Phase 2 (Data Model)
- `web/prisma/schema.prisma` - Ajouter `MenuItemI18n` et `ArticleCategoryI18n`
- Migration Prisma

### Phase 3 (API)
- `web/src/app/api/admin/menus/primary/route.ts` - Inclure i18n
- `web/src/app/api/admin/menus/primary/items/route.ts` - CRUD i18n
- `web/src/app/api/admin/article-categories/route.ts` - Inclure i18n
- `web/src/app/api/blog/route.ts` - Inclure i18n labels
- `web/src/lib/menu/getPrimaryMenu.ts` - Résoudre labels par locale

### Phase 4 (Admin UI)
- `web/src/app/admin/pages/menu/page.tsx` - Éditeur i18n
- Nouveau: `web/src/app/admin/articles/categories/page.tsx` - Gestion catégories
- `web/src/app/api/admin/translate/menu-item/route.ts` - Auto-translate
- `web/src/app/api/admin/translate/article-category/route.ts` - Auto-translate

### Phase 5 (Front)
- `web/src/components/sections/Navigation.tsx` - Utiliser labels i18n
- `web/src/app/blog/page.tsx` - Utiliser labels i18n catégories

---

## NOTES TECHNIQUES

- **Fallback chain**: locale demandée → default locale (fr) → base label
- **TranslationStatus**: Réutiliser enum existant (ORIGINAL/MACHINE/APPROVED)
- **TranslationLog**: Étendre `TranslationEntityType` avec `MENU_ITEM` et `ARTICLE_CATEGORY`
- **Slug stability**: Les slugs (`ArticleCategory.slug`, `MenuItem` target) restent stables et non traduits









