/** Guard + lecture env pour le sandbox LI.FI local (web BFF, dev uniquement). */

function readLifiSandboxEnabledRaw(): boolean {
  return process.env.LIFI_LOCAL_SANDBOX_ENABLED?.trim().toLowerCase() === 'true'
}

export function assertLifiLocalSandboxProductionGuard(): void {
  if (process.env.NODE_ENV === 'production' && readLifiSandboxEnabledRaw()) {
    throw new Error('LIFI_LOCAL_SANDBOX_ENABLED cannot be true in production')
  }
}

/** Sandbox LI.FI actif côté web (complète le mock backend `LIFI_SWAPS_MOCK` / catalog.mock_mode). */
export function isLifiLocalSandboxEnabled(): boolean {
  assertLifiLocalSandboxProductionGuard()
  return readLifiSandboxEnabledRaw() && process.env.NODE_ENV !== 'production'
}
