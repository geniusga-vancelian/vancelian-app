'use client'

import { useEffect, useMemo, useState } from 'react'

import { PortalPortfolioLayout } from '@/components/portal/dashboard/PortalPortfolioLayout'
import { PortalAcademyAdvisorCta } from '@/components/portal/academy/PortalAcademyAdvisorCta'
import { PortalAcademyArticleCard } from '@/components/portal/academy/PortalAcademyArticleCard'
import { PortalAcademyCategoryTabs } from '@/components/portal/academy/PortalAcademyCategoryTabs'
import { PortalAcademyHero } from '@/components/portal/academy/PortalAcademyHero'
import { PortalAcademyPagination } from '@/components/portal/academy/PortalAcademyPagination'
import { PortalAcademySearch } from '@/components/portal/academy/PortalAcademySearch'
import { PortalAcademySidebar } from '@/components/portal/academy/PortalAcademySidebar'
import { PortalPageContainer } from '@/components/portal/PortalPageContainer'
import { PortalReveal } from '@/components/portal/PortalReveal'
import { PortalAcademySkeleton } from '@/components/portal/PortalRouteSkeleton'
import {
  academyArticleMatchesSearch,
  normalizeAcademySearch,
} from '@/lib/portal/academyFormat'
import type { PortalAcademyArticle, PortalAcademyHubPayload } from '@/lib/portal/academyHubTypes'
import {
  articleMatchesAcademyEditorialTab,
  buildAcademyHubCatalog,
  PORTAL_ACADEMY_DEFAULT_TAB,
  PORTAL_ACADEMY_EDITORIAL_TABS,
  type PortalAcademyEditorialTabId,
} from '@/lib/portal/academyHubTabs'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import { Container } from '@/components/ui/Container'

const ACADEMY_CACHE_KEY = 'portal:academy:v3'
const ARTICLES_PER_PAGE = 6

function resolveSidebarHighlighted(
  highlighted: PortalAcademyArticle[],
  featured: PortalAcademyArticle | null,
): PortalAcademyArticle[] {
  const exclude = new Set<string>()
  if (featured) exclude.add(featured.id)
  return highlighted.filter((item) => !exclude.has(item.id)).slice(0, 4)
}

export function PortalAcademyScreen() {
  const { data, loading, error, refresh } = usePortalCachedScreen<PortalAcademyHubPayload>({
    cacheKey: ACADEMY_CACHE_KEY,
    url: '/api/portal/academy',
    ttlMs: 120_000,
    errorMessage: 'Unable to load Academy.',
  })

  const [query, setQuery] = useState('')
  const [activeTab, setActiveTab] = useState<PortalAcademyEditorialTabId>(PORTAL_ACADEMY_DEFAULT_TAB)
  const [page, setPage] = useState(1)

  const catalog = useMemo(() => (data ? buildAcademyHubCatalog(data) : []), [data])

  useEffect(() => {
    setPage(1)
  }, [activeTab, query])

  const hasSearch = normalizeAcademySearch(query).trim().length > 0
  const showMarketHero = !hasSearch && activeTab === 'market-news'

  const filtered = useMemo(() => {
    if (!data) return [] as PortalAcademyArticle[]

    let pool = catalog.filter((article) => articleMatchesAcademyEditorialTab(article, activeTab))

    if (showMarketHero && data.featured) {
      pool = pool.filter((article) => article.id !== data.featured?.id)
    }
    if (hasSearch) {
      pool = pool.filter((article) => academyArticleMatchesSearch(article, query))
    }
    return pool
  }, [activeTab, catalog, data, hasSearch, query, showMarketHero])

  const pageCount = Math.max(1, Math.ceil(filtered.length / ARTICLES_PER_PAGE))
  const safePage = Math.min(page, pageCount)
  const visible = filtered.slice((safePage - 1) * ARTICLES_PER_PAGE, safePage * ARTICLES_PER_PAGE)

  const sidebarHighlighted = useMemo(
    () => (data ? resolveSidebarHighlighted(data.highlighted, data.featured) : []),
    [data],
  )

  if (loading && !data) return <PortalAcademySkeleton />

  if (error && !data) {
    return (
      <Container className="flex min-h-[50vh] flex-col items-center justify-center gap-4 py-10">
        <p className="m-0 font-ui text-[15px] text-v-error">{error}</p>
        <button
          type="button"
          onClick={() => void refresh()}
          className="v-text-link border-0 bg-transparent p-0 font-ui text-[14px]"
        >
          Try again
        </button>
      </Container>
    )
  }

  if (!data) return null

  const emptyMessage = hasSearch
    ? 'No articles match your search.'
    : 'No articles in this category yet.'

  return (
    <PortalPageContainer>
      <PortalPortfolioLayout
        main={
          <div className="acd-page">
            <PortalReveal index={0}>
              <PortalAcademySearch value={query} onChange={setQuery} />
            </PortalReveal>

            {showMarketHero && data.featured ? (
              <PortalReveal index={1}>
                <PortalAcademyHero article={data.featured} />
              </PortalReveal>
            ) : null}

            <PortalReveal index={showMarketHero && data.featured ? 2 : 1}>
              <PortalAcademyCategoryTabs
                tabs={PORTAL_ACADEMY_EDITORIAL_TABS}
                activeTab={activeTab}
                onTabChange={(tabId) => setActiveTab(tabId as PortalAcademyEditorialTabId)}
              />
            </PortalReveal>

            <PortalReveal index={showMarketHero && data.featured ? 3 : 2}>
              <section className="acd-sec">
                {visible.length > 0 ? (
                  <div className="acd-grid acd-grid--3">
                    {visible.map((article) => (
                      <PortalAcademyArticleCard key={article.id} article={article} />
                    ))}
                  </div>
                ) : (
                  <p className="acd-empty">{emptyMessage}</p>
                )}
              </section>
            </PortalReveal>

            <PortalReveal index={showMarketHero && data.featured ? 4 : 3}>
              <PortalAcademyPagination page={safePage} pageCount={pageCount} onChange={setPage} />
            </PortalReveal>

            <PortalReveal index={showMarketHero && data.featured ? 5 : 4}>
              <PortalAcademyAdvisorCta />
            </PortalReveal>
          </div>
        }
        side={<PortalAcademySidebar highlighted={sidebarHighlighted} />}
      />
    </PortalPageContainer>
  )
}
