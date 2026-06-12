import assert from 'node:assert/strict'
import { test } from 'node:test'

import {
  invalidatePortalCache,
  readPortalCache,
  writePortalCache,
} from '@/lib/portal/portalClientCache'

test('invalidatePortalCache: supprime la clé exacte et ses sous-clés', () => {
  writePortalCache('portal:crypto-wallet', { a: 1 }, 60_000)
  writePortalCache('portal:crypto-wallet:positions:v1:ethereum:none', { a: 2 }, 60_000)
  writePortalCache('portal:crypto-wallet:BTC:core:ethereum:none', { a: 3 }, 60_000)

  invalidatePortalCache('portal:crypto-wallet')

  assert.equal(readPortalCache('portal:crypto-wallet'), null)
  assert.equal(readPortalCache('portal:crypto-wallet:positions:v1:ethereum:none'), null)
  assert.equal(readPortalCache('portal:crypto-wallet:BTC:core:ethereum:none'), null)
})

test('invalidatePortalCache: ne supprime pas un voisin au préfixe partiel', () => {
  writePortalCache('portal:invest:v3', { a: 1 }, 60_000)
  writePortalCache('portal:invest-markets:v1', { a: 2 }, 60_000)

  invalidatePortalCache('portal:invest')

  assert.equal(readPortalCache('portal:invest:v3'), null)
  assert.deepEqual(readPortalCache('portal:invest-markets:v1'), { a: 2 })

  invalidatePortalCache('portal:invest-markets:v1')
})

test('invalidatePortalCache: sans argument vide tout', () => {
  writePortalCache('portal:markets:top:v1', { a: 1 }, 60_000)
  writePortalCache('portal:dashboard:core', { a: 2 }, 60_000)

  invalidatePortalCache()

  assert.equal(readPortalCache('portal:markets:top:v1'), null)
  assert.equal(readPortalCache('portal:dashboard:core'), null)
})
