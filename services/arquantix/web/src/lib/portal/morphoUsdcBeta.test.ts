import assert from 'node:assert/strict'
import { afterEach, describe, it } from 'node:test'

import {
  getMorphoUsdcBetaLimits,
  getMorphoUsdcBetaPersonIds,
  isMorphoUsdcBetaAllowAllUsers,
  isMorphoUsdcBetaEnabled,
  isMorphoUsdcDepositsDisabled,
} from './morphoUsdcBetaConfig'

const ENV_KEYS = [
  'MORPHO_USDC_BETA_ENABLED',
  'MORPHO_USDC_DEPOSITS_DISABLED',
  'MORPHO_USDC_BETA_MIN_DEPOSIT_USDC',
  'MORPHO_USDC_BETA_MAX_DEPOSIT_USDC',
  'MORPHO_USDC_BETA_PERSON_IDS',
  'MORPHO_USDC_BETA_ALLOW_ALL_USERS',
  'MORPHO_USDC_MAX_GLOBAL_EXPOSURE_RAW',
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

describe('morphoUsdcBetaConfig', () => {
  afterEach(() => {
    /* restored per test */
  })

  it('lit les flags beta et kill switch depuis env', () => {
    const saved = saveEnv()
    try {
      process.env.MORPHO_USDC_BETA_ENABLED = 'true'
      process.env.MORPHO_USDC_DEPOSITS_DISABLED = '1'
      assert.equal(isMorphoUsdcBetaEnabled(), true)
      assert.equal(isMorphoUsdcDepositsDisabled(), true)
    } finally {
      restoreEnv(saved)
    }
  })

  it('parse les person ids allowlist', () => {
    const saved = saveEnv()
    try {
      process.env.MORPHO_USDC_BETA_PERSON_IDS = 'abc-123, def-456'
      const ids = getMorphoUsdcBetaPersonIds()
      assert.equal(ids.has('abc-123'), true)
      assert.equal(ids.has('def-456'), true)
    } finally {
      restoreEnv(saved)
    }
  })

  it('expose les plafonds beta par défaut en raw USDC (6 dec)', () => {
    const saved = saveEnv()
    try {
      for (const key of ENV_KEYS) delete process.env[key]
      const limits = getMorphoUsdcBetaLimits()
      assert.equal(limits.minDepositRaw, BigInt(10_000_000))
      assert.equal(limits.maxDepositRaw, BigInt(100_000_000))
      assert.equal(limits.maxUserExposureRaw, BigInt(500_000_000))
      assert.equal(limits.maxGlobalExposureRaw, BigInt(10_000_000_000))
    } finally {
      restoreEnv(saved)
    }
  })

  it('autorise tous les utilisateurs quand ALLOW_ALL_USERS=true', () => {
    const saved = saveEnv()
    try {
      process.env.MORPHO_USDC_BETA_ALLOW_ALL_USERS = 'true'
      assert.equal(isMorphoUsdcBetaAllowAllUsers(), true)
    } finally {
      restoreEnv(saved)
    }
  })

  it('lit les plafonds depuis les env RAW', () => {
    const saved = saveEnv()
    try {
      for (const key of ENV_KEYS) delete process.env[key]
      process.env.MORPHO_USDC_MAX_GLOBAL_EXPOSURE_RAW = '10000000000'
      const limits = getMorphoUsdcBetaLimits()
      assert.equal(limits.maxGlobalExposureRaw, BigInt(10_000_000_000))
    } finally {
      restoreEnv(saved)
    }
  })
})
