import type { AppLoanSafety } from '@/components/design-system/app/AppLoanCard'
import { bundledCryptoSvgPublicPath } from '@/lib/portal/cryptoInstrumentAssets'
import { formatBorrowAmountFr } from '@/lib/portal/lombard/lombardBorrowUi'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import type { LombardSafetyLevel } from '@/lib/portal/lombard/lombardTypes'
import { totalBorrowedUsdc } from '@/lib/portal/lombard/lombardWalletBalanceOverlay'

const LOAN_ALERT_THRESHOLD_PERCENT = 80

function parseHumanAmount(value: string): number {
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : 0
}

export function formatLombardUsdcAmountLabel(value: number, fractionDigits = 6): string {
  return `${formatBorrowAmountFr(value, fractionDigits)}\u00a0USDC`
}

export function mapLombardHealthToLoanSafety(status: LombardSafetyLevel): AppLoanSafety {
  if (status === 'comfortable') return 'ok'
  if (status === 'monitor') return 'warn'
  return 'error'
}

export function resolveLombardHealthLabelFr(status: LombardSafetyLevel, fallback: string): string {
  if (status === 'comfortable') return 'Position saine'
  if (status === 'monitor') return 'À surveiller'
  if (status === 'risky') return 'Risque élevé'
  if (status === 'blocked') return 'Action requise'
  return fallback
}

export function resolveLombardCollateralIconUrl(symbol: string): string | undefined {
  const ticker = symbol.replace(/^cb/i, '')
  return bundledCryptoSvgPublicPath(ticker) ?? undefined
}

export function formatLombardCollateralSubtitle(position: LombardActivePosition): string {
  const amount = formatBorrowAmountFr(parseHumanAmount(position.collateralAmount), 6)
  return `${amount} ${position.collateralSymbol} en garantie`
}

export function resolveLombardUsagePercent(position: LombardActivePosition): number | undefined {
  if (position.currentLtvPercent == null) return undefined
  return Math.round(position.currentLtvPercent)
}

export function estimateLombardMonthlyInterestUsdc(positions: LombardActivePosition[]): number {
  return positions.reduce((sum, position) => {
    const borrow = parseHumanAmount(position.borrowAmount)
    const apy = position.borrowApyPercent ?? 0
    if (!(borrow > 0) || !(apy > 0)) return sum
    return sum + (borrow * apy) / 100 / 12
  }, 0)
}

export function resolveCreditLineSummary(positions: LombardActivePosition[]) {
  const totalBorrowed = totalBorrowedUsdc(positions)
  const monthlyInterest = estimateLombardMonthlyInterestUsdc(positions)

  return {
    totalBorrowedUsdc: totalBorrowed,
    totalBorrowedLabel: formatLombardUsdcAmountLabel(totalBorrowed),
    monthlyInterestLabel: formatLombardUsdcAmountLabel(monthlyInterest, 3),
    loanCount: positions.filter((p) => parseHumanAmount(p.borrowAmount) > 0).length,
    alertThresholdPercent: LOAN_ALERT_THRESHOLD_PERCENT,
  }
}

export function resolveLombardLoanAlertPercent(): number {
  return LOAN_ALERT_THRESHOLD_PERCENT
}
