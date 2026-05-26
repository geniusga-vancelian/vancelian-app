import type { BundleInvestPayload } from '@/lib/portal/bundleClient'

const KEY_PREFIX = 'portal:bundle-invest:'

export type BundleInvestSession = {
  portfolioId: string
  batchId: string
  fundingAsset: string
  fundingAmount: number
  invest: BundleInvestPayload
  savedAt: string
}

export function bundleInvestSessionKey(portfolioId: string): string {
  return `${KEY_PREFIX}${portfolioId}`
}

export function saveBundleInvestSession(session: BundleInvestSession): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(
      bundleInvestSessionKey(session.portfolioId),
      JSON.stringify(session),
    )
  } catch {
    /* quota / private mode */
  }
}

export function loadBundleInvestSession(portfolioId: string): BundleInvestSession | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(bundleInvestSessionKey(portfolioId))
    if (!raw) return null
    const parsed = JSON.parse(raw) as BundleInvestSession
    if (parsed.portfolioId !== portfolioId || !parsed.batchId || !parsed.invest) {
      return null
    }
    return parsed
  } catch {
    return null
  }
}

export function clearBundleInvestSession(portfolioId: string): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.removeItem(bundleInvestSessionKey(portfolioId))
  } catch {
    /* ignore */
  }
}
