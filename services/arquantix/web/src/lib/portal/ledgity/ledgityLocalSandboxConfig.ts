/** Guard + lecture env pour le mode sandbox Ledgity local (dev uniquement). */

import {
  assertLedgityLocalSandboxProductionGuard,
  readLedgityLocalSandboxEnabledRaw,
} from '@/lib/portal/ledgity/ledgityConfig'

export { assertLedgityLocalSandboxProductionGuard }

/** Sandbox actif (dev/test uniquement). */
export function isLedgityLocalSandboxEnabled(): boolean {
  assertLedgityLocalSandboxProductionGuard()
  return readLedgityLocalSandboxEnabledRaw() && process.env.NODE_ENV !== 'production'
}

export function getLedgityLocalSandboxYieldBps(): number {
  const raw = process.env.LEDGITY_LOCAL_SANDBOX_YIELD_BPS?.trim()
  const parsed = raw ? Number(raw) : 900
  return Number.isFinite(parsed) && parsed >= 0 ? Math.round(parsed) : 900
}

export function getLedgityLocalSandboxPricePerShare(): number {
  const raw = process.env.LEDGITY_LOCAL_SANDBOX_PPS?.trim()
  const parsed = raw ? Number(raw.replace(',', '.')) : 1.0578
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1.0578
}

export const LEDGITY_LOCAL_SANDBOX_WALLET_ADDRESS =
  process.env.LEDGITY_LOCAL_SANDBOX_WALLET_ADDRESS?.trim().toLowerCase() ||
  '0x00000000000000000000000000000000000102'

export const LEDGITY_LOCAL_SANDBOX_PRIVY_WALLET_ID =
  process.env.LEDGITY_LOCAL_SANDBOX_PRIVY_WALLET_ID?.trim() || 'local_mock_ledgity_wallet'

export const LEDGITY_LOCAL_SANDBOX_PERSON_EMAIL =
  process.env.LEDGITY_LOCAL_SANDBOX_PERSON_EMAIL?.trim() || 'ledgity-sandbox@local.dev'
