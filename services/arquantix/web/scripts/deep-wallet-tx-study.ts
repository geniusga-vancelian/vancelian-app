/**
 * Étude transactionnelle profonde — ledger vs on-chain.
 * Usage: npx tsx scripts/deep-wallet-tx-study.ts
 */
import { erc20Abi, formatUnits, getAddress, type Hash } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { LOMBARD_INTEGRATION_MODE } from '@/lib/portal/lombard/lombardConfig'
import { resolvePortalTransactionReceiptStatus } from '@/lib/portal/portalTransactionReceiptStatus'
import { prisma } from '@/lib/prisma'

const PERSON_ID = process.env.PERSON_ID?.trim() || '8b0e0044-f1ef-47a5-99d4-370598a77492'
const WALLET = getAddress(process.env.WALLET_ADDRESS?.trim() || '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44')

const BASE_TOKENS: Record<string, { address: `0x${string}`; decimals: number }> = {
  USDC: { address: getAddress('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'), decimals: 6 },
  CBETH: { address: getAddress('0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22'), decimals: 18 },
  CBBTC: { address: getAddress('0xcbB7c0000aB88B473b1f5aFd9ef808440eed33Bf'), decimals: 8 },
}

type Verdict = 'KEEP_REAL' | 'REVERT_PHANTOM' | 'REVERT_MOCK' | 'REVERT_LOMBARD_FALSE_SUCCESS' | 'INVESTIGATE'

function classifyTxHash(txHash: string | null | undefined): Verdict {
  const h = (txHash ?? '').toLowerCase()
  if (!h) return 'INVESTIGATE'
  if (h.startsWith('0xsim')) return 'REVERT_PHANTOM'
  if (h.startsWith('0xmock')) return 'REVERT_MOCK'
  if (/^0x[0-9a-f]{64}$/.test(h)) return 'KEEP_REAL'
  return 'INVESTIGATE'
}

async function verifyOnChain(hash: string): Promise<'success' | 'reverted' | 'missing' | 'not_applicable'> {
  const cls = classifyTxHash(hash)
  if (cls === 'REVERT_PHANTOM' || cls === 'REVERT_MOCK') return 'not_applicable'
  if (!/^0x[0-9a-fA-F]{64}$/.test(hash)) return 'missing'
  await sleep(RPC_DELAY_MS)
  const client = createBasePublicClient({ side: 'server' })
  const receipt = await client.getTransactionReceipt({ hash: hash as Hash }).catch(() => null)
  if (!receipt) return 'missing'
  return resolvePortalTransactionReceiptStatus(receipt)
}

const RPC_DELAY_MS = 400

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function readOnChainBalances(): Promise<Record<string, number>> {
  const client = createBasePublicClient({ side: 'server' })
  const out: Record<string, number> = {}
  for (const [asset, meta] of Object.entries(BASE_TOKENS)) {
    await sleep(RPC_DELAY_MS)
    try {
      const raw = await client.readContract({
        address: meta.address,
        abi: erc20Abi,
        functionName: 'balanceOf',
        args: [WALLET],
      })
      out[asset] = Number(formatUnits(raw, meta.decimals))
    } catch {
      out[asset] = NaN
    }
  }
  return out
}

async function main(): Promise<void> {
  const onChain = await readOnChainBalances()

  const deposits = await prisma.$queryRawUnsafe<
    {
      id: string
      asset: string
      amount: string
      direction: string
      status: string
      tx_hash: string
      transaction_kind: string
      idempotency_key: string | null
      created_at: Date
    }[]
  >(`
    SELECT id, asset, amount::text AS amount, direction, status, tx_hash, transaction_kind,
           idempotency_key, created_at
    FROM person_wallet_deposits
    WHERE person_id = '${PERSON_ID}'::uuid
    ORDER BY created_at ASC
  `)

  const depositStudy = []
  for (const row of deposits) {
    const verdict = classifyTxHash(row.tx_hash)
    const onChainStatus = row.status === 'confirmed' ? await verifyOnChain(row.tx_hash) : 'not_applicable'
    depositStudy.push({
      id: row.id,
      createdAt: row.created_at,
      asset: row.asset,
      direction: row.direction,
      amount: row.amount,
      status: row.status,
      txHash: row.tx_hash,
      kind: row.transaction_kind,
      verdict: row.status !== 'confirmed' ? 'KEEP_REAL' : verdict,
      onChainStatus,
      action: row.status !== 'confirmed' ? 'none' : verdict.startsWith('REVERT') ? 'void' : 'keep',
    })
  }

  const swaps = await prisma.$queryRawUnsafe<
    {
      id: string
      status: string
      from_asset: string
      to_asset: string
      amount_in: string
      tx_hash: string | null
      created_at: Date
      updated_at: Date
    }[]
  >(`
    SELECT id, status, from_asset, to_asset, amount_in::text AS amount_in,
           tx_hash, created_at, updated_at
    FROM person_wallet_swaps
    WHERE person_id = '${PERSON_ID}'::uuid
    ORDER BY created_at ASC
  `)

  const swapStudy = []
  for (const row of swaps) {
    const verdict = classifyTxHash(row.tx_hash)
    const onChainStatus =
      row.status === 'CONFIRMED' && row.tx_hash ? await verifyOnChain(row.tx_hash) : 'not_applicable'
    swapStudy.push({
      id: row.id,
      createdAt: row.created_at,
      status: row.status,
      pair: `${row.from_asset}→${row.to_asset}`,
      amountIn: row.amount_in,
      txHash: row.tx_hash,
      verdict: row.status !== 'CONFIRMED' ? 'KEEP_REAL' : verdict,
      onChainStatus,
      action:
        row.status === 'CONFIRMED' && (verdict === 'REVERT_MOCK' || onChainStatus === 'missing')
          ? 'mark_investigate'
          : row.status === 'CONFIRMED' && onChainStatus === 'success'
            ? 'keep'
            : 'none',
    })
  }

  const lombardRows = await prisma.onchainVaultTransaction.findMany({
    where: {
      personId: PERSON_ID,
      walletAddress: WALLET.toLowerCase(),
      integrationMode: LOMBARD_INTEGRATION_MODE,
    },
    orderBy: { createdAt: 'asc' },
  })

  const lombardStudy = []
  for (const row of lombardRows) {
    const onChainStatus = row.txHash ? await verifyOnChain(row.txHash) : 'missing'
    const falseSuccess = row.status === 'success' && onChainStatus !== 'success'
    lombardStudy.push({
      id: row.id,
      createdAt: row.createdAt,
      operation: row.operation,
      status: row.status,
      groupKey: row.idempotencyKey,
      txHash: row.txHash,
      amountRaw: row.amountRaw,
      borrowUsdc: row.amountRaw ? Number(row.amountRaw) / 1e6 : null,
      onChainStatus,
      verdict: falseSuccess ? 'REVERT_LOMBARD_FALSE_SUCCESS' : onChainStatus === 'success' ? 'KEEP_REAL' : 'INVESTIGATE',
      action: falseSuccess ? 'revert_to_reverted' : 'keep',
      metadataMock: row.metadataJson,
    })
  }

  const balances = await prisma.$queryRawUnsafe<{ asset: string; balance: string }[]>(`
    SELECT asset, balance::text AS balance
    FROM person_wallet_balances
    WHERE person_id = '${PERSON_ID}'::uuid
  `)

  const toVoid = depositStudy.filter((r) => r.action === 'void')
  const lombardRevert = lombardStudy.filter((r) => r.action === 'revert_to_reverted')

  console.info(
    JSON.stringify(
      {
        personId: PERSON_ID,
        wallet: WALLET,
        onChainBalances: onChain,
        ledgerBalances: balances,
        summary: {
          depositsTotal: deposits.length,
          depositsConfirmed: deposits.filter((d) => d.status === 'confirmed').length,
          toVoidCount: toVoid.length,
          lombardRevertCount: lombardRevert.length,
          swapsTotal: swaps.length,
          swapsConfirmedMock: swapStudy.filter((s) => s.verdict === 'REVERT_MOCK').length,
          swapsConfirmedReal: swapStudy.filter((s) => s.verdict === 'KEEP_REAL' && s.status === 'CONFIRMED').length,
          usdcLedger: balances.find((b) => b.asset === 'USDC')?.balance,
          usdcOnChain: onChain.USDC,
          usdcGap: Number(balances.find((b) => b.asset === 'USDC')?.balance ?? 0) - onChain.USDC,
        },
        lombardStudy,
        depositStudy,
        swapStudy,
        repairActions: {
          voidDeposits: toVoid.map((r) => ({
            id: r.id,
            asset: r.asset,
            direction: r.direction,
            amount: r.amount,
            txHash: r.txHash,
            verdict: r.verdict,
          })),
          revertLombard: lombardRevert.map((r) => ({
            id: r.id,
            groupKey: r.groupKey,
            borrowUsdc: r.borrowUsdc,
            txHash: r.txHash,
          })),
        },
      },
      null,
      2,
    ),
  )
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(() => prisma.$disconnect())
