import { afterEach, describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  isPublicBaseRpcPrimary,
  labelBaseRpcUrl,
  PUBLIC_BASE_RPC_LAST_RESORT,
  resolveBaseRpcUrls,
} from './baseRpcProvider'
import { formatBaseRpcUserMessage, isBaseRpcTransientError } from './baseRpcErrors'

const ENV_KEYS = [
  'BASE_RPC_URL_PRIMARY',
  'BASE_RPC_URL_FALLBACK',
  'BASE_RPC_URL',
  'NEXT_PUBLIC_BASE_RPC_URL',
]

function saveEnv(): Record<string, string | undefined> {
  const saved: Record<string, string | undefined> = {}
  for (const key of ENV_KEYS) saved[key] = process.env[key]
  return saved
}

function restoreEnv(saved: Record<string, string | undefined>): void {
  for (const key of ENV_KEYS) {
    if (saved[key] === undefined) delete process.env[key]
    else process.env[key] = saved[key]
  }
}

describe('baseRpcProvider', () => {
  afterEach(() => {
    /* per-test restore */
  })

  it('priorise BASE_RPC_URL_PRIMARY avant le RPC public', () => {
    const saved = saveEnv()
    try {
      process.env.BASE_RPC_URL_PRIMARY = 'https://base-mainnet.g.alchemy.com/v2/test'
      process.env.BASE_RPC_URL_FALLBACK = PUBLIC_BASE_RPC_LAST_RESORT
      const urls = resolveBaseRpcUrls({ side: 'server' })
      assert.equal(urls[0], 'https://base-mainnet.g.alchemy.com/v2/test')
      assert.equal(isPublicBaseRpcPrimary(), false)
    } finally {
      restoreEnv(saved)
    }
  })

  it('n’utilise le RPC public que en dernier recours si primary configuré', () => {
    const saved = saveEnv()
    try {
      process.env.BASE_RPC_URL_PRIMARY = 'https://example.quicknode.com/base'
      const urls = resolveBaseRpcUrls({ side: 'server' })
      assert.equal(urls[0]?.includes('quicknode'), true)
      assert.equal(urls.at(-1), PUBLIC_BASE_RPC_LAST_RESORT)
    } finally {
      restoreEnv(saved)
    }
  })

  it('label RPC sans exposer la clé', () => {
    assert.equal(labelBaseRpcUrl('https://base-mainnet.g.alchemy.com/v2/secret-key'), 'alchemy')
    assert.equal(labelBaseRpcUrl(PUBLIC_BASE_RPC_LAST_RESORT), 'public-base')
  })
})

describe('baseRpcErrors', () => {
  it('détecte rate limit viem', () => {
    assert.equal(
      isBaseRpcTransientError(new Error('RPC Request failed.\n\nDetails: over rate limit')),
      true,
    )
  })

  it('masque l’erreur brute côté utilisateur', () => {
    const msg = formatBaseRpcUserMessage(new Error('RPC Request failed.\n\nURL: https://mainnet.base.org'))
    assert.match(msg, /réseau Base est temporairement occupé/)
    assert.doesNotMatch(msg, /mainnet\.base\.org/)
  })
})
