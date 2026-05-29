/** Bloque le démarrage prod si un mode sandbox/mock est actif. */

/** Flags DeFi / wallet : toute valeur truthy (true, 1, yes, on) interdit le runtime production. */
export const PRODUCTION_SANDBOX_ENV_FLAGS = [
  'BUNDLE_LIFI_SYNC_MOCK',
  'LIFI_SWAPS_MOCK',
  'LIFI_LOCAL_SANDBOX_ENABLED',
  'MORPHO_LOCAL_SANDBOX_ENABLED',
  'LOMBARD_V1_MOCK_ENABLED',
  'LEDGITY_LOCAL_SANDBOX_ENABLED',
  'EXTERNAL_WALLET_LOCAL_MOCK_ENABLED',
] as const

function isTruthySandboxValue(raw: string | undefined): boolean {
  if (!raw) return false
  const normalized = raw.trim().toLowerCase()
  return normalized === 'true' || normalized === '1' || normalized === 'yes'
}

function isProductionBuildPhase(): boolean {
  return process.env.NEXT_PHASE === 'phase-production-build'
}

export function assertProductionSandboxDisabled(): void {
  if (process.env.NODE_ENV !== 'production') return
  if (isProductionBuildPhase()) return

  const violations = PRODUCTION_SANDBOX_ENV_FLAGS.filter((name) =>
    isTruthySandboxValue(process.env[name]),
  )

  if (violations.length === 0) return

  throw new Error(
    `Production sandbox guard: forbidden env in production — ${violations.join(', ')}. ` +
      'Set all sandbox flags to false before deploy.',
  )
}
