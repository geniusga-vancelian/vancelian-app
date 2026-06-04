import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { ArticleBodyMarkdown } from './articleBodyMarkdown'

describe('ArticleBodyMarkdown', () => {
  it('interprète le gras en variante inline (listes / citations)', () => {
    const html = renderToStaticMarkup(
      ArticleBodyMarkdown({ text: 'Point **important** et *italique*', variant: 'inline' }),
    )
    assert.match(html, /<strong[^>]*>important<\/strong>/)
    assert.match(html, /<em[^>]*>italique<\/em>/)
    assert.doesNotMatch(html, /\*\*important\*\*/)
  })
})
