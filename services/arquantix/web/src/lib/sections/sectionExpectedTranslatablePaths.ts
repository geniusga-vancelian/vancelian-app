/**
 * Ground truth de la couverture i18n attendue par section CMS.
 *
 * Ce fichier est une **copie miroir** des chemins minimaux qu'on attend
 * voir présents dans `SECTION_I18N_POLICIES`. Sa raison d'être :
 *
 *   - documenter ce qui doit *au minimum* être couvert pour chaque section
 *     (basé sur l'audit renderer ↔ policy),
 *   - faire échouer un test (`sectionI18nPolicyCoverage.test.ts`) si l'un
 *     de ces chemins disparaît silencieusement de la policy lors d'un futur
 *     refactor.
 *
 * Règles de mise à jour :
 *
 *   1. Quand un nouveau champ texte est rendu/éditable dans une section,
 *      ajouter l'entrée ici **et** dans `SECTION_I18N_POLICIES`. La double
 *      saisie est volontaire — c'est le mécanisme du garde-fou.
 *
 *   2. La policy peut contenir **plus** de chemins que ce ground truth (cas
 *      « champ encore présent dans le schéma mais désactivé côté rendu » :
 *      cf. arbitrage Famille 2 « keep »). On vérifie donc que ground truth
 *      ⊆ policy, pas l'inverse.
 *
 *   3. Pour les paires `SECTION_KEY` / `CANONICAL_KEY` (ex. `projects` ↔
 *      `project_grid`), on ne déclare le ground truth que pour la clé
 *      canonique. La policy de l'alias est implicitement validée via
 *      `resolveCanonicalSectionKey`.
 *
 *   4. Les sections marquées `notTranslatable` n'ont pas d'entrée ici.
 */

export const SECTION_EXPECTED_TRANSLATABLE_PATHS: Record<string, readonly string[]> = {
  // --- Hero
  hero: [
    'title',
    'subtitle',
    'sidebarText',
    // `tags[]` n'est rendu QUE par `hero_secondary` (cf. mapDataToComponentProps).
    // Le hero principal masque les pastilles : on ne les déclare donc pas ici
    // pour que le scan/auto-trad ne crée pas un faux signal sur des champs invisibles.
    'ctaText',
  ],
  hero_secondary: [
    'title',
    'subtitle',
    'sidebarText',
    'tags[]',
    'ctaText',
  ],

  // --- Grilles & about
  // `eyebrow` n'est PAS lu par `SectionAbout` (composant utilisé pour `features`/`feature_grid`).
  // → Ne pas le déclarer traduisible tant que le composant ne l'expose pas (audit Famille 3).
  features: ['title', 'description'],
  feature_grid: [
    'title',
    'description',
    'content',
    'items[].title',
    'items[].description',
  ],
  about: ['title', 'description'],
  about_showcase: ['title', 'description'],
  about_transparency: ['title', 'description'],
  about_registration: ['title', 'description'],

  // --- Projets
  project_grid: [
    'title',
    'description',
    'eyebrow',
    'viewAllButtonText',
    'items[].title',
    'items[].description',
    'items[].location',
    'items[].tags[]',
  ],

  // --- CTA
  cta: [
    'eyebrow',
    'title',
    'description',
    'primaryButtonText',
    'secondaryButtonText',
  ],

  // --- Footer (section-level — le footer global vit dans son admin propre)
  footer: ['copyright'],

  // --- Blog
  blog_list: ['title', 'description'],
  blog_hero: ['eyebrow'],
  blog_category_nav: ['title', 'allLabel'],
  blog_mosaic: ['title', 'ctaLabel', 'paginationPrevLabel', 'paginationNextLabel'],
  blog_feed: ['title', 'loadMoreLabel', 'emptyStateTitle', 'emptyStateBody'],

  blog_article_reader: [
    'blogLabel',
    'tocTitle',
    'documentsTitle',
    'readingTimeLabel',
    'authorPrefixLabel',
  ],
  blog_article_hero: [
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
  share_sm: ['title', 'items[].label', 'items[].href'],
  blog_article_related: ['title', 'ctaLabel', 'emptyTitle'],

  // --- FAQ
  // Convention Surtitre / Titre / Description (cf. uniformisation modules CMS).
  // - `eyebrow`     : surtitre / pastille (CMS, traduisible).
  // - `title`       : titre canonique (l'admin écrit ici depuis l'uniformisation).
  // - `description` : chapô optionnel sous le titre.
  // - `subtitle`    : ancien emplacement du titre — `FaqSection` retombe dessus
  //                   en compat douce si `title` est vide. Reste traduisible
  //                   tant que la donnée existante n'a pas migré.
  faq: [
    'eyebrow',
    'title',
    'description',
    'subtitle',
    'items[].question',
    'items[].answerMarkdown',
    'ui.expandAllLabel',
    'ui.collapseAllLabel',
  ],

  // --- How it works
  how_it_works: [
    'label',
    'title',
    'subtitle',
    'steps[].title',
    'steps[].description',
    'steps[].stepButtonLabel',
    'primaryCtaText',
    'secondaryCtaText',
  ],

  // --- Testimonials
  testimonials: [
    'eyebrow',
    'title',
    'description',
    'items[].name',
    'items[].text',
    'items[].title',
  ],

  // --- Help center
  help_hero_v1: ['kicker', 'title', 'subtitle', 'placeholderSearch', 'helperText'],
  help_search_v1: [
    'placeholder',
    'hint',
    'clearLabel',
    'noResultsTitle',
    'noResultsSubtitle',
  ],
  help_collections_grid_v1: [
    'sectionTitle',
    'sectionSubtitle',
    'cardCtaLabel',
    'articlesCountLabel',
    'emptyTitle',
    'emptySubtitle',
  ],
  help_categories_grid_v1: [
    'sectionTitle',
    'sectionSubtitle',
    'articlesCountLabel',
    'emptyTitle',
    'emptySubtitle',
  ],
  help_collection_body_v1: [
    'emptyCategoriesTitle',
    'emptyCategoriesSubtitle',
    'emptyArticlesTitle',
    'emptyArticlesSubtitle',
  ],
  help_breadcrumbs_v1: ['rootLabel', 'separator'],
  help_search_results_v1: ['resultsTitle', 'resultsCountLabel', 'emptyTitle', 'emptySubtitle'],
  help_article_reader_v1: ['updatedLabel', 'byLabel', 'readingTimeLabel', 'relatedTitle'],
  help_sidebar_toc_v1: ['tocTitle'],

  // --- Figma / DS
  figma_simple_hero: ['title', 'description'],
  figma_stats_grid: [
    'eyebrow',
    'title',
    'description',
    'stats[].value',
    'stats[].label',
  ],
  key_figures: ['eyebrow', 'title', 'stats[].value', 'stats[].label'],
  figma_testimonial_cards: [
    'eyebrow',
    'title',
    'description',
    'items[].author',
    'items[].role',
    'items[].content',
  ],

  // --- Media / map (alts gérés via la médiathèque, hors scan section)
  // `eyebrow` : surtitre/pastille (ex. « Notre approche »), CMS-driven, traduisible.
  media_text: ['eyebrow', 'title', 'description'],
  company_map: ['eyebrow', 'title', 'description', 'bodyContent'],
}
