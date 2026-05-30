/** Guard + lecture env pour le mode sandbox Morpho local (dev uniquement). */

import { isPortalPrivyOtpDevMockEnabled } from '@/lib/portal/privyOtpDevMockConfig'

function readSandboxEnabledRaw(): boolean {
  return process.env.MORPHO_LOCAL_SANDBOX_ENABLED?.trim().toLowerCase() === 'true'
}

export function assertMorphoLocalSandboxProductionGuard(): void {
  if (process.env.NODE_ENV === 'production' && readSandboxEnabledRaw()) {
    throw new Error('MORPHO_LOCAL_SANDBOX_ENABLED cannot be true in production')
  }
}

/** Sandbox actif (dev/test uniquement). */
export function isMorphoLocalSandboxEnabled(): boolean {
  assertMorphoLocalSandboxProductionGuard()
  if (process.env.NODE_ENV === 'production') return false
  if (readSandboxEnabledRaw()) return true
  // Stack dev OTP mock (111111) : pas de session SDK Privy → ledger sandbox sans signature client.
  return isPortalPrivyOtpDevMockEnabled()
}

export function getMorphoLocalSandboxYieldBps(): number {
  const raw = process.env.MORPHO_LOCAL_SANDBOX_YIELD_BPS?.trim()
  const parsed = raw ? Number(raw) : 450
  return Number.isFinite(parsed) && parsed >= 0 ? Math.round(parsed) : 450
}

export const MORPHO_LOCAL_SANDBOX_WALLET_ADDRESS =
  process.env.MORPHO_LOCAL_SANDBOX_WALLET_ADDRESS?.trim().toLowerCase() ||
  '0x00000000000000000000000000000000000101'

export const MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID =
  process.env.MORPHO_LOCAL_SANDBOX_PRIVY_WALLET_ID?.trim() || 'local_mock_privy_wallet'

export const MORPHO_LOCAL_SANDBOX_PERSON_EMAIL =
  process.env.MORPHO_LOCAL_SANDBOX_PERSON_EMAIL?.trim() || 'morpho-sandbox@local.dev'
