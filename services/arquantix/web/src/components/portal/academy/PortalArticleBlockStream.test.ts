import assert from 'node:assert/strict'
import test from 'node:test'
import { ArticleBlockType } from '@prisma/client'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

import { buildPortalArticleBlockElements } from '@/components/portal/academy/PortalArticleBlockStream'
import { PORTAL_ARTICLE_MODULE_MAP } from '@/lib/portal/portalArticleModuleMap'

test('portal article module map covers all ArticleBlockType values', () => {
  const mapped = new Set(Object.keys(PORTAL_ARTICLE_MODULE_MAP))
  for (const type of Object.values(ArticleBlockType)) {
    assert.ok(mapped.has(type), `missing portal mapping for ${type}`)
  }
})

test('buildPortalArticleBlockElements renders art-prose DS classes', () => {
  const { elements, headings } = buildPortalArticleBlockElements([
    {
      id: 'h1',
      type: ArticleBlockType.HEADING,
      data: { text: 'Les étapes' },
      imageUrl: null,
    },
    {
      id: 'p1',
      type: ArticleBlockType.PARAGRAPH,
      data: { text: 'Un paragraphe **gras**.' },
      imageUrl: null,
    },
    {
      id: 'q1',
      type: ArticleBlockType.QUOTE,
      data: { text: '**$5.5 trillion** en tokenisation', author: 'Citi' },
      imageUrl: null,
    },
    {
      id: 'b1',
      type: ArticleBlockType.BULLET_LIST,
      data: { items: ['**Institutional** providers', 'Point B'] },
      imageUrl: null,
    },
    {
      id: 'n1',
      type: ArticleBlockType.NUMBERED_LIST,
      data: { items: ['Étape 1', 'Étape 2'] },
      imageUrl: null,
    },
  ])

  const html = elements.map((e) => renderToStaticMarkup(e.element)).join('\n')
  assert.match(html, /art-prose__h2/)
  assert.match(html, /art-prose__p/)
  assert.match(html, /art-prose__quote/)
  assert.match(html, /art-prose__check/)
  assert.match(html, /art-prose__ol/)
  assert.match(html, /<strong[^>]*>\$5\.5 trillion<\/strong>/)
  assert.match(html, /<strong[^>]*>Institutional<\/strong>/)
  assert.doesNotMatch(html, /\*\*\$5\.5 trillion\*\*/)
  assert.equal(headings.length, 1)
  assert.equal(headings[0]?.id, 'les-etapes')
})
