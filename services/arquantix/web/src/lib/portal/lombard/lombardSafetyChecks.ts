import { LOAN_HEALTH_STATUS } from '@/lib/portal/lombard/lombardHealth'
import {
  assertLombardBaseChain,
  assertLombardBetaAccess,
  assertLombardBetaBorrowLimits,
  assertLombardCollateralBalanceCoversGuarantee,
} from '@/lib/portal/lombard/lombardBetaLimits'
import { LombardSafetyError } from '@/lib/portal/lombard/lombardBetaErrors'
import { logLombardSupportEvent } from '@/lib/portal/lombard/lombardSupportLog'
import { buildLombardQuote, LombardQuoteError } from '@/lib/portal/lombard/lombardQuote'
import type { LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'
import { VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'

export type LombardSafetyWarning = {
  code: 'lombard.high_ltv_warning'
  message: string
  projectedLtvPercent: number
}

export type LombardPreparedBorrowSafety = LombardQuoteResult & {
  warnings: LombardSafetyWarning[]
}

function buildHighLtvWarning(projectedLtvPercent: number): LombardSafetyWarning | null {
  const ratio = projectedLtvPercent / 100
  if (ratio <= LOAN_HEALTH_STATUS.monitor.maxLtv) return null
  if (ratio > VANCELIAN_LOMBARD_V1.maxUserLtv) return null
  return {
    code: 'lombard.high_ltv_warning',
    message:
      'Your safety level is getting closer to the maximum. Consider borrowing a smaller amount.',
    projectedLtvPercent,
  }
}

export async function runLombardPreBorrowSafetyChecks(args: {
  personId: string
  collateral: string
  borrowAmount: string
  walletAddress: string
  targetLtvPercent: number
  chainId?: number
}): Promise<LombardPreparedBorrowSafety> {
  assertLombardBaseChain(args.chainId)

  await assertLombardBetaAccess({ walletAddress: args.walletAddress })

  let quote: LombardQuoteResult
  try {
    quote = await buildLombardQuote({
      collateral: args.collateral,
      borrowAmount: args.borrowAmount,
      walletAddress: args.walletAddress,
      targetLtvPercent: args.targetLtvPercent,
    })
  } catch (error) {
    if (error instanceof LombardQuoteError) throw error
    throw error
  }

  if (quote.projectedLtvPercent > VANCELIAN_LOMBARD_V1.maxUserLtv * 100 + 1e-9) {
    throw new LombardSafetyError(
      'lombard.ltv_cap_exceeded',
      'Borrow amount exceeds the 70% safety cap.',
      400,
    )
  }

  const borrowAmountRaw = BigInt(quote.borrowAmountRaw)
  await assertLombardBetaBorrowLimits({
    personId: args.personId,
    walletAddress: args.walletAddress,
    newBorrowAmountRaw: borrowAmountRaw,
  })

  await assertLombardCollateralBalanceCoversGuarantee({
    collateral: args.collateral,
    walletAddress: args.walletAddress,
    guaranteeAmountRaw: BigInt(quote.guaranteeAmountRaw),
  })

  const warnings: LombardSafetyWarning[] = []
  const warning = buildHighLtvWarning(quote.projectedLtvPercent)
  if (warning) {
    warnings.push(warning)
    logLombardSupportEvent({
      code: 'lombard.pre_borrow_warning',
      level: 'info',
      message: warning.message,
      personId: args.personId,
      walletAddress: args.walletAddress,
      marketId: quote.marketId,
      metadata: { projectedLtvPercent: quote.projectedLtvPercent },
    })
  }

  return { ...quote, warnings }
}

export { buildHighLtvWarning }
