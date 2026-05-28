import type { BundleWithdrawPayload } from '@/lib/portal/bundleClient'

const KEY_PREFIX = 'portal:bundle-withdraw:'

export type BundleWithdrawSession = {
  portfolioId: string
  batchId: string
  fullWithdraw: boolean
  withdrawAmount: number | null
  withdraw: BundleWithdrawPayload
  savedAt: string
}

export function bundleWithdrawSessionKey(portfolioId: string): string {
  return `${KEY_PREFIX}${portfolioId}`
}

export function saveBundleWithdrawSession(session: BundleWithdrawSession): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(
      bundleWithdrawSessionKey(session.portfolioId),
      JSON.stringify(session),
    )
  } catch {
    /* quota / private mode */
  }
}

export function loadBundleWithdrawSession(portfolioId: string): BundleWithdrawSession | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(bundleWithdrawSessionKey(portfolioId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as BundleWithdrawSession
    if (parsed.portfolioId !== portfolioId || !parsed.batchId || !parsed.withdraw) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function clearBundleWithdrawSession(portfolioId: string): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(bundleWithdrawSessionKey(portfolioId))
  } catch {
    /* ignore */
  }
}
