/**
 * Réparation ledger : Lombard false confirm + crédits Privy simulate (via admin API).
 *
 * Usage:
 *   npx tsx scripts/repair-wallet-ledger-sync.ts --dry-run
 *   npx tsx scripts/repair-wallet-ledger-sync.ts --apply --lombard-only
 *   npx tsx scripts/repair-wallet-ledger-sync.ts --apply
 *
 * Pour les void ledger (mock + simulate), préférer l'API Python locale (direction debit corrigée) :
 *   python scripts/run_privy_wallet_reconciliation.py --person-id <uuid> --void-phantoms --apply
 */
import { buildBackendUrl } from '@/lib/backend'
import { getAnonymousBackendAdminId, signInternalBackendJwtAu } from '@/lib/backend-jwt'
import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'
import { resolvePortalTransactionReceiptStatus } from '@/lib/portal/portalTransactionReceiptStatus'
import { prisma } from '@/lib/prisma'

const DEFAULT_PERSON_ID = '8b0e0044-f1ef-47a5-99d4-370598a77492'

type DepositRow = {
  id: string
  asset: string
  amount: string
  tx_hash: string
  status: string
  direction: string
}

async function voidPrivyDeposit(args: {
  personId: string
  depositId: string
  reason: string
}): Promise<void> {
  const token = signInternalBackendJwtAu(getAnonymousBackendAdminId(), '15m')
  const res = await fetch(buildBackendUrl('/api/admin/privy-wallet/void-deposit'), {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      Accept: 'application/json',
      'X-Actor-Type': 'service',
      'X-Actor-Id': 'wallet-ledger-repair',
      'X-Actor-Roles': 'admin',
    },
    body: JSON.stringify({
      person_id: args.personId,
      deposit_id: args.depositId,
      reason: args.reason,
    }),
    cache: 'no-store',
    signal: AbortSignal.timeout(20_000),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(typeof data === 'object' && data && 'message' in data ? String(data.message) : `HTTP ${res.status}`)
  }
}

async function main(): Promise<void> {
  const apply = process.argv.includes('--apply')
  const dryRun = !apply || process.argv.includes('--dry-run')
  const lombardOnly = process.argv.includes('--lombard-only')
  const personId = process.env.PERSON_ID?.trim() || DEFAULT_PERSON_ID

  const client = createBasePublicClient({ side: 'server' })
  const lombardDeposits = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId,
      integrationMode: LOMBARD_INTEGRATION_MODE,
      status: 'success',
    },
    orderBy: { createdAt: 'asc' },
  })

  for (const row of lombardDeposits) {
    const hash = row.txHash?.trim()
    if (!hash || !/^0x[0-9a-fA-F]{64}$/.test(hash)) continue
    const receipt = await client.getTransactionReceipt({ hash: hash as `0x${string}` }).catch(() => null)
    const onChain = receipt ? resolvePortalTransactionReceiptStatus(receipt) : 'missing'
    if (onChain === 'success') {
      console.info(JSON.stringify({ action: 'keep', groupKey: row.idempotencyKey, onChain }))
      continue
    }

    const patch = {
      status: 'reverted' as const,
      errorMessage: 'Repair — open_loan UserOp failed on-chain (false confirm).',
    }
    if (dryRun) {
      console.info(JSON.stringify({ action: 'would_revert_lombard', depositId: row.id, groupKey: row.idempotencyKey, onChain }))
      continue
    }

    await prisma.onchainVaultTransaction.update({
      where: { id: row.id },
      data: {
        ...patch,
        metadataJson: {
          ...(row.metadataJson && typeof row.metadataJson === 'object' && !Array.isArray(row.metadataJson)
            ? (row.metadataJson as Record<string, unknown>)
            : {}),
          manual_revert_at: new Date().toISOString(),
          manual_revert_reason: 'wallet_ledger_repair',
          manual_revert_on_chain_status: onChain,
        },
      },
    })
    console.info(JSON.stringify({ action: 'reverted_lombard', depositId: row.id, groupKey: row.idempotencyKey, operation: row.operation }))
  }

  if (lombardOnly) {
    console.info(JSON.stringify({ mode: dryRun ? 'dry-run' : 'apply', scope: 'lombard-only', personId, done: true }))
    return
  }

  const phantomDeposits = await prisma.$queryRawUnsafe<DepositRow[]>(`
    SELECT id, asset, amount::text AS amount, tx_hash, status, direction
    FROM person_wallet_deposits
    WHERE person_id = '${personId}'::uuid
      AND status = 'confirmed'
      AND (
        tx_hash LIKE '0xsim%'
        OR idempotency_key LIKE 'admin_sim_%'
        OR tx_hash LIKE '0xmock%'
      )
    ORDER BY CASE WHEN direction = 'debit' THEN 0 ELSE 1 END, created_at ASC
  `)

  for (const row of phantomDeposits) {
    if (dryRun) {
      console.info(JSON.stringify({ action: 'would_void_phantom', depositId: row.id, asset: row.asset, amount: row.amount, txHash: row.tx_hash }))
      continue
    }
    await voidPrivyDeposit({
      personId,
      depositId: row.id,
      reason: 'Wallet ledger repair — simulated Privy deposit without on-chain proof',
    })
    console.info(JSON.stringify({ action: 'voided_phantom', depositId: row.id, asset: row.asset, amount: row.amount }))
  }

  console.info(JSON.stringify({ mode: dryRun ? 'dry-run' : 'apply', personId, done: true }))
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
