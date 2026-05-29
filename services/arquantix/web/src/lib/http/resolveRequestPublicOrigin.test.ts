import assert from 'node:assert/strict'
import { test } from 'node:test'
import { NextRequest } from 'next/server'

import { resolveRequestPublicOrigin } from './resolveRequestPublicOrigin'

function makeRequest(url: string, headers: Record<string, string> = {}): NextRequest {
  return new NextRequest(url, { headers })
}

test('resolveRequestPublicOrigin : x-forwarded-host prioritaire', () => {
  const request = makeRequest('https://0.0.0.0:3000/api/portal/academy', {
    'x-forwarded-host': 'app.vancelian.finance',
    'x-forwarded-proto': 'https',
  })
  assert.equal(resolveRequestPublicOrigin(request), 'https://app.vancelian.finance')
})

test('resolveRequestPublicOrigin : ignore bind interne 0.0.0.0', () => {
  const request = makeRequest('https://0.0.0.0:3000/api/blog')
  assert.equal(resolveRequestPublicOrigin(request), null)
})

test('resolveRequestPublicOrigin : host header en dev local', () => {
  const request = makeRequest('http://127.0.0.1:3000/api/blog', {
    host: 'localhost:3000',
  })
  assert.equal(resolveRequestPublicOrigin(request), 'http://localhost:3000')
})
