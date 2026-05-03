import { test, afterEach } from 'node:test'
import assert from 'node:assert/strict'
import { absoluteUrlForPath, getSiteOrigin } from './siteOrigin'

const saved: Record<string, string | undefined> = {
  NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL,
  VERCEL_URL: process.env.VERCEL_URL,
}

afterEach(() => {
  for (const k of ['NEXT_PUBLIC_SITE_URL', 'VERCEL_URL'] as const) {
    if (saved[k] === undefined) delete process.env[k]
    else process.env[k] = saved[k]
  }
})

test('getSiteOrigin : NEXT_PUBLIC_SITE_URL prioritaire', () => {
  delete process.env.VERCEL_URL
  process.env.NEXT_PUBLIC_SITE_URL = 'https://example.com/path/'
  assert.equal(getSiteOrigin(), 'https://example.com')
})

test('getSiteOrigin : repli VERCEL_URL', () => {
  delete process.env.NEXT_PUBLIC_SITE_URL
  process.env.VERCEL_URL = 'my-app.vercel.app'
  assert.equal(getSiteOrigin(), 'https://my-app.vercel.app')
})

test('absoluteUrlForPath', () => {
  process.env.NEXT_PUBLIC_SITE_URL = 'https://example.com'
  assert.equal(absoluteUrlForPath('/foo'), 'https://example.com/foo')
})
