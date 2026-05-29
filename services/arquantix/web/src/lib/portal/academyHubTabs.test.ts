import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  articleMatchesAcademyEditorialTab,
  type PortalAcademyEditorialTabId,
} from '@/lib/portal/academyHubTabs'
import type { PortalAcademyArticle } from '@/lib/portal/academyHubTypes'

function article(
  overrides: Partial<PortalAcademyArticle> & Pick<PortalAcademyArticle, 'articleType'>,
): PortalAcademyArticle {
  return {
    id: '1',
    slug: 'slug',
    title: 'Title',
    standfirst: '',
    coverUrl: '',
    authorName: 'Vancelian',
    publishedAt: null,
    readingTime: 3,
    href: '/app/academy/slug',
    categorySlug: null,
    categoryLabel: null,
    categoryTone: 'ink',
    isCompanyNews: false,
    ...overrides,
  }
}

test('articleMatchesAcademyEditorialTab filters by editorial segment', () => {
  const market = article({ articleType: 'NEWS', isCompanyNews: false })
  const vancelian = article({ articleType: 'NEWS', isCompanyNews: true })
  const analysis = article({ articleType: 'ANALYSIS' })
  const academy = article({ articleType: 'ACADEMY' })

  const cases: Array<[PortalAcademyEditorialTabId, PortalAcademyArticle, boolean]> = [
    ['market-news', market, true],
    ['market-news', vancelian, false],
    ['vancelian-news', vancelian, true],
    ['vancelian-news', market, false],
    ['analysis', analysis, true],
    ['analysis', market, false],
    ['academy', academy, true],
    ['academy', analysis, false],
  ]

  for (const [tab, row, expected] of cases) {
    assert.equal(articleMatchesAcademyEditorialTab(row, tab), expected, tab)
  }
})
