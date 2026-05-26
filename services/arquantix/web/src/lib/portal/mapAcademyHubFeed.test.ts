import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  mapAcademyHubFromBlogFeed,
  mapAcademyResearchFromBlogFeed,
} from '@/lib/portal/mapAcademyHubFeed'

test('mapAcademyHubFromBlogFeed maps featured, highlighted and news with portal hrefs', () => {
  const payload = {
    featured: {
      id: 'f1',
      slug: 'featured-slug',
      title: 'Featured',
      standfirst: 'Lead',
      coverUrl: 'https://cdn.example/cover.jpg',
      authorName: 'Editor',
      publishedAt: '2026-01-01T00:00:00.000Z',
      readingTime: 4,
      articleType: 'NEWS',
    },
    highlighted: [
      {
        id: 'h1',
        slug: 'highlighted-slug',
        title: 'Highlighted',
        articleType: 'NEWS',
        readingTime: 3,
      },
    ],
    articles: [
      {
        id: 'a1',
        slug: 'news-one',
        title: 'News one',
        articleType: 'NEWS',
        readingTime: 2,
      },
      {
        id: 'f1',
        slug: 'featured-slug',
        title: 'Duplicate featured',
        articleType: 'NEWS',
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
  assert.equal(mapped.featured?.href, 'https://app.example/app/academy/featured-slug')
  assert.equal(mapped.highlighted.length, 1)
  assert.equal(mapped.highlighted[0]?.href, 'https://app.example/app/academy/highlighted-slug')
  assert.equal(mapped.news.length, 1)
  assert.equal(mapped.news[0]?.slug, 'news-one')
})

test('mapAcademyResearchFromBlogFeed keeps analysis articles only', () => {
  const payload = {
    featured: {
      id: 'r1',
      slug: 'research-featured',
      title: 'Research featured',
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
        id: 'r2',
        slug: 'research-two',
        title: 'Research two',
        articleType: 'RESEARCH',
        readingTime: 6,
      },
    ],
  }

  const mapped = mapAcademyResearchFromBlogFeed(payload)

  assert.equal(mapped.length, 2)
  assert.ok(mapped.every((item) => item.href.startsWith('/app/academy/')))
  assert.deepEqual(
    mapped.map((item) => item.title),
    ['Research featured', 'Research two'],
  )
})
