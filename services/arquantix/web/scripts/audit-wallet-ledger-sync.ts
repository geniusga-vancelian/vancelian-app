/**
 * Audit ledger Lombard (Prisma) + Privy (Postgres) vs soldes on-chain Base.
 *
 * Usage:
 *   npx tsx scripts/audit-wallet-ledger-sync.ts
 *   PERSON_ID=... WALLET_ADDRESS=0x... npx tsx scripts/audit-wallet-ledger-sync.ts
 */
import { erc20Abi, getAddress } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'
import { resolvePortalTransactionReceiptStatus } from '@/lib/portal/portalTransactionReceiptStatus'
import { prisma } from '@/lib/prisma'

const DEFAULT_PERSON_ID = '8b0e0044-f1ef-47a5-99d4-370598a77492'
const DEFAULT_WALLET = '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44'

const BASE_TOKENS: Record<string, `0x${string}`> = {
  USDC: getAddress('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
  CBETH: getAddress('0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22'),
  CBBTC: getAddress('0xcbB7c0000aB88B473b1f5aFd9ef808440eed33Bf'),
}

type DepositRow = {
  id: string
  asset: string
  amount: string
  direction: string
  status: string
  tx_hash: string
  transaction_kind: string
  idempotency_key: string | null
  created_at: Date
}

function classifyDeposit(row: DepositRow): string {
  const hash = row.tx_hash.toLowerCase()
  if (hash.startsWith('0xsim')) return 'phantom_simulated'
  if (hash.startsWith('0xmock')) return 'mock_swap_ledger'
  if ((row.idempotency_key ?? '').toLowerCase().startsWith('admin_sim_')) return 'phantom_admin_sim'
  if (row.transaction_kind === 'crypto_swap') return 'swap_ledger'
  return 'on_chain_or_webhook'
}

function summarizeDeposits(deposits: DepositRow[]) {
  const net: Record<string, number> = {}
  const byClass: Record<string, Record<string, number>> = {}
  for (const row of deposits) {
    if (row.status !== 'confirmed') continue
    const asset = row.asset.toUpperCase()
    const sign = row.direction === 'credit' ? 1 : -1
    const amt = sign * Number(row.amount)
    net[asset] = (net[asset] ?? 0) + amt
    const cls = classifyDeposit(row)
    byClass[cls] ??= {}
    byClass[cls][asset] = (byClass[cls][asset] ?? 0) + amt
  }
  return { net, byClass }
}

async function readOnChainBalances(wallet: `0x${string}`): Promise<Record<string, number>> {
  const client = createBasePublicClient({ side: 'server' })
  const out: Record<string, number> = {}
  for (const [asset, address] of Object.entries(BASE_TOKENS)) {
    const raw = await client.readContract({
      address,
      abi: erc20Abi,
      functionName: 'balanceOf',
      args: [wallet],
    })
    const decimals = asset === 'USDC' ? 6 : asset === 'CBBTC' ? 8 : 18
    out[asset] = Number(raw) / 10 ** decimals
  }
  return out
}

async function main(): Promise<void> {
  const personId = process.env.PERSON_ID?.trim() || DEFAULT_PERSON_ID
  const wallet = getAddress(process.env.WALLET_ADDRESS?.trim() || DEFAULT_WALLET)

  const lombardRows = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId,
      walletAddress: wallet.toLowerCase(),
      integrationMode: LOMBARD_INTEGRATION_MODE,
      operation: 'deposit',
    },
    orderBy: { createdAt: 'asc' },
  })

  const client = createBasePublicClient({ side: 'server' })
  const lombardAudit = []
  for (const row of lombardRows) {
    let onChain: 'success' | 'reverted' | 'missing' = 'missing'
    if (row.txHash && /^0x[0-9a-fA-F]{64}$/.test(row.txHash)) {
      const receipt = await client.getTransactionReceipt({ hash: row.txHash as `0x${string}` }).catch(() => null)
      onChain = receipt ? resolvePortalTransactionReceiptStatus(receipt) : 'missing'
    }
    lombardAudit.push({
      groupKey: row.idempotencyKey,
      depositId: row.id,
      ledgerStatus: row.status,
      txHash: row.txHash,
      onChainStatus: onChain,
      amountRaw: row.amountRaw,
      mismatch: row.status === 'success' && onChain !== 'success',
    })
  }

  const deposits = await prisma.$queryRawUnsafe<DepositRow[]>(`
    SELECT id, asset, amount::text AS amount, direction, status, tx_hash, transaction_kind,
           idempotency_key, created_at
    FROM person_wallet_deposits
    WHERE person_id = '${personId}'::uuid
    ORDER BY created_at DESC
    LIMIT 200
  `)

  const balances = await prisma.$queryRawUnsafe<
    { asset: string; balance: string; available_balance: string }[]
  >(`
    SELECT asset, balance::text AS balance, available_balance::text AS available_balance
    FROM person_wallet_balances
    WHERE person_id = '${personId}'::uuid
  `)

  const swaps = await prisma.$queryRawUnsafe<
    { id: string; status: string; from_asset: string; to_asset: string; amount_in: string; tx_hash: string | null }[]
  >(`
    SELECT id, status, from_asset, to_asset, amount_in::text AS amount_in, tx_hash
    FROM person_wallet_swaps
    WHERE person_id = '${personId}'::uuid
    ORDER BY created_at DESC
    LIMIT 50
  `).catch(() => [])

  const onChain = await readOnChainBalances(wallet)
  const depositSummary = summarizeDeposits(deposits)

  const ledgerUsdc = balances
    .filter((row) => row.asset.toUpperCase() === 'USDC')
    .reduce((sum, row) => sum + Number(row.balance), 0)

  const untrustedDeposits = deposits.filter(
    (row) =>
      row.status === 'confirmed' &&
      (classifyDeposit(row).startsWith('phantom') || classifyDeposit(row) === 'mock_swap_ledger'),
  )

  console.info(
    JSON.stringify(
      {
        personId,
        wallet,
        onChainBalances: onChain,
        ledgerBalances: balances,
        ledgerUsdcTotal: ledgerUsdc,
        usdcDeltaLedgerMinusOnChain: ledgerUsdc - (onChain.USDC ?? 0),
        depositLedgerNet: depositSummary.net,
        depositLedgerByClass: depositSummary.byClass,
        repairPlan: {
          lombardRowsToRevert: lombardAudit.filter((row) => row.mismatch).length,
          untrustedDepositsToVoid: untrustedDeposits.length,
          expectedUsdcAfterFullUntrustedVoid:
            ledgerUsdc +
            Math.abs(depositSummary.byClass.mock_swap_ledger?.USDC ?? 0) -
            (depositSummary.byClass.phantom_simulated?.USDC ?? 0),
        },
        lombardOpenLoans: lombardAudit,
        lombardFalseSuccess: lombardAudit.filter((row) => row.mismatch),
        phantomDeposits: untrustedDeposits.map((row) => ({
          ...row,
          classification: classifyDeposit(row),
        })),
        recentDeposits: deposits.slice(0, 15).map((row) => ({
          ...row,
          classification: classifyDeposit(row),
        })),
        recentSwaps: swaps,
      },
      null,
      2,
    ),
  )
}

main()
  .catch((error) => {
    console.error(error)
    process.exit(1)
  })
  .finally(async () => {
    await prisma.$disconnect()
  })
