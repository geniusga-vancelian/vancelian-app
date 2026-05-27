import type { LombardSafetyLevel } from '@/lib/portal/lombard/lombardTypes'

export const LOAN_HEALTH_STATUS = {
  comfortable: {
    maxLtv: 0.5,
    label: 'Comfortable',
    message: 'Your position has a strong safety margin.',
  },
  monitor: {
    maxLtv: 0.6,
    label: 'To monitor',
    message: 'Your position is still healthy, but keep eye on market movements.',
  },
  risky: {
    maxLtv: 0.7,
    label: 'High risk',
    message: 'Consider repaying part of your loan or adding more guarantee.',
  },
  blocked: {
    minLtv: 0.7,
    label: 'Action required',
    message: 'You cannot borrow more. Reduce your risk first.',
  },
} as const

export const LTV_ZONES = {
  safe: '0% - 50%',
  balanced: '50% - 60%',
  high: '60% - 70%',
  blocked: '>70%',
} as const

export function resolveLombardSafetyLevel(ltvRatio: number): LombardSafetyLevel {
  if (!Number.isFinite(ltvRatio) || ltvRatio < 0) return 'comfortable'
  if (ltvRatio > LOAN_HEALTH_STATUS.blocked.minLtv) return 'blocked'
  if (ltvRatio > LOAN_HEALTH_STATUS.monitor.maxLtv) return 'risky'
  if (ltvRatio > LOAN_HEALTH_STATUS.comfortable.maxLtv) return 'monitor'
  return 'comfortable'
}

export function lombardSafetyDetails(ltvRatio: number): {
  level: LombardSafetyLevel
  label: string
  message: string
} {
  const level = resolveLombardSafetyLevel(ltvRatio)
  const row = LOAN_HEALTH_STATUS[level === 'blocked' ? 'blocked' : level]
  return {
    level,
    label: row.label,
    message: row.message,
  }
}

export function lombardSliderLabel(ltvRatio: number): 'Safe' | 'Balanced' | 'Risky' {
  if (ltvRatio <= LOAN_HEALTH_STATUS.comfortable.maxLtv) return 'Safe'
  if (ltvRatio <= LOAN_HEALTH_STATUS.monitor.maxLtv) return 'Balanced'
  return 'Risky'
}

export function assertLombardUserLtvWithinCap(ltvRatio: number, maxUserLtv: number): void {
  if (!Number.isFinite(ltvRatio) || ltvRatio <= 0) return
  if (ltvRatio > maxUserLtv + 1e-9) {
    throw new Error('Borrow amount exceeds the maximum safety level (70%).')
  }
}
