/**
 * Component to render sections based on their key and data
 * Uses the section registry to map section keys to React components
 */

import { getSectionComponent, hasSectionComponent } from '@/lib/sections/registry'

interface SectionData {
  id: string
  key: string
  order: number
  schemaVersion: string
  data: any
  locale: string
  status: string
}

interface SectionRendererProps {
  section: SectionData
  locale?: string
  category?: string
  page?: number
  // Help Center context props
  collectionSlug?: string
  categorySlug?: string
  articleSlug?: string
  searchQuery?: string
}

export function SectionRenderer({ 
  section, 
  locale, 
  category, 
  page,
  collectionSlug,
  categorySlug,
  articleSlug,
  searchQuery,
}: SectionRendererProps) {
  const { key, data } = section

  // Get component from registry
  const Component = getSectionComponent(key)

  if (!Component) {
    // Fallback: render as JSON for unknown sections
    return (
      <div className="bg-yellow-50 border border-yellow-200 p-4 my-4">
        <p className="text-sm text-yellow-800">
          <strong>Unknown section:</strong> {key}
        </p>
        <pre className="mt-2 text-xs overflow-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      </div>
    )
  }

  // Render component with data as props
  // Map data fields to component props based on section key
  const props = mapDataToComponentProps(
    key, 
    data, 
    locale, 
    category, 
    page,
    collectionSlug,
    categorySlug,
    articleSlug,
    searchQuery,
  )
  
  return <Component {...props} />
}

/**
 * Map section data to component props based on section key
 */
function mapDataToComponentProps(
  key: string, 
  data: any, 
  locale?: string, 
  category?: string, 
  page?: number,
  collectionSlug?: string,
  categorySlug?: string,
  articleSlug?: string,
  searchQuery?: string,
): any {
  switch (key) {
    case 'hero':
      // Debug: log hero data mapping
      if (process.env.NODE_ENV === 'development') {
        console.log('[SectionRenderer] Hero data mapping:', {
          backgroundMediaUrl: data.backgroundMediaUrl,
          backgroundImage: data.backgroundImage,
          backgroundMediaId: data.backgroundMediaId,
          finalBackgroundImage: data.backgroundMediaUrl || data.backgroundImage,
        })
      }
      return {
        backgroundImage: data.backgroundMediaUrl || data.backgroundImage,
        title: data.title,
        subtitle: data.subtitle,
        ctaText: data.ctaText,
        ctaLink: data.ctaLink,
        features: data.features,
        sidebarText: data.sidebarText,
      }

    case 'about':
    case 'features':
    case 'feature_grid':
      return {
        title: data.title,
        description: data.description,
        items: data.items,
        imageUrl: data.imageMediaUrl || data.imageUrl,
        content: data.content,
        ctaText: data.ctaText,
        ctaLink: data.ctaLink,
      }

    case 'projects':
    case 'project_grid':
      // Priority: resolvedProjects (from DB) > items (legacy hardcoded)
      if (data.resolvedProjects && data.resolvedProjects.length > 0) {
        return {
          title: data.title,
          description: data.description,
          resolvedProjects: data.resolvedProjects,
        }
      }
      return {
        title: data.title,
        description: data.description,
        items: data.items?.map((item: any) => ({
          ...item,
          backgroundImage: item.mediaUrl || item.backgroundImage,
        })),
      }

    case 'cta':
      return {
        title: data.title,
        description: data.description,
        primaryButtonText: data.primaryButtonText || data.ctaText,
        primaryButtonHref: data.primaryButtonHref || data.ctaLink,
        secondaryButtonText: data.secondaryButtonText,
        secondaryButtonHref: data.secondaryButtonHref,
      }

    case 'footer':
      return {
        copyright: data.copyright,
        description: data.description,
        links: data.links,
      }

    case 'header':
      return {
        links: data.links,
        logoUrl: data.logoUrl,
      }

    case 'blog_hero':
      return {
        eyebrow: data.eyebrow,
        showEyebrow: data.showEyebrow ?? true,
        showStandfirst: data.showStandfirst ?? true,
        showMeta: data.showMeta ?? true,
        locale: locale || 'fr',
      }

    case 'blog_category_nav':
      return {
        title: data.title,
        showTitle: data.showTitle ?? false,
        allLabel: data.allLabel ?? 'All',
        locale: locale || 'fr',
        currentCategory: category,
      }

    case 'blog_mosaic':
      return {
        title: data.title,
        showTitle: data.showTitle ?? true,
        limit: data.limit ?? 4,
        locale: locale || 'fr',
      }

    case 'blog_feed':
      return {
        title: data.title,
        showTitle: data.showTitle ?? true,
        pageSize: data.pageSize ?? 10,
        loadMoreLabel: data.loadMoreLabel ?? 'Load more',
        emptyStateTitle: data.emptyStateTitle,
        emptyStateBody: data.emptyStateBody,
        locale: locale || 'fr',
        category: category,
        page: page ?? 1,
      }

    case 'faq':
      return {
        title: data.title,
        subtitle: data.subtitle,
        items: data.items || [],
        ui: data.ui,
      }

    // Help Center sections
    case 'help_hero_v1':
      return {
        kicker: data.kicker,
        title: data.title,
        subtitle: data.subtitle,
        placeholderSearch: data.placeholderSearch,
        helperText: data.helperText,
        backgroundStyle: data.backgroundStyle || 'purple',
        locale: locale || 'fr',
        collectionSlug: collectionSlug,
        collectionTitle: data.collectionTitle, // Will be passed from route
        categorySlug: categorySlug,
        categoryTitle: data.categoryTitle, // Will be passed from route
        showBreadcrumbs: data.showBreadcrumbs ?? false,
        breadcrumbsRootLabel: data.breadcrumbsRootLabel,
        breadcrumbsSeparator: data.breadcrumbsSeparator,
      }

    case 'help_search_v1':
      return {
        placeholder: data.placeholder,
        hint: data.hint,
        clearLabel: data.clearLabel,
        noResultsTitle: data.noResultsTitle,
        noResultsSubtitle: data.noResultsSubtitle,
        locale: locale || 'fr',
        searchQuery: searchQuery,
        collectionSlug: collectionSlug,
        categorySlug: categorySlug,
      }

    case 'help_collections_grid_v1':
      return {
        sectionTitle: data.sectionTitle,
        sectionSubtitle: data.sectionSubtitle,
        cardCtaLabel: data.cardCtaLabel,
        articlesCountLabel: data.articlesCountLabel,
        emptyTitle: data.emptyTitle,
        emptySubtitle: data.emptySubtitle,
        locale: locale || 'fr',
      }

    case 'help_categories_grid_v1':
      return {
        sectionTitle: data.sectionTitle,
        sectionSubtitle: data.sectionSubtitle,
        articlesCountLabel: data.articlesCountLabel,
        emptyTitle: data.emptyTitle,
        emptySubtitle: data.emptySubtitle,
        locale: locale || 'fr',
        collectionSlug: collectionSlug || '',
      }

    case 'help_collection_body_v1':
      return {
        emptyCategoriesTitle: data.emptyCategoriesTitle,
        emptyCategoriesSubtitle: data.emptyCategoriesSubtitle,
        emptyArticlesTitle: data.emptyArticlesTitle,
        emptyArticlesSubtitle: data.emptyArticlesSubtitle,
        locale: locale || 'fr',
        collectionSlug: collectionSlug || '',
      }

    case 'help_breadcrumbs_v1':
      return {
        rootLabel: data.rootLabel,
        separator: data.separator,
        locale: locale || 'fr',
        collectionSlug: collectionSlug,
        collectionTitle: data.collectionTitle, // Will be passed from route
        categorySlug: categorySlug,
        categoryTitle: data.categoryTitle, // Will be passed from route
        articleTitle: data.articleTitle, // Will be passed from route
      }

    case 'help_search_results_v1':
      return {
        resultsTitle: data.resultsTitle,
        resultsCountLabel: data.resultsCountLabel,
        emptyTitle: data.emptyTitle,
        emptySubtitle: data.emptySubtitle,
        locale: locale || 'fr',
        collectionSlug: collectionSlug,
        categorySlug: categorySlug,
        searchQuery: searchQuery,
      }

    case 'help_article_reader_v1':
      return {
        updatedLabel: data.updatedLabel,
        byLabel: data.byLabel,
        readingTimeLabel: data.readingTimeLabel,
        relatedTitle: data.relatedTitle,
        locale: locale || 'fr',
        collectionSlug: collectionSlug || '',
        categorySlug: categorySlug || '',
        articleSlug: articleSlug || '',
      }

    case 'help_sidebar_toc_v1':
      return {
        tocTitle: data.tocTitle,
        locale: locale || 'fr',
        articleId: data.articleId, // Will be passed from route
      }

    default:
      // For unknown sections, pass data as-is with sectionKey instead of key (key is reserved in React)
      return { sectionKey: key, data }
  }
}

