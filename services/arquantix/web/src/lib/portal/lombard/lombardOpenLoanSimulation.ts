import type { Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import type { LombardPreparedTx } from '@/lib/portal/lombard/lombardTypes'

export class LombardSimulationError extends Error {
  readonly httpStatus = 400
  readonly code = 'lombard.open_loan_simulation_failed'

  constructor(
    message: string,
    readonly revertReason?: string,
  ) {
    super(message)
    this.name = 'LombardSimulationError'
  }
}

export function formatLombardSimulationUserMessage(revertReason: string | null | undefined): string {
  const lower = (revertReason ?? '').toLowerCase()

  if (
    lower.includes('insufficient') ||
    lower.includes('collateral') ||
    lower.includes('liquidity')
  ) {
    return 'La marge ou la garantie disponible est insuffisante pour cet emprunt. Réduisez le montant ou réessayez dans quelques instants.'
  }

  if (lower.includes('ltv') || lower.includes('borrow') || lower.includes('cap')) {
    return 'Le montant dépasse ce que le marché accepte actuellement. Réduisez l’emprunt ou ajustez le niveau de risque.'
  }

  return 'Le réseau refuse cette ouverture d’emprunt pour l’instant. Vous pouvez réessayer — le marché peut accepter la transaction quelques secondes plus tard.'
}

function extractRevertReason(error: unknown): string | null {
  if (!error || typeof error !== 'object') return null
  const row = error as { shortMessage?: string; message?: string; details?: string }
  const raw = row.shortMessage ?? row.message ?? row.details
  if (typeof raw !== 'string' || !raw.trim()) return null
  return raw.trim().slice(0, 500)
}

/** eth_call open_loan — bloque avant signature si Morpho revert. */
export async function assertLombardOpenLoanSimulates(args: {
  walletAddress: string
  transactions: LombardPreparedTx[]
}): Promise<void> {
  const openLoan = args.transactions.find((tx) => tx.operation === 'open_loan')
  if (!openLoan) return

  const client = createBasePublicClient({ side: 'server' })

  try {
    await client.call({
      account: args.walletAddress as Address,
      to: openLoan.to as Address,
      data: openLoan.data as `0x${string}`,
      value: BigInt(openLoan.value || '0x0'),
    })
  } catch (error) {
    const revertReason = extractRevertReason(error)
    throw new LombardSimulationError(
      formatLombardSimulationUserMessage(revertReason),
      revertReason ?? undefined,
    )
  }
}
