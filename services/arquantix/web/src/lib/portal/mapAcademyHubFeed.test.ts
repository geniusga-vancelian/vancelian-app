import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  mapAcademyHubFromBlogFeed,
  mapAnalysisFromBlogFeed,
  mapVancelianNewsFromBlogFeed,
} from '@/lib/portal/mapAcademyHubFeed'

test('mapAcademyHubFromBlogFeed maps market news and excludes company news', () => {
  const payload = {
    featured: {
      id: 'f1',
      slug: 'featured-slug',
      title: 'Featured',
      articleType: 'NEWS',
      isCompanyNews: false,
      readingTime: 4,
    },
    highlighted: [
      {
        id: 'h1',
        slug: 'highlighted-slug',
        title: 'Highlighted',
        articleType: 'NEWS',
        isCompanyNews: false,
      },
    ],
    companyNews: [
      {
        id: 'c1',
        slug: 'company-slug',
        title: 'Company',
        articleType: 'NEWS',
        isCompanyNews: true,
      },
    ],
    articles: [
      {
        id: 'a1',
        slug: 'news-one',
        title: 'News one',
        articleType: 'NEWS',
        isCompanyNews: false,
      },
      {
        id: 'r1',
        slug: 'research-one',
        title: 'Research one',
        articleType: 'ANALYSIS',
      },
    ],
  }

  const mapped = mapAcademyHubFromBlogFeed(payload, { origin: 'https://app.example' })

  assert.equal(mapped.featured?.title, 'Featured')
  assert.equal(mapped.highlighted.length, 1)
  assert.equal(mapped.marketNews.length, 1)
  assert.equal(mapped.marketNews[0]?.slug, 'news-one')
})

test('mapVancelianNewsFromBlogFeed keeps company news only', () => {
  const payload = {
    featured: {
      id: 'c1',
      slug: 'company-featured',
      title: 'Company featured',
      articleType: 'NEWS',
      isCompanyNews: true,
    },
    articles: [
      {
        id: 'n1',
        slug: 'market-slug',
        title: 'Market',
        articleType: 'NEWS',
        isCompanyNews: false,
      },
      {
        id: 'c2',
        slug: 'company-two',
        title: 'Company two',
        articleType: 'NEWS',
        isCompanyNews: true,
      },
    ],
  }

  const mapped = mapVancelianNewsFromBlogFeed(payload)

  assert.equal(mapped.length, 3)
  assert.ok(mapped.every((item) => item.isCompanyNews))
})

test('mapAnalysisFromBlogFeed keeps ANALYSIS articles only', () => {
  const payload = {
    featured: {
      id: 'a1',
      slug: 'analysis-featured',
      title: 'Analysis featured',
      articleType: 'ANALYSIS',
      readingTime: 8,
    },
    articles: [
      {
        id: 'n1',
        slug: 'news-slug',
        title: 'News',
        articleType: 'NEWS',
      },
      {
        id: 'r1',
        slug: 'research-two',
        title: 'Research legacy',
        articleType: 'RESEARCH',
        readingTime: 6,
      },
    ],
  }

  const mapped = mapAnalysisFromBlogFeed(payload)

  assert.equal(mapped.length, 1)
  assert.equal(mapped[0]?.articleType, 'ANALYSIS')
})
