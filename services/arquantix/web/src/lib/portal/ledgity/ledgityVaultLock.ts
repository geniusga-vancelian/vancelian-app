import type { Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { LEDGITY_CHAIN_ID, normalizeVaultAddress } from '@/lib/portal/ledgity/ledgityConstants'
import { LEDGITY_VAULT_LOCK_ABI } from '@/lib/portal/ledgity/ledgityVaultExtendedAbi'
import { LedgityVaultLockError } from '@/lib/portal/ledgity/ledgityVaultLockErrors'
import {
  formatLedgityLockStatusLabel,
  isLedgityVaultLockActive,
  resolveLedgityVaultProfile,
  resolveLedgityVaultWithdrawMode,
  type LedgityVaultProfile,
  type LedgityVaultWithdrawMode,
} from '@/lib/portal/ledgity/ledgityVaultProfiles'
import { isLedgityLocalSandboxEnabled } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import { getSandboxMockVaultCatalog } from '@/lib/portal/ledgity/mocks/ledgityLocalSandbox'

export type LedgityVaultLockState = {
  vaultAddress: string
  profile: LedgityVaultProfile
  operationEndDateUnix: string | null
  operationEndAt: string | null
  lockActive: boolean
  withdrawMode: LedgityVaultWithdrawMode
  withdrawalRequestsEnabled: boolean | null
  lockStatusLabel: string
}

function unixToIso(unix: bigint): string | null {
  if (unix <= BigInt(0)) return null
  const ms = Number(unix) * 1000
  if (!Number.isFinite(ms) || ms <= 0) return null
  return new Date(ms).toISOString()
}

function sandboxLockState(vaultAddress: string): LedgityVaultLockState | null {
  const mock = getSandboxMockVaultCatalog(vaultAddress)
  if (!mock?.lockState) return null
  const profile = resolveLedgityVaultProfile(vaultAddress)
  const operationEndDateUnix = mock.lockState.operationEndDateUnix ?? null
  const endBig =
    operationEndDateUnix != null && operationEndDateUnix !== ''
      ? BigInt(operationEndDateUnix)
      : null
  const lockActive = isLedgityVaultLockActive({ profile, operationEndDateUnix: endBig })
  const operationEndAt = endBig != null ? unixToIso(endBig) : null
  return {
    vaultAddress: normalizeVaultAddress(vaultAddress),
    profile,
    operationEndDateUnix: endBig != null ? endBig.toString() : null,
    operationEndAt,
    lockActive,
    withdrawMode: resolveLedgityVaultWithdrawMode({ profile, operationEndDateUnix: endBig }),
    withdrawalRequestsEnabled: mock.lockState.withdrawalRequestsEnabled ?? true,
    lockStatusLabel: formatLedgityLockStatusLabel({ profile, lockActive, operationEndAt }),
  }
}

/** Lit l'état lock-up / maturité on-chain (ou sandbox). */
export async function readLedgityVaultLockState(args: {
  vaultAddress: string
  chainId?: number
}): Promise<LedgityVaultLockState> {
  const vaultAddress = normalizeVaultAddress(args.vaultAddress)
  const profile = resolveLedgityVaultProfile(vaultAddress)

  if (isLedgityLocalSandboxEnabled()) {
    return (
      sandboxLockState(vaultAddress) ?? {
        vaultAddress,
        profile,
        operationEndDateUnix: null,
        operationEndAt: null,
        lockActive: profile === 'exclusive_offer_locked',
        withdrawMode: resolveLedgityVaultWithdrawMode({ profile, operationEndDateUnix: null }),
        withdrawalRequestsEnabled: true,
        lockStatusLabel: formatLedgityLockStatusLabel({
          profile,
          lockActive: profile === 'exclusive_offer_locked',
          operationEndAt: null,
        }),
      }
    )
  }

  const chainId = args.chainId ?? LEDGITY_CHAIN_ID
  if (chainId !== LEDGITY_CHAIN_ID) {
    return {
      vaultAddress,
      profile,
      operationEndDateUnix: null,
      operationEndAt: null,
      lockActive: false,
      withdrawMode: 'instant',
      withdrawalRequestsEnabled: null,
      lockStatusLabel: formatLedgityLockStatusLabel({
        profile,
        lockActive: false,
        operationEndAt: null,
      }),
    }
  }

  let operationEndDateUnix: bigint | null = null
  let withdrawalRequestsEnabled: boolean | null = null

  try {
    const client = createBasePublicClient({ side: 'server' })
    const address = vaultAddress as Address
    const [endDate, requestsEnabled] = await Promise.all([
      client.readContract({
        address,
        abi: LEDGITY_VAULT_LOCK_ABI,
        functionName: 'operationEndDate',
      }) as Promise<bigint>,
      client.readContract({
        address,
        abi: LEDGITY_VAULT_LOCK_ABI,
        functionName: 'withdrawalRequestsEnabled',
      }) as Promise<boolean>,
    ])
    operationEndDateUnix = endDate
    withdrawalRequestsEnabled = requestsEnabled
  } catch (error) {
    console.error('[ledgityVaultLock] read on-chain lock state failed', { vaultAddress, error })
  }

  const lockActive = isLedgityVaultLockActive({ profile, operationEndDateUnix })
  const operationEndAt = operationEndDateUnix != null ? unixToIso(operationEndDateUnix) : null

  return {
    vaultAddress,
    profile,
    operationEndDateUnix:
      operationEndDateUnix != null && operationEndDateUnix > BigInt(0)
        ? operationEndDateUnix.toString()
        : null,
    operationEndAt,
    lockActive,
    withdrawMode: resolveLedgityVaultWithdrawMode({ profile, operationEndDateUnix }),
    withdrawalRequestsEnabled,
    lockStatusLabel: formatLedgityLockStatusLabel({ profile, lockActive, operationEndAt }),
  }
}

export async function assertLedgityWithdrawNotLocked(args: {
  vaultAddress: string
  chainId?: number
}): Promise<LedgityVaultLockState> {
  const state = await readLedgityVaultLockState(args)
  if (state.withdrawMode === 'blocked') {
    throw new LedgityVaultLockError(state.lockStatusLabel)
  }
  return state
}

/** Champs sérialisables pour snapshots catalogue / admin. */
export function ledgityLockStateToSnapshotFields(
  state: LedgityVaultLockState,
): Record<string, unknown> {
  return {
    vault_profile: state.profile,
    lock_active: state.lockActive,
    operation_end_at: state.operationEndAt,
    operation_end_date_unix: state.operationEndDateUnix,
    withdraw_mode: state.withdrawMode,
    withdrawal_requests_enabled: state.withdrawalRequestsEnabled,
    lock_status_label: state.lockStatusLabel,
  }
}
