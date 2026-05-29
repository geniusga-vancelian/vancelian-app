import {
  lombardLtvRiskLabelFr,
  lombardLtvRiskMessageFr,
  resolveLombardLtvRiskTone,
  type LombardLtvRiskTone,
} from '@/lib/portal/lombard/lombardBorrowLtv'

export type LombardBorrowZoneStyle = {
  id: LombardLtvRiskTone
  title: string
  blurb: string
  color: string
  bg: string
}

const ZONE_STYLES: Record<Exclude<LombardLtvRiskTone, 'idle'>, LombardBorrowZoneStyle> = {
  safe: {
    id: 'safe',
    title: 'Prudent',
    blurb:
      'Marge confortable. Votre garantie peut chuter fortement avant la moindre liquidation.',
    color: 'var(--v-green)',
    bg: 'var(--v-success-bg)',
  },
  balanced: {
    id: 'balanced',
    title: 'Équilibré',
    blurb:
      'Compromis entre capital emprunté et marge. Le seuil reste raisonnable, surveillez les variations du marché.',
    color: 'var(--v-yellow-pressed)',
    bg: 'var(--v-warning-bg)',
  },
  risky: {
    id: 'risky',
    title: 'Élevé',
    blurb:
      'Capital maximisé, marge réduite. Une baisse rapide peut déclencher une liquidation. Pour profils qui suivent leur position activement.',
    color: 'var(--v-error)',
    bg: 'var(--v-error-bg)',
  },
}

export function lombardBorrowZoneFor(ltvPercent: number): LombardBorrowZoneStyle {
  const tone = resolveLombardLtvRiskTone(ltvPercent)
  if (tone === 'idle') return ZONE_STYLES.safe
  return {
    ...ZONE_STYLES[tone],
    title: lombardLtvRiskLabelFr(ltvPercent),
    blurb: lombardLtvRiskMessageFr(ltvPercent),
  }
}

export function parseBorrowAmountInput(value: string): number {
  if (typeof value !== 'string') return Number(value) || 0
  const cleaned = value.replace(/[\s\u00A0\u202F]/g, '').replace(',', '.').replace(/[^\d.]/g, '')
  const n = parseFloat(cleaned)
  return Number.isFinite(n) ? n : 0
}

/** Montant USDC normalisé pour query/API (`3440`, pas `3 440`). */
export function formatLombardBorrowAmountForApi(n: number): string {
  if (!Number.isFinite(n) || n <= 0) return ''
  const rounded = Math.round(n * 1_000_000) / 1_000_000
  return rounded.toFixed(6).replace(/\.?0+$/, '')
}

export function normalizeLombardBorrowAmountForApi(input: string): string | null {
  const amount = formatLombardBorrowAmountForApi(parseBorrowAmountInput(input))
  return amount || null
}

/** Estimation affichée si le devis Morpho est en attente ou en erreur (handoff borrow-flow). */
export function estimateLombardGuaranteeDisplay(args: {
  borrowAmountUsd: number
  targetLtvPercent: number
  collateral: string
  collateralPriceUsd: number | null
}): { guaranteeAmount: string; collateral: string } | null {
  const { borrowAmountUsd, targetLtvPercent, collateral, collateralPriceUsd } = args
  if (!(borrowAmountUsd > 0) || !(targetLtvPercent > 0) || collateralPriceUsd == null || collateralPriceUsd <= 0) {
    return null
  }
  const collateralNeededUsdc = borrowAmountUsd / (targetLtvPercent / 100)
  const units = collateralNeededUsdc / collateralPriceUsd
  const maxFraction = collateral === 'cbBTC' ? 8 : 6
  const fractionDigits = units < 1 ? maxFraction : Math.min(4, maxFraction)
  return {
    guaranteeAmount: formatBorrowAmountFr(units, fractionDigits),
    collateral,
  }
}

export function formatBorrowAmountFr(value: number, fractionDigits = 0): string {
  if (!Number.isFinite(value)) return '0'
  return value.toLocaleString('fr-FR', {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  })
}

export function lombardBorrowLiquidationDisplay(args: {
  targetLtvPercent: number
  liquidationLltvPercent: number | null
  collateralPriceUsd: number | null
}): { dropPercent: number; priceUsdc: number | null } {
  const lltv = args.liquidationLltvPercent ?? 77
  if (lltv <= 0) return { dropPercent: 0, priceUsdc: null }
  const dropPercent = Math.max(0, (1 - args.targetLtvPercent / lltv) * 100)
  const priceUsdc =
    args.collateralPriceUsd != null && args.collateralPriceUsd > 0
      ? args.collateralPriceUsd * (args.targetLtvPercent / lltv)
      : null
  return { dropPercent, priceUsdc }
}

export const BORROW_INTRO_STORAGE_KEY = 'vncl:borrowIntroSeen'

export function readBorrowIntroSeen(): boolean {
  if (typeof window === 'undefined') return false
  try {
    return window.localStorage.getItem(BORROW_INTRO_STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export function markBorrowIntroSeen(): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(BORROW_INTRO_STORAGE_KEY, '1')
  } catch {
    /* ignore */
  }
}
