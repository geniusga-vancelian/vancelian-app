import type { LombardExecutionPhase, LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
function formatLombardBorrowInterestLabel(value: number | null): string {
  if (value == null || !Number.isFinite(value)) return '—'
  const pct = value.toFixed(1).replace('.', ',')
  return `~ ${pct} %/an · variable`
}
import { formatBorrowAmountFr, parseBorrowAmountInput } from '@/lib/portal/lombard/lombardBorrowUi'

export type LombardBorrowRecap = {
  borrowAmount: string
  borrowAmountLabel: string
  guaranteeAmount: string
  collateral: string
  collateralLabel: string
  targetLtvPercent: number
  safetyLabel: string
  interestLabel: string
  marketLabel: string
}

export function buildLombardBorrowRecap(quote: LombardQuoteResult): LombardBorrowRecap {
  const borrowNum = parseBorrowAmountInput(quote.borrowAmount)
  return {
    borrowAmount: quote.borrowAmount,
    borrowAmountLabel: formatBorrowAmountFr(borrowNum, borrowNum % 1 === 0 ? 2 : 2),
    guaranteeAmount: quote.guaranteeAmount,
    collateral: quote.collateral,
    collateralLabel: quote.collateralName,
    targetLtvPercent: quote.targetLtvPercent,
    safetyLabel: quote.safetyLabel,
    interestLabel: formatLombardBorrowInterestLabel(quote.borrowApyPercent),
    marketLabel: `${VANCELIAN_LOMBARD_V1.poweredByLabel.replace('Powered by ', '')} · ${quote.collateral} → USDC`,
  }
}

/** Index du stepper (0–3) ; 4 = les 4 étapes sont terminées. */
export function lombardBorrowStepperIndex(phase: LombardExecutionPhase): number {
  switch (phase) {
    case 'preparing':
    case 'authorizing':
      return 0
    case 'locking':
      return 1
    case 'sending':
      return 2
    case 'confirming':
      return 3
    case 'confirmed':
      return 4
    default:
      return 0
  }
}

export function lombardBorrowStepperState(
  stepIndex: number,
  progressIndex: number,
): 'done' | 'current' | 'pending' {
  if (stepIndex < progressIndex) return 'done'
  if (stepIndex === progressIndex && progressIndex < 4) return 'current'
  return 'pending'
}
