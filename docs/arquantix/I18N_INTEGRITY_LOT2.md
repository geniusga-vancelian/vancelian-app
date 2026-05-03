# Intégrité linguistique — Lot 2 (prepare-fixes, preview)

## Rôle

À partir du même périmètre que le lot 1 (vault allowlisté + `hero` / `hero_secondary` / `cta`, **DRAFT** uniquement), le lot 2 produit un **plan de corrections structuré** avec **avant / après proposé**, **stratégie** et **rationale**. Aucune écriture en base.

## Ce que le lot 2 fait

- Relit les brouillons **toutes locales** nécessaires pour les sections concernées (requêtes Prisma **read-only**).
- Pour chaque finding d’audit **≠ OK**, génère une **proposition** avec stratégie explicite :
  - `copy-as-is` — reprise d’un texte jugé déjà conforme à la locale cible (classification).
  - `translate-from-source` — aperçu via le **MockTranslationProvider** (`[i18n-preview fr→en] …`) en attendant un vrai fournisseur.
  - `needs-review` — pas de correction automatique agressive (mélange, ambiguïté, cas non résolus).
  - `skip` — pas de source utilisable ou champ non éligible à l’auto.

## Ce que le lot 2 ne fait pas

- Aucun `update` / `create` sur `SectionContent`, `Page`, `PageI18n`, menu, footer.
- Aucun « apply » sur brouillon ou publié.
- Pas d’extension de périmètre au-delà du lot 1.

## Points d’entrée

- **API** : `GET /api/admin/i18n/integrity/prepare?targetLocale=…` (session admin).
- **UI** : `/admin/i18n/integrity` — bouton de génération des propositions et tableau de preview.

## Lot 3 (prévu)

Apply ciblé **sur brouillon uniquement**, avec validation explicite — hors scope du lot 2.
