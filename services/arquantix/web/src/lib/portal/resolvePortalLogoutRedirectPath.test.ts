import test from 'node:test'
import assert from 'node:assert/strict'
import {
  portalLogoutRedirectPathFallback,
  resolvePortalLogoutRedirectPath,
  resolvePortalLogoutRedirectUrl,
} from '@/lib/portal/resolvePortalLogoutRedirectPath'

test('portalLogoutRedirectPathFallback inclut signed_out', () => {
  assert.equal(portalLogoutRedirectPathFallback(), '/app/login?signed_out=1')
})

test('resolvePortalLogoutRedirectPath accepte login verify relatif', () => {
  assert.equal(
    resolvePortalLogoutRedirectPath('/app/login/verify?email=a%40b.com'),
    '/app/login/verify?email=a%40b.com',
  )
})

test('resolvePortalLogoutRedirectPath rejette URL absolue et chemins non auth', () => {
  const fallback = '/app/login?signed_out=1'
  assert.equal(resolvePortalLogoutRedirectPath('https://evil.com/app/login'), fallback)
  assert.equal(resolvePortalLogoutRedirectPath('//evil.com/app/login'), fallback)
  assert.equal(resolvePortalLogoutRedirectPath('/app/dashboard'), fallback)
  assert.equal(resolvePortalLogoutRedirectPath(null), fallback)
})

test('resolvePortalLogoutRedirectUrl produit une URL absolue', () => {
  const url = resolvePortalLogoutRedirectUrl(
    {
      headers: new Headers({ host: 'localhost:3000' }),
      nextUrl: new URL('http://localhost:3000/api/portal/logout'),
    },
    '/app/login?signed_out=1',
  )
  assert.equal(url, 'http://localhost:3000/app/login?signed_out=1')
})
