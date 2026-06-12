import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

import { PortalArticleMarkdown } from './portalArticleBodyMarkdown'

describe('PortalArticleMarkdown', () => {
  it('interprète le gras en variante inline (citations / listes)', () => {
    const html = renderToStaticMarkup(
      PortalArticleMarkdown({ text: '**$5.5 trillion** en tokenisation', variant: 'inline' }),
    )
    assert.match(html, /<strong[^>]*>\$5\.5 trillion<\/strong>/)
    assert.doesNotMatch(html, /\*\*\$5\.5 trillion\*\*/)
  })

  it('interprète le gras en variante body (paragraphes)', () => {
    const html = renderToStaticMarkup(
      PortalArticleMarkdown({ text: 'Paragraphe avec **gras**.' }),
    )
    assert.match(html, /art-prose__p/)
    assert.match(html, /<strong[^>]*>gras<\/strong>/)
  })
})
