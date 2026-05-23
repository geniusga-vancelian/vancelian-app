import test from 'node:test'
import assert from 'node:assert/strict'
import {
  portalLogoutRedirectPathFallback,
  resolvePortalLogoutRedirectPath,
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
