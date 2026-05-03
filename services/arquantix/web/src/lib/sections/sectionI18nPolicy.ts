/**
 * Gouvernance i18n des sections CMS (Lot 5)
 * -----------------------------------------
 * Une clé de section doit avoir ici une entrée explicite :
 * - `translatable` + chemins (alignés sur les champs texte du schéma Zod dans `library.ts`)
 * - `notTranslatable` + raison (pas de traduction auto, pas d’avertissement bruyant)
 *
 * Garde-fou : `sectionI18nPolicy.test.ts` vérifie que chaque entrée du `SECTION_REGISTRY`
 * résout vers une politique connue (via `resolveSectionI18nPolicy`).
 *
 * @see translateSectionData — consommateur runtime
 * @see SECTION_TYPES / schémas Zod — source de vérité structurelle
 */

/** Déclaration stockée (source unique pour l’éditeur / revue). */
export type SectionI18nPolicyDefinition =
  | { kind: 'translatable'; paths: readonly string[] }
  | { kind: 'notTranslatable'; reason: string }

export type ResolvedSectionI18n =
  | { kind: 'translatable'; paths: readonly string[] }
  | { kind: 'notTranslatable'; reason: string }
  | { kind: 'missingPolicy'; sectionKey: string }

/* -------------------------------------------------------------------------- */
/* Chemins réutilisés (même rendu / même schéma) — évite la dérive copier-coller */
/* -------------------------------------------------------------------------- */

/**
 * Paths du hero principal (`hero`) — les pastilles `tags[]` sont volontairement
 * masquées au rendu par `mapDataToComponentProps` (audit Famille 3) et donc
 * **exclues** de la traduction pour ne pas créer de faux signal.
 */
const HERO_PATHS = [
  'title',
  'subtitle',
  // `sidebarText` est rendu par `SectionHero` (fusionné au corps).
  'sidebarText',
  'ctaText',
] as const

/** Paths du `hero_secondary` — variante qui rend les pastilles `tags[]`. */
const HERO_SECONDARY_PATHS = [...HERO_PATHS, 'tags[]'] as const

const ABOUT_LIKE_PATHS = ['title', 'description'] as const

const PROJECT_GRID_PATHS = [
  'title',
  'description',
  'eyebrow',
  // CTA visible côté SectionProjects (`viewAllButtonText`, lu en runtime).
  'viewAllButtonText',
  // Items dynamiques rendus sur les cartes projets.
  'items[].title',
  'items[].description',
  'items[].location',
  'items[].tags[]',
] as const

const FEATURE_GRID_PATHS = [
  'title',
  'description',
  'content',
  'items[].title',
  'items[].description',
] as const

/**
 * Politiques par clé **canonique** ou alias stable utilisé en base (`features`, `about_showcase`, …).
 * Toute clé du registre doit être couverte directement ou via `resolveCanonicalSectionKey`.
 */
export const SECTION_I18N_POLICIES: Record<string, SectionI18nPolicyDefinition> = {
  // --- Layout / navigation
  header: {
    kind: 'notTranslatable',
    reason:
      'Libellés de navigation souvent alignés sur le menu primaire ; traduction ciblée plutôt que ce pipeline.',
  },

  common_module_ref: {
    kind: 'notTranslatable',
    reason:
      'Référence (`commonModuleId`) : les textes sont dans le module commun global (Zone 2), pas dans cette section.',
  },

  // --- Hero
  hero: { kind: 'translatable', paths: HERO_PATHS },
  hero_secondary: { kind: 'translatable', paths: HERO_SECONDARY_PATHS },

  // --- Grilles & about (aliases historiques)
  // `eyebrow` n'est PAS lu par `SectionAbout` (composant de rendu) — exclu pour
  // ne pas auto-traduire un champ invisible côté site (audit Famille 3 — F3.5).
  features: { kind: 'translatable', paths: ['title', 'description'] },
  feature_grid: { kind: 'translatable', paths: FEATURE_GRID_PATHS },
  about: { kind: 'translatable', paths: ABOUT_LIKE_PATHS },
  about_showcase: { kind: 'translatable', paths: ABOUT_LIKE_PATHS },
  about_transparency: { kind: 'translatable', paths: ABOUT_LIKE_PATHS },
  about_registration: { kind: 'translatable', paths: ABOUT_LIKE_PATHS },

  projects: { kind: 'translatable', paths: PROJECT_GRID_PATHS },
  project_grid: { kind: 'translatable', paths: PROJECT_GRID_PATHS },

  cta: {
    kind: 'translatable',
    paths: [
      'eyebrow',
      'title',
      'description',
      'primaryButtonText',
      'secondaryButtonText',
    ],
  },

  footer: {
    kind: 'translatable',
    paths: ['copyright'],
  },

  // --- Blog
  blog_list: {
    kind: 'translatable',
    paths: ['title', 'description'],
  },
  blog_hero: { kind: 'translatable', paths: ['eyebrow'] },
  blog_category_nav: { kind: 'translatable', paths: ['title', 'allLabel'] },
  blog_mosaic: {
    kind: 'translatable',
    paths: ['title', 'ctaLabel', 'paginationPrevLabel', 'paginationNextLabel'],
  },
  blog_feed: {
    kind: 'translatable',
    paths: ['title', 'loadMoreLabel', 'emptyStateTitle', 'emptyStateBody'],
  },
  blog_article_reader: {
    kind: 'translatable',
    paths: [
      'blogLabel',
      'tocTitle',
      'documentsTitle',
      'readingTimeLabel',
      'authorPrefixLabel',
    ],
  },
  blog_article_hero: {
    kind: 'translatable',
    paths: [
      'blogLabel',
      'breadcrumbCurrentText',
      'title',
      'standfirst',
      'categoryPillLabels[]',
      'editorialPillLabel',
      'authorName',
      'authorRole',
      'readingTimeText',
      'coverTitle',
      'coverCredit',
      'coverSource',
    ],
  },
  share_sm: {
    kind: 'translatable',
    paths: ['title', 'items[].label', 'items[].href'],
  },
  blog_article_related: {
    kind: 'translatable',
    paths: ['title', 'ctaLabel', 'emptyTitle'],
  },
  exclusive_offer_vault: {
    kind: 'notTranslatable',
    reason:
      'Aucun texte CMS : le contenu est celui du Vault Builder pour chaque offre (résolu au rendu public).',
  },

  faq: {
    kind: 'translatable',
    // Convention Surtitre / Titre / Description (cf. uniformisation modules CMS).
    // - `eyebrow`     : surtitre / pastille (CMS, traduisible).
    // - `title`       : titre canonique du module (nouveau champ d'écriture admin).
    // - `description` : chapô optionnel sous le titre (CMS, traduisible).
    // - `subtitle`    : ancien emplacement du titre — conservé en lecture par
    //                   `FaqSection` (compat douce). Reste traduisible pour
    //                   ne pas perdre les contenus existants tant que la
    //                   donnée n'a pas migré vers `title`.
    paths: [
      'eyebrow',
      'title',
      'description',
      'subtitle',
      'items[].question',
      'items[].answerMarkdown',
      'ui.expandAllLabel',
      'ui.collapseAllLabel',
    ],
  },

  how_it_works: {
    kind: 'translatable',
    paths: [
      'label',
      'title',
      'subtitle',
      'steps[].title',
      'steps[].description',
      'steps[].stepButtonLabel',
      'primaryCtaText',
      'secondaryCtaText',
    ],
  },

  testimonials: {
    kind: 'translatable',
    paths: [
      'eyebrow',
      'title',
      'description',
      'items[].name',
      'items[].text',
      'items[].title',
    ],
  },

  // --- Help
  help_hero_v1: {
    kind: 'translatable',
    paths: ['kicker', 'title', 'subtitle', 'placeholderSearch', 'helperText'],
  },
  help_search_v1: {
    kind: 'translatable',
    paths: ['placeholder', 'hint', 'clearLabel', 'noResultsTitle', 'noResultsSubtitle'],
  },
  help_collections_grid_v1: {
    kind: 'translatable',
    paths: [
      'sectionTitle',
      'sectionSubtitle',
      'cardCtaLabel',
      'articlesCountLabel',
      'emptyTitle',
      'emptySubtitle',
    ],
  },
  help_categories_grid_v1: {
    kind: 'translatable',
    paths: [
      'sectionTitle',
      'sectionSubtitle',
      'articlesCountLabel',
      'emptyTitle',
      'emptySubtitle',
    ],
  },
  help_collection_body_v1: {
    kind: 'translatable',
    paths: [
      'emptyCategoriesTitle',
      'emptyCategoriesSubtitle',
      'emptyArticlesTitle',
      'emptyArticlesSubtitle',
    ],
  },
  help_breadcrumbs_v1: { kind: 'translatable', paths: ['rootLabel', 'separator'] },
  help_search_results_v1: {
    kind: 'translatable',
    paths: ['resultsTitle', 'resultsCountLabel', 'emptyTitle', 'emptySubtitle'],
  },
  help_article_reader_v1: {
    kind: 'translatable',
    paths: ['updatedLabel', 'byLabel', 'readingTimeLabel', 'relatedTitle'],
  },
  help_sidebar_toc_v1: { kind: 'translatable', paths: ['tocTitle'] },

  // --- Figma / DS
  figma_simple_hero: { kind: 'translatable', paths: ['title', 'description'] },
  figma_stats_grid: {
    kind: 'translatable',
    paths: ['eyebrow', 'title', 'description', 'stats[].value', 'stats[].label'],
  },
  key_figures: {
    kind: 'translatable',
    paths: ['eyebrow', 'title', 'stats[].value', 'stats[].label'],
  },
  figma_testimonial_cards: {
    kind: 'translatable',
    paths: [
      'eyebrow',
      'title',
      'description',
      'items[].author',
      'items[].role',
      'items[].content',
    ],
  },

  media_text: {
    kind: 'translatable',
    // `imageMediaAlt` n'est PAS scanné ici : sa source de vérité est la
    // médiathèque (méta du média, traduit dans /admin/media). Le mapping
    // `SectionRenderer` se contente de le propager au composant.
    // `eyebrow` : surtitre / pastille au-dessus du titre (CMS, traduisible).
    paths: ['eyebrow', 'title', 'description'],
  },
  company_map: {
    kind: 'translatable',
    // `backgroundMediaAlt` : même rationnel que `media_text.imageMediaAlt`.
    paths: ['eyebrow', 'title', 'description', 'bodyContent'],
  },
}

/**
 * Résout la politique i18n pour une clé d’instance (`cta_2`, `hero`, …).
 * Ordre : clé brute → clé canonique (passée depuis `resolveCanonicalSectionKey` dans `library.ts`,
 * pour éviter un import circulaire library ↔ ce module).
 */
export function resolveSectionI18nPolicy(
  sectionKey: string,
  canonicalKey: string | null
): ResolvedSectionI18n {
  const direct = SECTION_I18N_POLICIES[sectionKey]
  if (direct) {
    return direct.kind === 'translatable'
      ? { kind: 'translatable', paths: direct.paths }
      : { kind: 'notTranslatable', reason: direct.reason }
  }

  if (canonicalKey) {
    const byCanon = SECTION_I18N_POLICIES[canonicalKey]
    if (byCanon) {
      return byCanon.kind === 'translatable'
        ? { kind: 'translatable', paths: byCanon.paths }
        : { kind: 'notTranslatable', reason: byCanon.reason }
    }
  }

  return { kind: 'missingPolicy', sectionKey }
}
