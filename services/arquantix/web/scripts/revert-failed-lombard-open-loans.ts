/**
 * Corrige le ledger Lombard lorsqu'un open_loan a été confirmé à tort (UserOp Privy revertie).
 *
 * Usage (prod via ECS) :
 *   npx tsx scripts/revert-failed-lombard-open-loans.ts --dry-run
 *   npx tsx scripts/revert-failed-lombard-open-loans.ts --apply
 *
 * Cible par défaut : personId + groupKeys des deux derniers emprunts cbBTC du 2026-05-27.
 */
import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'
import { resolvePortalTransactionReceiptStatus } from '@/lib/portal/portalTransactionReceiptStatus'
import { prisma } from '@/lib/prisma'

const DEFAULT_PERSON_ID = '8b0e0044-f1ef-47a5-99d4-370598a77492'
const DEFAULT_GROUP_KEYS = [
  '2d55f862-6312-41c9-aac9-f7327dcdd2de', // 15 USDC — open_loan UserOp failed
  '6646f058-1b0f-4b63-995b-8a6ee1862e13', // 10 USDC — vérification on-chain
]

function readBorrowAmount(metadata: unknown): string | null {
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata)) return null
  const row = metadata as Record<string, unknown>
  const value = row.borrow_amount ?? row.borrowAmount
  return typeof value === 'string' ? value : null
}

async function resolveOnChainStatus(txHash: string | null | undefined): Promise<'success' | 'reverted' | 'missing'> {
  const hash = txHash?.trim()
  if (!hash || !/^0x[0-9a-fA-F]{64}$/.test(hash)) return 'missing'

  const client = createBasePublicClient({ side: 'server' })
  const receipt = await client.getTransactionReceipt({ hash: hash as `0x${string}` }).catch(() => null)
  if (!receipt) return 'missing'
  return resolvePortalTransactionReceiptStatus(receipt)
}

async function main(): Promise<void> {
  const apply = process.argv.includes('--apply')
  const dryRun = !apply || process.argv.includes('--dry-run')
  const personId = process.env.LOMBARD_REVERT_PERSON_ID?.trim() || DEFAULT_PERSON_ID
  const groupKeys =
    process.env.LOMBARD_REVERT_GROUP_KEYS?.split(',').map((value) => value.trim()).filter(Boolean) ??
    DEFAULT_GROUP_KEYS

  console.info(
    JSON.stringify({
      mode: dryRun ? 'dry-run' : 'apply',
      personId,
      groupKeys,
    }),
  )

  for (const groupKey of groupKeys) {
    const rows = await prisma.onchainVaultTransaction.findMany({
      where: {
        personId,
        idempotencyKey: groupKey,
        integrationMode: LOMBARD_INTEGRATION_MODE,
      },
      orderBy: [{ txIndex: 'asc' }, { operation: 'asc' }],
    })

    if (rows.length === 0) {
      console.warn(JSON.stringify({ groupKey, action: 'skip', reason: 'no_ledger_rows' }))
      continue
    }

    const deposit = rows.find((row) => row.operation === 'deposit') ?? null
    if (!deposit) {
      console.warn(JSON.stringify({ groupKey, action: 'skip', reason: 'no_deposit_row' }))
      continue
    }

    const onChainStatus = await resolveOnChainStatus(deposit.txHash)
    const borrowAmount = readBorrowAmount(deposit.metadataJson)

    console.info(
      JSON.stringify({
        groupKey,
        borrowAmount,
        depositId: deposit.id,
        depositStatus: deposit.status,
        txHash: deposit.txHash,
        onChainStatus,
      }),
    )

    if (onChainStatus === 'success') {
      console.info(JSON.stringify({ groupKey, action: 'keep', reason: 'open_loan_succeeded_on_chain' }))
      continue
    }

    if (deposit.status === 'reverted' || deposit.status === 'failed') {
      console.info(JSON.stringify({ groupKey, action: 'keep', reason: 'deposit_already_terminal', status: deposit.status }))
      continue
    }

    const patch = {
      status: 'reverted' as const,
      errorMessage: 'Manual revert — open_loan UserOp failed on-chain (false confirm).',
      metadataJson: {
        ...(deposit.metadataJson && typeof deposit.metadataJson === 'object' && !Array.isArray(deposit.metadataJson)
          ? (deposit.metadataJson as Record<string, unknown>)
          : {}),
        manual_revert_at: new Date().toISOString(),
        manual_revert_reason: 'privy_user_operation_failed',
        manual_revert_on_chain_status: onChainStatus,
      },
    }

    if (dryRun) {
      console.info(JSON.stringify({ groupKey, action: 'would_revert_deposit', depositId: deposit.id, patch }))
      continue
    }

    await prisma.onchainVaultTransaction.update({
      where: { id: deposit.id },
      data: patch,
    })

    console.info(JSON.stringify({ groupKey, action: 'reverted_deposit', depositId: deposit.id }))
  }
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
