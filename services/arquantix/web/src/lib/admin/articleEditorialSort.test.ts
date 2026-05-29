import assert from 'node:assert/strict'
import test from 'node:test'
import { sortArticlesEditorialOrder } from './articleEditorialSort'

test('sortArticlesEditorialOrder: featured, then highlighted by date, then rest by createdAt', () => {
  const rows = [
    {
      key: 'old-regular',
      isFeatured: false,
      isHighlighted: false,
      createdAt: '2024-01-01T00:00:00.000Z',
      publishedAt: null,
    },
    {
      key: 'highlight-old',
      isFeatured: false,
      isHighlighted: true,
      createdAt: '2024-02-01T00:00:00.000Z',
      publishedAt: '2024-02-10T00:00:00.000Z',
    },
    {
      key: 'featured',
      isFeatured: true,
      isHighlighted: false,
      createdAt: '2023-01-01T00:00:00.000Z',
      publishedAt: '2023-06-01T00:00:00.000Z',
    },
    {
      key: 'highlight-new',
      isFeatured: false,
      isHighlighted: true,
      createdAt: '2024-03-01T00:00:00.000Z',
      publishedAt: '2024-03-15T00:00:00.000Z',
    },
    {
      key: 'new-regular',
      isFeatured: false,
      isHighlighted: false,
      createdAt: '2024-05-01T00:00:00.000Z',
      publishedAt: null,
    },
  ]

  const sorted = sortArticlesEditorialOrder(rows)

  assert.deepEqual(
    sorted.map((r) => r.key),
    ['featured', 'highlight-new', 'highlight-old', 'new-regular', 'old-regular']
  )
})
