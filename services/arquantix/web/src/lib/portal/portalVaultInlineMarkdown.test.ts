import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

import { PortalVaultFaqBodyMarkdown, PortalVaultInlineMarkdown } from './portalVaultInlineMarkdown'

describe('PortalVaultInlineMarkdown', () => {
  it('interprète le gras dans les champs texte Vault portail', () => {
    const html = renderToStaticMarkup(
      PortalVaultInlineMarkdown({ text: '**DTCC**, **NYSE** et **Nasdaq**' }),
    )
    assert.match(html, /<strong[^>]*>DTCC<\/strong>/)
    assert.match(html, /<strong[^>]*>NYSE<\/strong>/)
    assert.doesNotMatch(html, /\*\*DTCC\*\*/)
  })

  it('interprète le gras dans les réponses FAQ accordéon', () => {
    const html = renderToStaticMarkup(
      PortalVaultFaqBodyMarkdown({
        text: 'The projected fixed annual return is **11.5% APR**, paid **daily in Bitcoin**.',
      }),
    )
    assert.match(html, /faq__body/)
    assert.match(html, /<strong[^>]*>11\.5% APR<\/strong>/)
    assert.match(html, /<strong[^>]*>daily in Bitcoin<\/strong>/)
    assert.doesNotMatch(html, /\*\*11\.5% APR\*\*/)
  })
})
