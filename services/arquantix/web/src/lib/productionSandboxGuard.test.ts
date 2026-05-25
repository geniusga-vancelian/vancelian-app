import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { assertProductionSandboxDisabled } from '@/lib/productionSandboxGuard'

describe('productionSandboxGuard', () => {
  it('ignore en dev', () => {
    const prev = process.env.NODE_ENV
    process.env.NODE_ENV = 'development'
    process.env.MORPHO_LOCAL_SANDBOX_ENABLED = 'true'
    try {
      assertProductionSandboxDisabled()
    } finally {
      process.env.NODE_ENV = prev
      delete process.env.MORPHO_LOCAL_SANDBOX_ENABLED
    }
  })

  it('bloque morpho sandbox en production', () => {
    const prevNode = process.env.NODE_ENV
    const prevMorpho = process.env.MORPHO_LOCAL_SANDBOX_ENABLED
    process.env.NODE_ENV = 'production'
    process.env.MORPHO_LOCAL_SANDBOX_ENABLED = 'true'
    try {
      assert.throws(() => assertProductionSandboxDisabled(), /MORPHO_LOCAL_SANDBOX_ENABLED/)
    } finally {
      process.env.NODE_ENV = prevNode
      if (prevMorpho === undefined) delete process.env.MORPHO_LOCAL_SANDBOX_ENABLED
      else process.env.MORPHO_LOCAL_SANDBOX_ENABLED = prevMorpho
    }
  })

  it('accepte production sans sandbox', () => {
    const prevNode = process.env.NODE_ENV
    process.env.NODE_ENV = 'production'
    delete process.env.MORPHO_LOCAL_SANDBOX_ENABLED
    delete process.env.EXTERNAL_WALLET_LOCAL_MOCK_ENABLED
    delete process.env.LIFI_LOCAL_SANDBOX_ENABLED
    delete process.env.LIFI_SWAPS_MOCK
    try {
      assertProductionSandboxDisabled()
    } finally {
      process.env.NODE_ENV = prevNode
    }
  })
})
