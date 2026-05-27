import { LOMBARD_WAD, VANCELIAN_LOMBARD_V1 } from '@/lib/portal/lombard/lombardConfig'
import { lombardSliderLabel, LOAN_HEALTH_STATUS } from '@/lib/portal/lombard/lombardHealth'

export const LOMBARD_MAX_USER_LTV_PERCENT = Math.round(VANCELIAN_LOMBARD_V1.maxUserLtv * 100)

export function clampLombardTargetLtvPercent(value: number): number {
  if (!Number.isFinite(value)) return 0
  return Math.min(LOMBARD_MAX_USER_LTV_PERCENT, Math.max(0, Math.round(value)))
}

export function lombardTargetLtvPercentToWad(ltvPercent: number): bigint {
  const clamped = clampLombardTargetLtvPercent(ltvPercent)
  if (clamped <= 0) return BigInt(0)
  return (BigInt(clamped) * LOMBARD_WAD) / BigInt(100)
}

export function lombardTargetLtvRatio(ltvPercent: number): number {
  return clampLombardTargetLtvPercent(ltvPercent) / 100
}

/** Plafond empruntable si toute la garantie wallet est déposée au LTV cible. */
export function maxBorrowAmountHumanAtTargetLtv(args: {
  absoluteMaxBorrowHuman: string
  targetLtvPercent: number
}): string {
  const maxAtCap = Number(String(args.absoluteMaxBorrowHuman).replace(',', '.'))
  const target = clampLombardTargetLtvPercent(args.targetLtvPercent)
  if (!Number.isFinite(maxAtCap) || maxAtCap <= 0 || target <= 0) return '0'
  const amount = (maxAtCap * target) / LOMBARD_MAX_USER_LTV_PERCENT
  return trimBorrowAmountDisplay(amount)
}

function trimBorrowAmountDisplay(value: number): string {
  if (!Number.isFinite(value) || value <= 0) return '0'
  if (value >= 100) return String(Math.round(value))
  if (value >= 1) {
    const rounded = Math.round(value * 100) / 100
    return String(rounded).replace(/\.?0+$/, '')
  }
  const rounded = Math.round(value * 1_000_000) / 1_000_000
  return String(rounded).replace(/\.?0+$/, '')
}

export type LombardLtvRiskTone = 'safe' | 'balanced' | 'risky' | 'idle'

export function resolveLombardLtvRiskTone(ltvPercent: number): LombardLtvRiskTone {
  if (ltvPercent <= 0) return 'idle'
  const ratio = ltvPercent / 100
  if (ratio <= LOAN_HEALTH_STATUS.comfortable.maxLtv) return 'safe'
  if (ratio <= LOAN_HEALTH_STATUS.monitor.maxLtv) return 'balanced'
  return 'risky'
}

export function lombardLtvRiskLabelFr(ltvPercent: number): string {
  const tone = resolveLombardLtvRiskTone(ltvPercent)
  if (tone === 'idle') return 'Choisissez votre LTV'
  if (tone === 'safe') return 'Prudent'
  if (tone === 'balanced') return 'Équilibré'
  return 'Élevé'
}

export function lombardLtvRiskMessageFr(ltvPercent: number): string {
  const tone = resolveLombardLtvRiskTone(ltvPercent)
  if (tone === 'idle') {
    return 'Déplacez le curseur pour fixer votre niveau de risque. Seule la garantie nécessaire sera déposée sur Morpho.'
  }
  if (tone === 'safe') {
    return 'LTV basse : vous déposez plus de garantie par USDC emprunté, avec une marge confortable avant liquidation.'
  }
  if (tone === 'balanced') {
    return 'Bon compromis : moins de garantie verrouillée qu’en mode prudent, tout en gardant une marge raisonnable.'
  }
  return 'LTV proche du plafond (70 %) : vous déposez le minimum de garantie — une baisse de marché peut déclencher une liquidation.'
}

export function lombardLtvSliderHintFr(ltvPercent: number): string {
  if (ltvPercent <= 0) return lombardSliderLabel(0)
  return lombardSliderLabel(ltvPercent / 100)
}

export function lombardLtvTrackGradient(): string {
  return 'linear-gradient(90deg, rgb(34 197 94 / 0.35) 0%, rgb(34 197 94 / 0.35) 50%, rgb(245 158 11 / 0.45) 50%, rgb(245 158 11 / 0.45) 71.4%, rgb(239 68 68 / 0.5) 71.4%, rgb(239 68 68 / 0.5) 100%)'
}
