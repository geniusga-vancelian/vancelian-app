/**
 * Section Library - Definitions of available section types
 * Each section type defines its metadata, default data, and validation schema
 */

import { z } from 'zod'

export enum SectionCategory {
  LAYOUT = 'LAYOUT',
  CONTENT = 'CONTENT',
  BLOG = 'BLOG',
  PROJECTS = 'PROJECTS',
  HELP = 'HELP',
}

export interface SectionType {
  key: string
  label: string
  category: SectionCategory
  schemaVersion: string
  defaultData: any
  zodSchema: z.ZodType<any>
  allowedOnTemplates: string[]
  description?: string
}

// Zod schemas for each section type
const heroSchema = z.object({
  title: z.string().optional(),
  subtitle: z.string().optional(),
  ctaText: z.string().optional(),
  ctaLink: z.string().optional(),
  backgroundMediaUrl: z.string().optional(),
  backgroundImage: z.string().optional(),
  features: z.array(z.object({ label: z.string() })).optional(),
  sidebarText: z.string().optional(),
})

const headerSchema = z.object({
  logoUrl: z.string().optional(),
  links: z.array(z.object({
    label: z.string(),
    href: z.string(),
  })).optional(),
})

const featureGridSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  items: z.array(z.object({
    title: z.string(),
    description: z.string(),
  })).optional(),
})

const ctaSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  primaryButtonText: z.string().optional(),
  primaryButtonHref: z.string().optional(),
  secondaryButtonText: z.string().optional(),
  secondaryButtonHref: z.string().optional(),
})

const footerSchema = z.object({
  copyright: z.string().optional(),
  description: z.string().optional(),
  links: z.array(z.object({
    label: z.string(),
    href: z.string(),
    category: z.string().optional(),
  })).optional(),
})

const projectGridSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  limit: z.number().int().min(1).max(20).optional().default(3),
  selectedProjectIds: z.array(z.string()).optional(),
  layout: z.enum(['grid', 'carousel']).optional().default('grid'),
  // Legacy: items array for backward compatibility
  items: z.array(z.object({
    title: z.string(),
    location: z.string().optional(),
    tags: z.array(z.string()).optional(),
    description: z.string().optional(),
    mediaId: z.string().optional(),
    mediaUrl: z.string().optional(),
  })).optional(),
})

const blogListSchema = z.object({
  title: z.string().optional(),
  description: z.string().optional(),
  items: z.array(z.object({
    title: z.string(),
    excerpt: z.string().optional(),
    publishedAt: z.string().optional(),
    slug: z.string().optional(),
    mediaId: z.string().optional(),
  })).optional(),
})

// Blog section schemas
const blogHeroSchema = z.object({
  eyebrow: z.string().optional(),
  showEyebrow: z.boolean().optional().default(true),
  showStandfirst: z.boolean().optional().default(true),
  showMeta: z.boolean().optional().default(true),
})

const blogCategoryNavSchema = z.object({
  title: z.string().optional(),
  showTitle: z.boolean().optional().default(false),
  allLabel: z.string().optional().default('All'),
})

const blogMosaicSchema = z.object({
  title: z.string().optional(),
  showTitle: z.boolean().optional().default(true),
  limit: z.number().int().min(1).max(10).optional().default(4),
})

const blogFeedSchema = z.object({
  title: z.string().optional(),
  showTitle: z.boolean().optional().default(true),
  pageSize: z.number().int().min(1).max(50).optional().default(10),
  loadMoreLabel: z.string().optional().default('Load more'),
  emptyStateTitle: z.string().optional(),
  emptyStateBody: z.string().optional(),
})

const faqSchema = z.object({
  title: z.string().optional().default('FAQ'),
  subtitle: z.string().optional().default('Frequently Asked Questions'),
  items: z.array(
    z.object({
      id: z.string(),
      question: z.string(),
      answerMarkdown: z.string(),
    })
  ).optional().default([]),
  ui: z.object({
    expandAllLabel: z.string().optional(),
    collapseAllLabel: z.string().optional(),
  }).optional(),
})

// Help Center section schemas
const helpHeroV1Schema = z.object({
  kicker: z.string().optional(),
  title: z.string().optional(),
  subtitle: z.string().optional(),
  placeholderSearch: z.string().optional(),
  helperText: z.string().optional(),
  backgroundStyle: z.enum(['purple', 'dark', 'light']).optional().default('purple'),
})

const helpSearchV1Schema = z.object({
  placeholder: z.string().optional(),
  hint: z.string().optional(),
  clearLabel: z.string().optional(),
  noResultsTitle: z.string().optional(),
  noResultsSubtitle: z.string().optional(),
})

const helpCollectionsGridV1Schema = z.object({
  sectionTitle: z.string().optional(),
  sectionSubtitle: z.string().optional(),
  cardCtaLabel: z.string().optional(),
  articlesCountLabel: z.string().optional(),
  emptyTitle: z.string().optional(),
  emptySubtitle: z.string().optional(),
})

const helpCategoriesGridV1Schema = z.object({
  sectionTitle: z.string().optional(),
  sectionSubtitle: z.string().optional(),
  articlesCountLabel: z.string().optional(),
  emptyTitle: z.string().optional(),
  emptySubtitle: z.string().optional(),
})

const helpCollectionBodyV1Schema = z.object({
  emptyCategoriesTitle: z.string().optional(),
  emptyCategoriesSubtitle: z.string().optional(),
  emptyArticlesTitle: z.string().optional(),
  emptyArticlesSubtitle: z.string().optional(),
})

const helpBreadcrumbsV1Schema = z.object({
  rootLabel: z.string().optional(),
  separator: z.string().optional(),
})

const helpSearchResultsV1Schema = z.object({
  resultsTitle: z.string().optional(),
  resultsCountLabel: z.string().optional(),
  emptyTitle: z.string().optional(),
  emptySubtitle: z.string().optional(),
})

const helpArticleReaderV1Schema = z.object({
  updatedLabel: z.string().optional(),
  byLabel: z.string().optional(),
  readingTimeLabel: z.string().optional(),
  relatedTitle: z.string().optional(),
})

const helpSidebarTocV1Schema = z.object({
  tocTitle: z.string().optional(),
})

// Section type definitions
export const SECTION_TYPES: SectionType[] = [
  {
    key: 'header',
    label: 'Header / Navigation',
    category: SectionCategory.LAYOUT,
    schemaVersion: 'v1',
    defaultData: {
      logoUrl: '/images/logo.svg',
      links: [
        { label: 'Home', href: '/' },
        { label: 'About', href: '/about' },
        { label: 'Projects', href: '/projects' },
      ],
    },
    zodSchema: headerSchema,
    allowedOnTemplates: ['homepage', 'default', 'blog', 'project'],
    description: 'Navigation header with logo and links',
  },
  {
    key: 'hero',
    label: 'Hero Section',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Welcome',
      subtitle: 'Your subtitle here',
      ctaText: 'Get Started',
      ctaLink: '/contact',
      features: [
        { label: 'Feature 1' },
        { label: 'Feature 2' },
        { label: 'Feature 3' },
      ],
    },
    zodSchema: heroSchema,
    allowedOnTemplates: ['homepage', 'default'],
    description: 'Hero banner with title, subtitle, CTA, and optional background image',
  },
  {
    key: 'feature_grid',
    label: 'Feature Grid',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Features',
      description: 'Our key features',
      items: [
        { title: 'Feature 1', description: 'Description 1' },
        { title: 'Feature 2', description: 'Description 2' },
        { title: 'Feature 3', description: 'Description 3' },
      ],
    },
    zodSchema: featureGridSchema,
    allowedOnTemplates: ['homepage', 'default'],
    description: 'Grid of feature items with title and description',
  },
  {
    key: 'cta',
    label: 'Call to Action',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Ready to get started?',
      description: 'Join us today',
      primaryButtonText: 'Get Started',
      primaryButtonHref: '/signup',
      secondaryButtonText: 'Learn More',
      secondaryButtonHref: '/about',
    },
    zodSchema: ctaSchema,
    allowedOnTemplates: ['homepage', 'default', 'blog', 'project'],
    description: 'Call-to-action section with buttons',
  },
  {
    key: 'footer',
    label: 'Footer',
    category: SectionCategory.LAYOUT,
    schemaVersion: 'v1',
    defaultData: {
      copyright: `© ${new Date().getFullYear()} Your Company. All rights reserved.`,
      description: 'Company description',
      links: [
        { label: 'About', href: '/about', category: 'company' },
        { label: 'Privacy', href: '/privacy', category: 'legal' },
        { label: 'Contact', href: '/contact', category: 'contact' },
      ],
    },
    zodSchema: footerSchema,
    allowedOnTemplates: ['homepage', 'default', 'blog', 'project'],
    description: 'Footer with copyright, description, and links',
  },
  {
    key: 'project_grid',
    label: 'Project Grid',
    category: SectionCategory.PROJECTS,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Our Projects',
      description: 'Discover our portfolio',
      items: [],
    },
    zodSchema: projectGridSchema,
    allowedOnTemplates: ['homepage', 'default', 'project'],
    description: 'Grid of project items (will connect to Projects DB in Phase B)',
  },
  {
    key: 'blog_list',
    label: 'Blog List',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Latest Articles',
      description: 'Read our latest blog posts',
      items: [],
    },
    zodSchema: blogListSchema,
    allowedOnTemplates: ['homepage', 'default', 'blog'],
    description: 'List of blog articles (will connect to Articles DB in Phase C)',
  },
  {
    key: 'blog_hero',
    label: 'Blog Hero (Featured Article)',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      eyebrow: 'À la une',
      showEyebrow: true,
      showStandfirst: true,
      showMeta: true,
    },
    zodSchema: blogHeroSchema,
    allowedOnTemplates: ['blog'],
    description: 'Hero section displaying the featured article',
  },
  {
    key: 'blog_category_nav',
    label: 'Blog Category Navigation',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Explorer',
      showTitle: false,
      allLabel: 'Tous',
    },
    zodSchema: blogCategoryNavSchema,
    allowedOnTemplates: ['blog'],
    description: 'Category navigation pills with optional title',
  },
  {
    key: 'blog_mosaic',
    label: 'Blog Mosaic (Highlighted Articles)',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'À ne pas manquer',
      showTitle: true,
      limit: 4,
    },
    zodSchema: blogMosaicSchema,
    allowedOnTemplates: ['blog'],
    description: 'Mosaic grid of highlighted articles',
  },
  {
    key: 'blog_feed',
    label: 'Blog Feed (Latest Articles)',
    category: SectionCategory.BLOG,
    schemaVersion: 'v1',
    defaultData: {
      title: 'Derniers articles',
      showTitle: true,
      pageSize: 10,
      loadMoreLabel: 'Voir plus',
      emptyStateTitle: 'Aucun article',
      emptyStateBody: 'Il n\'y a pas encore d\'articles publiés.',
    },
    zodSchema: blogFeedSchema,
    allowedOnTemplates: ['blog'],
    description: 'Paginated feed of latest articles with load more',
  },
  {
    key: 'faq',
    label: 'FAQ Section',
    category: SectionCategory.CONTENT,
    schemaVersion: 'v1',
    defaultData: {
      title: 'FAQ',
      subtitle: 'Frequently Asked Questions',
      items: [],
    },
    zodSchema: faqSchema,
    allowedOnTemplates: ['homepage', 'default', 'blog', 'project'],
    description: 'FAQ accordion section with questions and answers',
  },
  // Help Center sections
  {
    key: 'help_hero_v1',
    label: 'Help Hero',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      kicker: 'HELP CENTER',
      title: 'Conseils et réponses de l\'équipe Arquantix',
      subtitle: 'Trouvez rapidement les réponses à vos questions',
      placeholderSearch: 'Rechercher un article…',
      helperText: 'Recherchez par mot-clé, question, sujet…',
      backgroundStyle: 'purple',
    },
    zodSchema: helpHeroV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Hero section for Help Center with purple background',
  },
  {
    key: 'help_search_v1',
    label: 'Help Search',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      placeholder: 'Rechercher un article…',
      hint: 'Recherchez par mot-clé, question, sujet…',
      clearLabel: 'Effacer',
      noResultsTitle: 'Aucun résultat',
      noResultsSubtitle: 'Essayez un autre mot-clé.',
    },
    zodSchema: helpSearchV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Search bar for Help Center articles',
  },
  {
    key: 'help_collections_grid_v1',
    label: 'Help Collections Grid',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      sectionTitle: 'Collections',
      sectionSubtitle: 'Parcourir par thème',
      cardCtaLabel: 'Voir',
      articlesCountLabel: 'articles',
      emptyTitle: 'Aucune collection',
      emptySubtitle: 'Créez votre première collection dans l\'admin.',
    },
    zodSchema: helpCollectionsGridV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Grid of Help Center collections',
  },
  {
    key: 'help_categories_grid_v1',
    label: 'Help Categories Grid',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      sectionTitle: 'Catégories',
      sectionSubtitle: '',
      articlesCountLabel: 'articles',
      emptyTitle: 'Aucune catégorie',
      emptySubtitle: '',
    },
    zodSchema: helpCategoriesGridV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Grid of Help Center categories',
  },
  {
    key: 'help_collection_body_v1',
    label: 'Help Collection Body',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      emptyCategoriesTitle: 'Aucune catégorie',
      emptyCategoriesSubtitle: 'Aucune catégorie disponible dans cette collection.',
      emptyArticlesTitle: 'Aucun article',
      emptyArticlesSubtitle: 'Aucun article disponible dans cette catégorie.',
    },
    zodSchema: helpCollectionBodyV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Collection page body with categories and article lists (Shares-style)',
  },
  {
    key: 'help_breadcrumbs_v1',
    label: 'Help Breadcrumbs',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      rootLabel: 'Toutes les collections',
      separator: '›',
    },
    zodSchema: helpBreadcrumbsV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Breadcrumb navigation for Help Center',
  },
  {
    key: 'help_search_results_v1',
    label: 'Help Search Results',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      resultsTitle: 'Résultats',
      resultsCountLabel: 'résultats',
      emptyTitle: 'Aucun article trouvé',
      emptySubtitle: 'Essayez une autre recherche.',
    },
    zodSchema: helpSearchResultsV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Search results list for Help Center',
  },
  {
    key: 'help_article_reader_v1',
    label: 'Help Article Reader',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      updatedLabel: 'Mis à jour',
      byLabel: 'Par',
      readingTimeLabel: 'min de lecture',
      relatedTitle: 'Articles associés',
    },
    zodSchema: helpArticleReaderV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Article reader view for Help Center',
  },
  {
    key: 'help_sidebar_toc_v1',
    label: 'Help Sidebar TOC',
    category: SectionCategory.HELP,
    schemaVersion: 'v1',
    defaultData: {
      tocTitle: 'Sur cette page',
    },
    zodSchema: helpSidebarTocV1Schema,
    allowedOnTemplates: ['default'],
    description: 'Table of contents sidebar for Help Center articles',
  },
]

/**
 * Get section type by key
 */
export function getSectionType(key: string): SectionType | undefined {
  return SECTION_TYPES.find((type) => type.key === key)
}

/**
 * Get section types by category
 */
export function getSectionTypesByCategory(category: SectionCategory): SectionType[] {
  return SECTION_TYPES.filter((type) => type.category === category)
}

/**
 * Get section types allowed on template
 */
export function getSectionTypesForTemplate(template: string): SectionType[] {
  return SECTION_TYPES.filter(
    (type) => type.allowedOnTemplates.includes(template) || type.allowedOnTemplates.includes('default')
  )
}

/**
 * Validate section data against its schema
 */
export function validateSectionData(key: string, data: any): { valid: boolean; error?: string } {
  const sectionType = getSectionType(key)
  if (!sectionType) {
    return { valid: false, error: `Unknown section type: ${key}` }
  }

  try {
    sectionType.zodSchema.parse(data)
    return { valid: true }
  } catch (error) {
    if (error instanceof z.ZodError) {
      return { valid: false, error: error.issues.map((e) => `${e.path.join('.')}: ${e.message}`).join(', ') }
    }
    return { valid: false, error: 'Validation failed' }
  }
}

