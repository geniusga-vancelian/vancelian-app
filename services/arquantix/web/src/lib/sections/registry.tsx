/**
 * Section Registry - Maps section keys to React components
 * This is used by SectionRenderer to render the appropriate component
 */

import { SectionHero } from '@/components/sections/SectionHero'
import { SectionAbout } from '@/components/sections/SectionAbout'
import { SectionProjects } from '@/components/sections/SectionProjects'
import { SectionCTA } from '@/components/sections/SectionCTA'
import { Footer } from '@/components/sections/Footer'
import { Navigation } from '@/components/sections/Navigation'
import { SectionBlogHero } from '@/components/sections/SectionBlogHero'
import { SectionBlogCategoryNav } from '@/components/sections/SectionBlogCategoryNav'
import { SectionBlogMosaic } from '@/components/sections/SectionBlogMosaic'
import { SectionBlogFeed } from '@/components/sections/SectionBlogFeed'
import { FaqSection } from '@/components/sections/FaqSection'
import { SectionHelpHero } from '@/components/sections/SectionHelpHero'
import { SectionHelpSearch } from '@/components/sections/SectionHelpSearch'
import { SectionHelpCollectionsGrid } from '@/components/sections/SectionHelpCollectionsGrid'
import { SectionHelpCategoriesGrid } from '@/components/sections/SectionHelpCategoriesGrid'
import { SectionHelpBreadcrumbs } from '@/components/sections/SectionHelpBreadcrumbs'
import { SectionHelpSearchResults } from '@/components/sections/SectionHelpSearchResults'
import { SectionHelpArticleReader } from '@/components/sections/SectionHelpArticleReader'
import { SectionHelpSidebarToc } from '@/components/sections/SectionHelpSidebarToc'
import { SectionHelpCollectionBody } from '@/components/sections/SectionHelpCollectionBody'
import type { SectionHeroProps } from '@/components/sections/SectionHero'
import type { SectionProjectsProps } from '@/components/sections/SectionProjects'
import type { SectionAboutProps } from '@/components/sections/SectionAbout'
import type { SectionCTAProps } from '@/components/sections/SectionCTA'
import type { FooterProps } from '@/components/sections/Footer'
import React from 'react'

// Placeholder components for sections not yet implemented
function PlaceholderSection({ sectionKey, data }: { sectionKey: string; data: any }) {
  return (
    <div className="bg-yellow-50 border border-yellow-200 p-8 my-4 text-center">
      <p className="text-yellow-800 font-semibold">Section: {sectionKey}</p>
      <p className="text-yellow-600 text-sm mt-2">
        This section type is not yet implemented. Data:
      </p>
      <pre className="mt-4 text-xs text-left bg-yellow-100 p-4 rounded overflow-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  )
}

export interface SectionComponentProps {
  [key: string]: any
}

export type SectionComponent = React.ComponentType<SectionComponentProps>

/**
 * Registry mapping section keys to React components
 */
export const SECTION_REGISTRY: Record<string, SectionComponent> = {
  header: Navigation as SectionComponent,
  hero: SectionHero as SectionComponent,
  features: SectionAbout as SectionComponent, // feature_grid uses SectionAbout
  feature_grid: SectionAbout as SectionComponent,
  about: SectionAbout as SectionComponent,
  projects: SectionProjects as SectionComponent,
  project_grid: SectionProjects as SectionComponent,
  cta: SectionCTA as SectionComponent,
  footer: Footer as SectionComponent,
  blog_list: PlaceholderSection as SectionComponent, // Placeholder for Phase C
  blog_hero: SectionBlogHero as SectionComponent,
  blog_category_nav: SectionBlogCategoryNav as SectionComponent,
  blog_mosaic: SectionBlogMosaic as SectionComponent,
  blog_feed: SectionBlogFeed as SectionComponent,
  faq: FaqSection as SectionComponent,
  // Help Center sections
  help_hero_v1: SectionHelpHero as SectionComponent,
  help_search_v1: SectionHelpSearch as SectionComponent,
  help_collections_grid_v1: SectionHelpCollectionsGrid as SectionComponent,
  help_categories_grid_v1: SectionHelpCategoriesGrid as SectionComponent,
  help_collection_body_v1: SectionHelpCollectionBody as SectionComponent,
  help_breadcrumbs_v1: SectionHelpBreadcrumbs as SectionComponent,
  help_search_results_v1: SectionHelpSearchResults as SectionComponent,
  help_article_reader_v1: SectionHelpArticleReader as SectionComponent,
  help_sidebar_toc_v1: SectionHelpSidebarToc as SectionComponent,
}

/**
 * Get component for a section key
 */
export function getSectionComponent(key: string): SectionComponent | undefined {
  return SECTION_REGISTRY[key]
}

/**
 * Check if a section key has a registered component
 */
export function hasSectionComponent(key: string): boolean {
  return key in SECTION_REGISTRY
}

