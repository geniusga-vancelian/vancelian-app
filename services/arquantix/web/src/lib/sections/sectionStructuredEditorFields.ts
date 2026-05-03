/**
 * Registre des **champs top-level** que `SectionEditor` (composant React `'use client'`)
 * expose à l'opérateur sous forme d'**inputs explicites** pour chaque section
 * dotée d'un éditeur structuré.
 *
 * Pourquoi ce registre ?
 * ----------------------
 *
 * Le scanner d'audit Famille 3 a montré qu'il est facile, par inadvertance,
 * d'ajouter un champ dans l'UI admin qui n'est lu nulle part au rendu (ou
 * inversement, de masquer un champ visuellement essentiel). Le test
 * `sectionStructuredEditorCoverage.test.ts` utilise ce registre pour vérifier :
 *
 *   « tout champ `direct` déclaré ici doit être lu par `mapDataToComponentProps` »
 *
 * Ce n'est pas un duplicata de la gouvernance i18n
 * (`SECTION_I18N_POLICIES` / `SECTION_EXPECTED_TRANSLATABLE_PATHS`) :
 *
 *   - i18n parle des champs **traduisibles** (donc nécessairement texte),
 *   - ce registre parle de **tout** input structuré exposé à l'opérateur
 *     (texte, booléens, médias, nombres…), traduisible ou non.
 *
 * Conventions
 * -----------
 *
 *  - On ne liste que les **clés racines** (`tags`, pas `tags[]` ; `items`,
 *    pas `items[].title`). Le test vérifie que la clé racine est présente
 *    dans la sortie de `mapDataToComponentProps` via une sentinelle ; la
 *    structure des sous-arborescences est validée par le composant final.
 *  - Deux familles de champs édités :
 *      - `direct`         : la valeur saisie est lue **telle quelle** par le
 *                           mapping (testée par sentinelle).
 *      - `serverResolved` : la valeur est **transformée côté serveur** avant
 *                           d'atteindre le mapping (`backgroundMediaId` →
 *                           `backgroundMediaUrl`, `selectedPackagedProductIds` →
 *                           `resolvedProjects`, `limit` → query DB). Listée
 *                           ici pour documentation, **exemptée** du test
 *                           sentinelle car la transformation se fait dans
 *                           `getPageSections` / API admin, pas dans le mapping.
 *  - Les sections **sans éditeur structuré** (about, features,
 *    help_*, …) passent par le JSON brut ; exceptions blog documentées
 *    (`blog_mosaic`, `blog_hero`, `blog_feed`, lecteur / hero article…).
 *
 * Si vous ajoutez un input dans `SectionEditor.tsx`, ajoutez la clé
 * correspondante ici. Si vous le retirez, retirez-la aussi : le test sera
 * une boussole pour les deux cas.
 */

export type SectionStructuredEditorFields = Readonly<
  Record<
    string,
    {
      /** Champs lus tels quels par `mapDataToComponentProps`. */
      readonly direct: readonly string[]
      /**
       * Champs transformés côté serveur (média ID → URL, IDs → entités
       * résolues, query params…) avant d'arriver au mapping. Documentés
       * pour l'opérateur, exemptés du test sentinelle.
       */
      readonly serverResolved?: readonly string[]
    }
  >
>

/**
 * Sources canoniques (cf. `structuredEditorCanonicalKeys` dans
 * `src/app/admin/sections/[id]/page.tsx`).
 *
 * Note : `hero` et `hero_secondary` partagent le même éditeur ; on déclare
 * deux entrées pour permettre une divergence future propre (ex. champs
 * spécifiques à une seule variante).
 */
export const SECTION_STRUCTURED_EDITOR_FIELDS: SectionStructuredEditorFields = {
  hero: {
    direct: [
      'title',
      'subtitle',
      'sidebarText',
      'backgroundImageOpacity',
      'hideCta',
      'ctaText',
      'ctaLink',
    ],
    serverResolved: ['backgroundMediaId'],
  },
  hero_secondary: {
    direct: [
      'title',
      'subtitle',
      'sidebarText',
      'backgroundImageOpacity',
      'tags',
      'hideCta',
      'ctaText',
      'ctaLink',
    ],
    serverResolved: ['backgroundMediaId'],
  },

  project_grid: {
    direct: [
      'eyebrow',
      'title',
      'description',
      'showAllExclusiveOffers',
      'viewAllButtonText',
    ],
    // `limit` est consommé côté API admin (taille de la page d'offres) et
    // `selectedPackagedProductIds` est résolu en `resolvedProjects` par
    // `getPageSections` : ces champs n'arrivent jamais bruts au mapping.
    serverResolved: ['limit', 'selectedPackagedProductIds'],
  },

  feature_grid: {
    direct: ['title', 'description', 'content', 'items'],
    serverResolved: ['imageMediaId'],
  },

  // Convention Surtitre / Titre / Description (cf. uniformisation modules CMS).
  // `subtitle` est désormais le champ legacy : il n'est plus exposé dans
  // l'éditeur, mais reste lu en compat douce par le mapping renderer
  // (`title || subtitle`) pour ne pas casser les contenus existants.
  faq: { direct: ['eyebrow', 'title', 'description', 'items', 'ui'] },

  how_it_works: {
    direct: [
      'label',
      'title',
      'subtitle',
      'hideStepNumbering',
      'primaryCtaText',
      'primaryCtaHref',
      'secondaryCtaText',
      'secondaryCtaHref',
      'steps',
    ],
  },

  cta: {
    direct: [
      'backgroundColor',
      'backgroundImageOpacity',
      'overlayOpacity',
      'eyebrow',
      'title',
      'description',
      'contentTextAlign',
      'showPrimaryButton',
      'showSecondaryButton',
      'primaryButtonText',
      'primaryButtonHref',
      'secondaryButtonText',
      'secondaryButtonHref',
    ],
    serverResolved: ['backgroundMediaId'],
  },

  figma_simple_hero: {
    direct: ['title', 'description', 'backgroundColor', 'textColor'],
  },

  figma_stats_grid: {
    direct: ['eyebrow', 'title', 'description', 'columns', 'stats'],
  },

  key_figures: {
    direct: [
      'backgroundColor',
      'backgroundImageOpacity',
      'overlayOpacity',
      'eyebrow',
      'title',
      'stats',
    ],
    serverResolved: ['backgroundMediaId'],
  },

  figma_testimonial_cards: {
    direct: ['eyebrow', 'title', 'description', 'cardsPerRow', 'items'],
  },

  media_text: {
    direct: ['eyebrow', 'title', 'description', 'mediaRight'],
    serverResolved: ['imageMediaId'],
  },

  testimonials: { direct: ['eyebrow', 'title', 'description', 'items'] },

  company_map: {
    direct: ['eyebrow', 'title', 'description', 'bodyContent'],
    serverResolved: ['backgroundMediaId'],
  },

  share_sm: {
    direct: ['title', 'items'],
  },

  blog_mosaic: {
    direct: [
      'title',
      'ctaLabel',
      'showTitle',
      'limit',
      'paginationPrevLabel',
      'paginationNextLabel',
    ],
  },

  blog_hero: {
    direct: ['eyebrow', 'showEyebrow', 'showStandfirst', 'showMeta'],
  },

  blog_feed: {
    direct: [
      'title',
      'showTitle',
      'pageSize',
      'loadMoreLabel',
      'emptyStateTitle',
      'emptyStateBody',
    ],
  },
} as const
