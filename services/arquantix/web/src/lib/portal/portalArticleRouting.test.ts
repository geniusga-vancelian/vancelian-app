import assert from 'node:assert/strict'
import test from 'node:test'

import {
  portalAcademyHubRoute,
  portalArticleRoute,
  resolvePortalArticleHref,
} from './portalArticleRouting'

test('portalArticleRoute builds /app/academy/{slug}', () => {
  assert.equal(portalArticleRoute('bitcoin-et-etf'), '/app/academy/bitcoin-et-etf')
  assert.equal(portalArticleRoute(''), portalAcademyHubRoute())
})

test('resolvePortalArticleHref absolutizes with origin', () => {
  assert.equal(
    resolvePortalArticleHref('foo', 'https://app.example.com'),
    'https://app.example.com/app/academy/foo',
  )
})
