/** Bloque le démarrage prod si un mode sandbox/mock est actif. */

const SANDBOX_FLAGS: Array<{ name: string; forbiddenValue?: string }> = [
  { name: 'MORPHO_LOCAL_SANDBOX_ENABLED', forbiddenValue: 'true' },
  { name: 'LEDGITY_LOCAL_SANDBOX_ENABLED', forbiddenValue: 'true' },
  { name: 'EXTERNAL_WALLET_LOCAL_MOCK_ENABLED', forbiddenValue: 'true' },
  { name: 'LIFI_LOCAL_SANDBOX_ENABLED', forbiddenValue: 'true' },
  { name: 'LIFI_SWAPS_MOCK', forbiddenValue: 'true' },
  { name: 'LOMBARD_V1_MOCK_ENABLED', forbiddenValue: 'true' },
]

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

  const violations = SANDBOX_FLAGS.filter(({ name, forbiddenValue }) => {
    const raw = process.env[name]
    if (forbiddenValue) {
      return raw?.trim().toLowerCase() === forbiddenValue
    }
    return isTruthySandboxValue(raw)
  }).map(({ name }) => name)

  if (violations.length === 0) return

  throw new Error(
    `Production sandbox guard: forbidden env in production — ${violations.join(', ')}. ` +
      'Set all sandbox flags to false before deploy.',
  )
}
