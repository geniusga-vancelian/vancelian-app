/**
 * Validation des variables Lombard requises en production.
 * Appelée au démarrage Node (instrumentation) quand NODE_ENV=production.
 */

import { getPrivyAppIdServer } from '@/lib/portal/privyConfig'
import { isLombardV1Enabled } from '@/lib/portal/lombard/lombardConfig'
import { readLombardMockEnabledRaw } from '@/lib/portal/lombard/lombardMockConfig'

export type LombardProdEnvCheck = {
  name: string
  ok: boolean
  detail: string
  required: boolean
}

function isSet(name: string): boolean {
  const value = process.env[name]?.trim()
  return Boolean(value)
}

function hasBaseRpcConfigured(): boolean {
  return (
    isSet('BASE_RPC_URL_PRIMARY') ||
    isSet('BASE_RPC_URL') ||
    isSet('NEXT_PUBLIC_BASE_RPC_URL')
  )
}

function hasPrivyConfigured(): boolean {
  return Boolean(getPrivyAppIdServer()) && isSet('PRIVY_APP_SECRET')
}

function hasWalletConnectConfigured(): boolean {
  return isSet('NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID')
}

export function collectLombardProdEnvChecks(options?: {
  lombardEnabled?: boolean
}): LombardProdEnvCheck[] {
  const lombardEnabled = options?.lombardEnabled ?? isLombardV1Enabled()
  const checks: LombardProdEnvCheck[] = []

  checks.push({
    name: 'LOMBARD_V1_MOCK_ENABLED',
    ok: !readLombardMockEnabledRaw(),
    detail: readLombardMockEnabledRaw()
      ? 'must be false/unset in production'
      : 'mock disabled',
    required: true,
  })

  if (!lombardEnabled) {
    checks.push({
      name: 'LOMBARD_V1_ENABLED',
      ok: true,
      detail: 'Lombard disabled — skipping beta/RPC/Privy Lombard-specific requirements',
      required: false,
    })
    return checks
  }

  const requiredWhenEnabled = [
    'LOMBARD_V1_ENABLED',
    'LOMBARD_V1_BETA_ENABLED',
    'LOMBARD_V1_BETA_LIMITS_ENABLED',
    'LOMBARD_V1_BETA_MAX_BORROW_USDC_PER_WALLET',
    'LOMBARD_V1_BETA_MAX_TOTAL_BORROW_USDC_GLOBAL',
  ] as const

  for (const name of requiredWhenEnabled) {
    checks.push({
      name,
      ok: isSet(name),
      detail: isSet(name) ? 'set' : 'missing',
      required: true,
    })
  }

  checks.push({
    name: 'LOMBARD_V1_BETA_ALLOWED_WALLETS',
    ok: true,
    detail: isSet('LOMBARD_V1_BETA_ALLOWED_WALLETS')
      ? 'allowlist configured'
      : 'unset — all wallets allowed (beta caps still apply)',
    required: false,
  })

  checks.push({
    name: 'BASE_RPC_URL',
    ok: hasBaseRpcConfigured(),
    detail: hasBaseRpcConfigured()
      ? 'BASE_RPC_URL_PRIMARY / BASE_RPC_URL / NEXT_PUBLIC_BASE_RPC_URL configured'
      : 'missing Base RPC URL',
    required: true,
  })

  checks.push({
    name: 'MORPHO_GRAPHQL_URL',
    ok: true,
    detail: isSet('MORPHO_GRAPHQL_URL')
      ? 'custom MORPHO_GRAPHQL_URL set'
      : 'using default https://api.morpho.org/graphql',
    required: false,
  })

  checks.push({
    name: 'PRIVY_APP_ID',
    ok: hasPrivyConfigured(),
    detail: hasPrivyConfigured()
      ? 'PRIVY_APP_ID/NEXT_PUBLIC_PRIVY_APP_ID + PRIVY_APP_SECRET configured'
      : 'missing Privy app id or secret',
    required: true,
  })

  checks.push({
    name: 'NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID',
    ok: hasWalletConnectConfigured(),
    detail: hasWalletConnectConfigured()
      ? 'set (required for external wallet borrow path)'
      : 'missing — external wallet signing unavailable',
    required: true,
  })

  return checks
}

export function validateLombardProductionEnv(options?: {
  lombardEnabled?: boolean
  throwOnFailure?: boolean
}): { ok: boolean; checks: LombardProdEnvCheck[]; missing: string[] } {
  const checks = collectLombardProdEnvChecks(options)
  const missing = checks.filter((row) => row.required && !row.ok).map((row) => row.name)
  const ok = missing.length === 0

  if (!ok && options?.throwOnFailure) {
    throw new Error(
      `[lombard:prod-env] Missing or invalid production env: ${missing.join(', ')}`,
    )
  }

  return { ok, checks, missing }
}

export function logLombardProductionEnvValidation(): void {
  if (process.env.NODE_ENV !== 'production') return
  const result = validateLombardProductionEnv({ throwOnFailure: false })
  if (result.ok) {
    console.info('[lombard:prod-env] production env validation passed')
    return
  }
  console.error(
    '[lombard:prod-env] CRITICAL missing/invalid env:',
    JSON.stringify({ missing: result.missing, checks: result.checks.filter((row) => !row.ok) }),
  )
}
