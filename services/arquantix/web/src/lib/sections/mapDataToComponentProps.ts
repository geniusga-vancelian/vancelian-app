/**
 * Mapping données CMS → props des composants de section.
 * Les coalescences documentées (hero, CTA, famille about) sont
 * centralisées dans `sectionRenderCoalesce.ts` pour tests unitaires dédiés.
 */

import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import type { PublicArticle } from '@/lib/blog/getPublicArticle'
import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import { getLocaleOrDefault } from '@/config/locales'
import { normalizeVancelianDarkColor } from '@/lib/cms/parseEditorialTitle'
import { publicArticlePageUrl } from '@/lib/blog/articlePublicPageUrl'
import type { SectionPageRendererContext } from '@/lib/sections/sectionPageRendererTypes'
import {
  aboutFamilyToProps,
  ctaPrimaryFromLegacy,
  heroBackgroundOpacity01,
  heroResolvedBackgroundUrl,
  projectGridLegacyItemToProp,
} from '@/lib/sections/sectionRenderCoalesce'
import { readShowAllExclusiveOffersFlag } from '@/lib/cms/showAllExclusiveOffersFlag'
import {
  splitCmsBackgroundMedia,
  splitCmsInlineMedia,
} from '@/lib/storage/mediaKind'

/**
 * Map section data to component props based on section key.
 *
 * Exporté pour les tests de cohérence « editor → renderer » et golden tests.
 */
export function mapDataToComponentProps(
  key: string,
  data: any,
  locale?: string,
  category?: string,
  page?: number,
  collectionSlug?: string,
  categorySlug?: string,
  articleSlug?: string,
  searchQuery?: string,
  blogArticle?: PublicArticle | null,
  rendererContext?: SectionPageRendererContext,
  exclusiveOfferVaultPayload?: ExclusiveOfferVaultPayload | null,
  mosaicPage?: number,
  blogSegment?: string,
): any {
  const canonicalKey = resolveCanonicalSectionKey(key) ?? key

  switch (canonicalKey) {
    case 'hero':
    case 'hero_secondary': {
      /** Uniquement le média choisi en CMS (`backgroundMediaId` → `backgroundMediaUrl`). */
      const heroBackgroundUrl = heroResolvedBackgroundUrl(data)
      const backgroundImageOpacity = heroBackgroundOpacity01(data.backgroundImageOpacity)
      const heroMedia = splitCmsBackgroundMedia(data)

      if (process.env.NODE_ENV === 'development') {
        console.log('[SectionRenderer] Hero data mapping:', {
          backgroundMediaUrl: data.backgroundMediaUrl,
          backgroundMediaId: data.backgroundMediaId,
          resolvedHeroBackgroundUrl: heroBackgroundUrl,
        })
      }
      const isSecondary = key === 'hero_secondary'
      const tagList = Array.isArray(data.tags)
        ? data.tags
            .map((t: unknown) => String(t).trim())
            .filter((t: string) => t.length > 0)
        : []
      return {
        backgroundImage: heroMedia.imageUrl,
        backgroundVideoUrl: heroMedia.videoUrl,
        backgroundImageOpacity,
        variant: isSecondary ? 'secondary' : 'homepage',
        /**
         * Même règle que `ExclusiveOfferVaultDetail` : avec image, seul le thème du contenu
         * (texte / pastilles / CTA) passe en contraste sur photo — espacements et typo inchangés dans `SectionHero`.
         */
        inverseOverlay: isSecondary && Boolean(heroBackgroundUrl),
        eyebrow: data.eyebrow,
        inlineStats: Array.isArray(data.inlineStats) ? data.inlineStats : undefined,
        note: data.note,
        typewriterWords: Array.isArray(data.typewriterWords) ? data.typewriterWords : undefined,
        secondaryCtaText: data.secondaryCtaText,
        secondaryCtaHref: data.secondaryCtaHref,
        title: data.title,
        subtitle: data.subtitle,
        ctaText: data.ctaText,
        ctaLink: data.ctaLink,
        sidebarText: data.sidebarText,
        hideCta: data.hideCta === true,
        tags: isSecondary && tagList.length > 0 ? tagList : undefined,
      }
    }

    case 'about':
    case 'about_showcase':
    case 'about_transparency':
    case 'about_registration':
    case 'features':
    case 'feature_grid':
      // `ctaText` / `ctaLink` ne sont volontairement PAS passés : aucun de ces
      // composants ne les rend (cf. audit Famille 3 — `about_cta: remove_mapping`).
      // Les conserver dans le schéma Zod le temps qu'une éventuelle migration
      // décide de leur sort, mais ne pas les pousser au composant pour éviter
      // les attributs DOM non standard et le faux espoir « champ éditable ».
      return aboutFamilyToProps(data)

    case 'testimonials':
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        items: data.items || [],
      }

    case 'projects':
    case 'project_grid': {
      const showAllExclusiveOffers = readShowAllExclusiveOffersFlag(data.showAllExclusiveOffers)
      const viewAllButtonText = data.viewAllButtonText
      // Priority: resolvedProjects (from DB) > items (legacy hardcoded)
      if (data.resolvedProjects && data.resolvedProjects.length > 0) {
        return {
          title: data.title,
          description: data.description,
          eyebrow: data.eyebrow,
          resolvedProjects: data.resolvedProjects,
          showAllExclusiveOffers,
          viewAllButtonText,
        }
      }
      return {
        title: data.title,
        description: data.description,
        eyebrow: data.eyebrow,
        showAllExclusiveOffers,
        viewAllButtonText,
        items: data.items?.map((item: any) => projectGridLegacyItemToProp(item)),
      }
    }

    case 'cta': {
      const primary = ctaPrimaryFromLegacy(data)
      const bg = splitCmsBackgroundMedia(data)
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        primaryButtonText: primary.primaryButtonText,
        primaryButtonHref: primary.primaryButtonHref,
        secondaryButtonText: data.secondaryButtonText,
        secondaryButtonHref: data.secondaryButtonHref,
        showPrimaryButton: data.showPrimaryButton !== false,
        showSecondaryButton: data.showSecondaryButton !== false,
        contentTextAlign:
          data.contentTextAlign === 'justify' ? ('justify' as const) : ('center' as const),
        backgroundMediaUrl: bg.imageUrl,
        backgroundVideoUrl: bg.videoUrl,
        backgroundColor: normalizeVancelianDarkColor(
          typeof data.backgroundColor === 'string' && data.backgroundColor.trim()
            ? data.backgroundColor.trim()
            : undefined,
        ),
        backgroundImageOpacity:
          typeof data.backgroundImageOpacity === 'number' &&
          Number.isFinite(data.backgroundImageOpacity)
            ? Math.min(1, Math.max(0, data.backgroundImageOpacity))
            : 1,
        overlayOpacity:
          typeof data.overlayOpacity === 'number' && Number.isFinite(data.overlayOpacity)
            ? Math.min(1, Math.max(0, data.overlayOpacity))
            : 0.55,
        marketingVariant: 'image' as const,
      }
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
        ctaLabel: data.ctaLabel,
        showTitle: data.showTitle ?? true,
        limit: data.limit ?? 3,
        paginationPrevLabel: data.paginationPrevLabel,
        paginationNextLabel: data.paginationNextLabel,
        locale: locale || 'fr',
        mosaicPage: mosaicPage ?? 1,
        blogFeedPage: page ?? 1,
        category,
        blogSegment,
      }

    case 'blog_feed':
      return {
        title: data.title,
        showTitle: data.showTitle ?? true,
        pageSize: data.pageSize ?? 10,
        loadMoreLabel: data.loadMoreLabel ?? siteCommonCta(locale, 'load_more'),
        emptyStateTitle: data.emptyStateTitle,
        emptyStateBody: data.emptyStateBody,
        locale: locale || 'fr',
        category: category,
        page: page ?? 1,
      }

    case 'blog_article_hero':
      return {
        locale: locale || 'fr',
        showBreadcrumb: data.showBreadcrumb === true,
        blogLabel: data.blogLabel,
        breadcrumbCurrentText:
          typeof data.breadcrumbCurrentText === 'string' ? data.breadcrumbCurrentText : undefined,
        title: typeof data.title === 'string' ? data.title : '',
        standfirst: typeof data.standfirst === 'string' ? data.standfirst : undefined,
        categoryPillLabels: Array.isArray(data.categoryPillLabels)
          ? (data.categoryPillLabels as unknown[]).filter((x): x is string => typeof x === 'string')
          : [],
        editorialPillLabel:
          typeof data.editorialPillLabel === 'string' ? data.editorialPillLabel : undefined,
        authorName: typeof data.authorName === 'string' ? data.authorName : undefined,
        authorRole: typeof data.authorRole === 'string' ? data.authorRole : undefined,
        showAuthorByPrefix: data.showAuthorByPrefix === true,
        showReadingTime: data.showReadingTime !== false,
        readingTimeText: typeof data.readingTimeText === 'string' ? data.readingTimeText : undefined,
        showDate: data.showDate !== false,
        publishedAtIso: typeof data.publishedAtIso === 'string' ? data.publishedAtIso : undefined,
        showUpdatedDate: data.showUpdatedDate === true,
        updatedAtIso: typeof data.updatedAtIso === 'string' ? data.updatedAtIso : undefined,
        coverTitle: typeof data.coverTitle === 'string' ? data.coverTitle : undefined,
        coverUrl: typeof data.imageMediaUrl === 'string' ? data.imageMediaUrl : '',
        videoUrl: typeof data.videoUrl === 'string' ? data.videoUrl : undefined,
        coverCredit: typeof data.coverCredit === 'string' ? data.coverCredit : undefined,
        coverSource: typeof data.coverSource === 'string' ? data.coverSource : undefined,
      }

    case 'blog_article_reader': {
      const demoArticle =
        data && typeof data === 'object' && data.__demoBlogArticle != null
          ? (data.__demoBlogArticle as PublicArticle)
          : null
      return {
        blogLabel: data.blogLabel,
        tocTitle: data.tocTitle,
        showToc: data.showToc !== false,
        tocMinHeadings: typeof data.tocMinHeadings === 'number' ? data.tocMinHeadings : 3,
        showDocuments: data.showDocuments !== false,
        documentsTitle: data.documentsTitle,
        readingTimeLabel: data.readingTimeLabel,
        showAuthorByPrefix: data.showAuthorByPrefix === true,
        authorPrefixLabel: data.authorPrefixLabel,
        showUpdatedDate: data.showUpdatedDate === true,
        locale: locale || 'fr',
        blogArticle: blogArticle ?? demoArticle,
        shareSmData: rendererContext?.shareSmSection?.data ?? null,
        showBreadcrumb: data?.showBreadcrumb !== false,
      }
    }

    case 'share_sm': {
      const loc = getLocaleOrDefault(locale || 'fr')
      let pageUrl = ''
      let articleTitle = ''
      if (blogArticle) {
        pageUrl = publicArticlePageUrl(loc, blogArticle.slug)
        articleTitle = blogArticle?.i18n?.title ?? ''
      } else if (exclusiveOfferVaultPayload) {
        pageUrl = `/${loc}/projects/${exclusiveOfferVaultPayload.pageSlug}`
        articleTitle =
          exclusiveOfferVaultPayload.heroTitle || exclusiveOfferVaultPayload.pageTitle || ''
      }
      return {
        title: data.title,
        items: data.items || [],
        pageUrl,
        articleTitle,
      }
    }

    case 'exclusive_offer_vault':
      return { exclusiveOfferVaultPayload }

    case 'blog_article_related':
      return {
        title: data.title,
        ctaLabel: data.ctaLabel,
        ctaHref: data.ctaHref,
        limit: typeof data.limit === 'number' ? data.limit : 4,
        emptyTitle: data.emptyTitle,
        locale: locale || 'fr',
        currentArticleId: blogArticle?.id ?? '',
      }

    case 'faq':
      // Convention Surtitre / Titre / Description (cf. uniformisation modules CMS).
      // - `eyebrow` : surtitre / pastille (CMS, traduisible).
      // - `title`   : titre canonique du module — l'admin écrit ici.
      // - `subtitle`: champ legacy (ancien emplacement du titre) — lu en fallback
      //               par `FaqSection` pour ne pas casser les contenus existants.
      // - `description` : chapô optionnel sous le titre (nouveau, traduisible).
      // - `ui` : libellés optionnels « tout ouvrir / tout fermer » (design-system FAQ).
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        subtitle: data.subtitle,
        items: data.items || [],
        ...(data.support != null &&
        typeof data.support === 'object' &&
        !Array.isArray(data.support)
          ? { support: data.support }
          : {}),
        ...(data.ui != null &&
        typeof data.ui === 'object' &&
        !Array.isArray(data.ui) &&
        Object.keys(data.ui as object).length > 0
          ? { ui: data.ui }
          : {}),
      }

    case 'how_it_works':
      return {
        label: data.label,
        title: data.title,
        subtitle: data.subtitle,
        hideStepNumbering: data.hideStepNumbering === true,
        steps:
          Array.isArray(data.steps) && data.steps.length > 0 ? data.steps : undefined,
        primaryCtaText: data.primaryCtaText,
        primaryCtaHref: data.primaryCtaHref,
        secondaryCtaText: data.secondaryCtaText,
        secondaryCtaHref: data.secondaryCtaHref,
        /* Toujours fond clair + CTA plein (la valeur CMS `surface` historique est ignorée). */
        surface: 'light' as const,
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

    case 'figma_simple_hero':
      return {
        title: data.title,
        description: data.description,
        backgroundColor: data.backgroundColor,
        textColor: data.textColor,
      }

    case 'figma_stats_grid':
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        stats: Array.isArray(data.stats) ? data.stats : [],
        columns:
          data.columns === 6 ? 6 : data.columns === 4 ? 4 : 3,
      }

    case 'key_figures': {
      const bg = splitCmsBackgroundMedia(data)
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        stats: Array.isArray(data.stats) ? data.stats : [],
        backgroundMediaUrl: bg.imageUrl,
        backgroundVideoUrl: bg.videoUrl,
        backgroundColor: normalizeVancelianDarkColor(
          typeof data.backgroundColor === 'string' && data.backgroundColor.trim()
            ? data.backgroundColor.trim()
            : undefined,
        ),
        backgroundImageOpacity:
          typeof data.backgroundImageOpacity === 'number' &&
          Number.isFinite(data.backgroundImageOpacity)
            ? Math.min(1, Math.max(0, data.backgroundImageOpacity))
            : 1,
        overlayOpacity:
          typeof data.overlayOpacity === 'number' && Number.isFinite(data.overlayOpacity)
            ? Math.min(1, Math.max(0, data.overlayOpacity))
            : 0,
      }
    }

    case 'figma_testimonial_cards':
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        cardsPerRow: data.cardsPerRow === 2 ? 2 : 1,
        items: Array.isArray(data.items) ? data.items : [],
      }

    case 'proof_press':
      return {
        eyebrow: data.eyebrow,
        items: Array.isArray(data.items) ? data.items : [],
      }

    case 'offer_cards':
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        viewAllButtonText: data.viewAllButtonText,
        viewAllButtonHref: data.viewAllButtonHref,
        items: Array.isArray(data.items) ? data.items : [],
      }

    case 'product_ecosystem':
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        items: Array.isArray(data.items) ? data.items : [],
      }

    case 'journey': {
      const bg = splitCmsBackgroundMedia(data)
      return {
        pill: data.pill,
        title: data.title,
        description: data.description,
        backgroundMediaUrl: bg.videoUrl ?? bg.imageUrl,
        backgroundMediaMimeType: bg.videoUrl ? 'video/mp4' : data.backgroundMediaMimeType,
        notificationMessage: data.notificationMessage,
        ctas: Array.isArray(data.ctas) ? data.ctas : [],
      }
    }

    case 'security':
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        points: Array.isArray(data.points) ? data.points : [],
        linkText: data.linkText,
        linkHref: data.linkHref,
        logos: Array.isArray(data.logos) ? data.logos : [],
      }

    case 'media_text': {
      const media = splitCmsInlineMedia(data)
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        imageMediaUrl: media.imageUrl,
        videoMediaUrl: media.videoUrl,
        imageMediaAlt: data.imageMediaAlt,
        mediaRight: data.mediaRight === true,
      }
    }

    case 'company_map': {
      const bg = splitCmsBackgroundMedia(data)
      return {
        eyebrow: data.eyebrow,
        title: data.title,
        description: data.description,
        backgroundMediaUrl: bg.imageUrl,
        backgroundVideoUrl: bg.videoUrl,
        backgroundMediaAlt: data.backgroundMediaAlt,
        bodyContent: data.bodyContent,
      }
    }

    default:
      // For unknown sections, pass data as-is with sectionKey instead of key (key is reserved in React)
      return { sectionKey: key, data }
  }
}
