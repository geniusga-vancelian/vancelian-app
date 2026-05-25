/** Guard + lecture env pour le mock wallet externe local (dev sandbox uniquement). */

import { isLifiLocalSandboxEnabled } from '@/lib/wallet/lifiLocalSandboxConfig'
import { isMorphoLocalSandboxEnabled } from '@/lib/portal/morphoLocalSandboxConfig'

function readMockEnabledRaw(): boolean {
  return process.env.EXTERNAL_WALLET_LOCAL_MOCK_ENABLED?.trim().toLowerCase() === 'true'
}

export function assertExternalWalletLocalMockProductionGuard(): void {
  if (process.env.NODE_ENV === 'production' && readMockEnabledRaw()) {
    throw new Error('EXTERNAL_WALLET_LOCAL_MOCK_ENABLED cannot be true in production')
  }
}

/** Mock wallet externe actif (dev/test + sandbox Morpho ou LI.FI). */
export function isExternalWalletLocalMockEnabled(): boolean {
  assertExternalWalletLocalMockProductionGuard()
  if (process.env.NODE_ENV === 'production') return false
  if (!readMockEnabledRaw()) return false
  return isMorphoLocalSandboxEnabled() || isLifiLocalSandboxEnabled()
}

export function isExternalWalletMockDevRouteAvailable(): boolean {
  if (process.env.NODE_ENV === 'production') return false
  return isExternalWalletLocalMockEnabled()
}
