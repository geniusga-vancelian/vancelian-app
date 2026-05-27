import { buildBackendUrl } from '@/lib/backend'
import { getAnonymousBackendAdminId, signInternalBackendJwtAu } from '@/lib/backend-jwt'
import { LOMBARD_INTEGRATION_MODE, VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { rawToLombardHumanAmount } from '@/lib/portal/lombard/lombardFormat'
import { logLombardOpsEvent } from '@/lib/portal/lombard/lombardOpsLog'
import { isLombardMockEnabled } from '@/lib/portal/lombard/lombardMockConfig'
import { prisma } from '@/lib/prisma'

const USDC_DECIMALS = 6

async function callPrivySimulateDeposit(args: {
  personId: string
  walletAddress: string
  amount: string
}): Promise<{ txHash?: string; depositId?: string }> {
  const token = signInternalBackendJwtAu(getAnonymousBackendAdminId(), '15m')
  const res = await fetch(buildBackendUrl('/api/admin/privy-wallet/simulate-deposit'), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
      'X-Actor-Type': 'service',
      'X-Actor-Id': 'lombard-mock-v1',
      'X-Actor-Roles': 'admin',
    },
    body: JSON.stringify({
      person_id: args.personId,
      wallet_address: args.walletAddress,
      asset: 'USDC',
      amount: args.amount,
      chain_id: VANCELIAN_LOMBARD_V1.chainId,
    }),
    cache: 'no-store',
    signal: AbortSignal.timeout(20_000),
  })

  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const message =
      typeof data === 'object' && data && 'detail' in data
        ? String((data as { detail?: unknown }).detail)
        : typeof data === 'object' && data && 'message' in data
          ? String((data as { message?: unknown }).message)
          : `HTTP ${res.status}`
    throw new Error(message)
  }

  const txHash =
    typeof data === 'object' && data && 'tx_hash' in data
      ? String((data as { tx_hash?: unknown }).tx_hash ?? '').trim()
      : ''
  const depositId =
    typeof data === 'object' && data && 'deposit_id' in data
      ? String((data as { deposit_id?: unknown }).deposit_id ?? '').trim()
      : ''

  return { txHash: txHash || undefined, depositId: depositId || undefined }
}

export async function creditLombardMockBorrowToPrivyLedger(args: {
  personId: string
  groupKey: string
}): Promise<boolean> {
  if (!isLombardMockEnabled()) return false

  const rows = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      idempotencyKey: args.groupKey,
      integrationMode: LOMBARD_INTEGRATION_MODE,
      operation: 'deposit',
      status: 'success',
    },
  })
  const primary = rows[0]
  if (!primary) return false

  const meta =
    primary.metadataJson && typeof primary.metadataJson === 'object' && !Array.isArray(primary.metadataJson)
      ? (primary.metadataJson as Record<string, unknown>)
      : {}

  if (meta.mock_usdc_ledger_credited === true) {
    return false
  }

  const borrowRaw = BigInt(String(primary.amountRaw || meta.borrow_amount_raw || '0'))
  if (borrowRaw <= BigInt(0)) return false

  const amount = rawToLombardHumanAmount(borrowRaw, USDC_DECIMALS, 6)

  const credited = await callPrivySimulateDeposit({
    personId: args.personId,
    walletAddress: primary.walletAddress,
    amount,
  })

  for (const row of rows) {
    const currentMeta =
      row.metadataJson && typeof row.metadataJson === 'object' && !Array.isArray(row.metadataJson)
        ? (row.metadataJson as Record<string, unknown>)
        : {}
    await prisma.onchainVaultTransaction.update({
      where: { id: row.id },
      data: {
        metadataJson: {
          ...currentMeta,
          mock_usdc_ledger_credited: true,
          mock_usdc_ledger_credited_at: new Date().toISOString(),
          ...(credited.txHash ? { mock_usdc_privy_tx_hash: credited.txHash } : {}),
          ...(credited.depositId ? { mock_usdc_privy_deposit_id: credited.depositId } : {}),
        },
      },
    })
  }

  logLombardOpsEvent({
    code: 'lombard.mock_usdc_ledger_credited',
    level: 'info',
    message: 'Mock Lombard USDC credited to Privy wallet ledger.',
    personId: args.personId,
    walletAddress: primary.walletAddress,
    groupKey: args.groupKey,
    metadata: { amount, chainId: VANCELIAN_LOMBARD_V1.chainId },
  })

  return true
}

/** Backfill idempotent pour les emprunts mock confirmés avant crédit ledger Privy. */
export async function ensureLombardMockPrivyLedgerCredits(args: {
  personId: string
  walletAddress: string
}): Promise<void> {
  if (!isLombardMockEnabled()) return

  const deposits = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId: args.personId,
      walletAddress: args.walletAddress.toLowerCase(),
      integrationMode: LOMBARD_INTEGRATION_MODE,
      operation: 'deposit',
      status: 'success',
    },
    orderBy: { createdAt: 'asc' },
  })

  for (const row of deposits) {
    const meta =
      row.metadataJson && typeof row.metadataJson === 'object' && !Array.isArray(row.metadataJson)
        ? (row.metadataJson as Record<string, unknown>)
        : {}
    if (meta.lombard_mock !== true || meta.mock_usdc_ledger_credited === true) continue
    await creditLombardMockBorrowToPrivyLedger({
      personId: args.personId,
      groupKey: row.idempotencyKey,
    })
  }
}
