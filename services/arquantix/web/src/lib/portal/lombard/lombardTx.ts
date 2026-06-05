import { DEFAULT_SLIPPAGE_TOLERANCE } from '@morpho-org/blue-sdk'
import { MorphoClient } from '@morpho-org/morpho-sdk'
import type { Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { withLombardAsyncTimeout } from '@/lib/portal/lombard/lombardAsyncTimeout'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { resolveLombardMarket, type ResolvedLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import type { LombardPreparedTx } from '@/lib/portal/lombard/lombardTypes'

const LOMBARD_BUILD_TX_TIMEOUT_MS = 25_000

function mapSdkTx(
  tx: { to: Address; data: `0x${string}`; value?: bigint },
  chainId: number,
  operation: LombardPreparedTx['operation'],
): LombardPreparedTx {
  return {
    to: tx.to,
    data: tx.data,
    value: `0x${(tx.value ?? BigInt(0)).toString(16)}`,
    chainId,
    operation,
  }
}

function isApprovalTx(
  item: unknown,
): item is { to: Address; data: `0x${string}`; value?: bigint } {
  if (!item || typeof item !== 'object') return false
  const row = item as Record<string, unknown>
  if (row.type === 'permit' || row.type === 'permit2' || row.type === 'signature') return false
  return typeof row.to === 'string' && typeof row.data === 'string'
}

function isAuthorizationTx(item: unknown): boolean {
  if (!item || typeof item !== 'object') return false
  const row = item as Record<string, unknown>
  return row.type === 'morphoAuthorization' || row.action === 'morphoAuthorization'
}

export async function buildLombardOpenLoanTransactions(args: {
  collateral: string
  walletAddress: string
  guaranteeAmountRaw: bigint
  borrowAmountRaw: bigint
  resolvedMarket?: ResolvedLombardMarket
}): Promise<LombardPreparedTx[]> {
  return withLombardAsyncTimeout('build_open_loan_transactions', async () => {
    const chainId = VANCELIAN_LOMBARD_V1.chainId
    const resolved = args.resolvedMarket ?? (await resolveLombardMarket({ collateral: args.collateral }))
    const { morphoMarket } = resolved
    const userAddress = args.walletAddress as Address

    const publicClient = createBasePublicClient({ side: 'server' })
    const morpho = new MorphoClient(publicClient, { supportSignature: false })

    const positionData = await morphoMarket.getPositionData(userAddress)
    const marketEntity = morpho.marketV1(resolved.marketParams, chainId)

    const { buildTx, getRequirements } = marketEntity.supplyCollateralBorrow({
      userAddress,
      positionData,
      amount: args.guaranteeAmountRaw,
      borrowAmount: args.borrowAmountRaw,
      slippageTolerance: DEFAULT_SLIPPAGE_TOLERANCE,
    })

    const requirements = await getRequirements()
    const prepared: LombardPreparedTx[] = []

    for (const item of requirements) {
      if (isApprovalTx(item)) {
        prepared.push(mapSdkTx(item, chainId, 'approve'))
      } else if (typeof item === 'object' && item !== null && 'to' in item && 'data' in item) {
        const tx = item as { to: Address; data: `0x${string}`; value?: bigint }
        prepared.push(mapSdkTx(tx, chainId, isAuthorizationTx(item) ? 'authorize' : 'approve'))
      }
    }

    prepared.push(mapSdkTx(buildTx(), chainId, 'open_loan'))
    return prepared
  }, LOMBARD_BUILD_TX_TIMEOUT_MS)
}
