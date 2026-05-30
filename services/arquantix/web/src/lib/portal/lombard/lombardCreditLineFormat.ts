import { formatBorrowAmountFr } from '@/lib/portal/lombard/lombardBorrowUi'
import type { LombardActivePosition } from '@/lib/portal/lombard/lombardPositionTypes'
import { totalBorrowedUsdc } from '@/lib/portal/lombard/lombardWalletBalanceOverlay'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

export function formatCreditLineBalanceLabel(totalUsdc: number): string {
  if (!(totalUsdc > 0)) return '0\u00a0USDC'
  return `${formatBorrowAmountFr(totalUsdc, 6)}\u00a0USDC`
}

export function resolveCreditLineSubtitle(loanCount: number): string {
  if (loanCount <= 0) return 'Liquidity advances · Morpho'
  return `${loanCount} loan${loanCount === 1 ? '' : 's'} · Morpho`
}

export function resolveCreditLineHref(_positions: LombardActivePosition[]): string {
  return PORTAL_ROUTES.creditLine
}

export function resolveCreditLineFromPositions(positions: LombardActivePosition[]) {
  const totalBorrowed = totalBorrowedUsdc(positions)
  return {
    totalBorrowedUsdc: totalBorrowed,
    loanCount: positions.length,
    balanceLabel: formatCreditLineBalanceLabel(totalBorrowed),
    subtitle: resolveCreditLineSubtitle(positions.length),
    href: resolveCreditLineHref(positions),
    visible: totalBorrowed > 0,
  }
}
