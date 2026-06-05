import {
  normalizeVaultAddress,
  VANCELIAN_AXBALI_VAULT,
  VANCELIAN_AXDUBAI_VAULT,
} from '@/lib/portal/ledgity/ledgityConstants'

/** Profil comportemental du vault ERC-4626 (CDC Vancelian v0.3). */
export type LedgityVaultProfile = 'flexible' | 'exclusive_offer_locked'

/** Mode de retrait exposé au portail / admin. */
export type LedgityVaultWithdrawMode = 'instant' | 'async_request' | 'blocked'

const EXCLUSIVE_OFFER_LOCKED_VAULTS = new Set([
  normalizeVaultAddress(VANCELIAN_AXDUBAI_VAULT),
  normalizeVaultAddress(VANCELIAN_AXBALI_VAULT),
])

export function resolveLedgityVaultProfile(vaultAddress: string): LedgityVaultProfile {
  return EXCLUSIVE_OFFER_LOCKED_VAULTS.has(normalizeVaultAddress(vaultAddress))
    ? 'exclusive_offer_locked'
    : 'flexible'
}

export function isExclusiveOfferLockedVault(vaultAddress: string): boolean {
  return resolveLedgityVaultProfile(vaultAddress) === 'exclusive_offer_locked'
}

export function resolveLedgityVaultWithdrawMode(args: {
  profile: LedgityVaultProfile
  operationEndDateUnix: bigint | null
  nowUnix?: bigint
}): LedgityVaultWithdrawMode {
  const now = args.nowUnix ?? BigInt(Math.floor(Date.now() / 1000))
  const end = args.operationEndDateUnix

  if (args.profile === 'exclusive_offer_locked') {
    // Club deal : vesting jusqu'à maturité (operationEndDate) — pas de sortie pendant le lock.
    if (end == null || end <= BigInt(0) || now < end) return 'blocked'
    return 'async_request'
  }

  return 'instant'
}

export function isLedgityVaultLockActive(args: {
  profile: LedgityVaultProfile
  operationEndDateUnix: bigint | null
  nowUnix?: bigint
}): boolean {
  return resolveLedgityVaultWithdrawMode(args) === 'blocked'
}

export function formatLedgityLockStatusLabel(args: {
  profile: LedgityVaultProfile
  lockActive: boolean
  operationEndAt: string | null
}): string {
  if (args.profile !== 'exclusive_offer_locked') return 'Coffre flexible'
  if (args.lockActive) {
    if (args.operationEndAt) {
      return `Offre exclusive — lock-up actif jusqu'au ${args.operationEndAt}`
    }
    return 'Offre exclusive — période de lock-up (club deal) en cours'
  }
  return 'Offre exclusive — maturité atteinte, retrait asynchrone disponible'
}
