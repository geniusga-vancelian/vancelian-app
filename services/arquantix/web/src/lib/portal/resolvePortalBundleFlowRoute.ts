import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import {
  portalBundleInvestRoute,
  portalBundleProductInvestRoute,
  type PortalBundleInvestFrom,
  type PortalVaultFlowMode,
} from '@/lib/portal/portalRouting'

/** Route invest/retrait bundle depuis carte Placer, wallet ou détail panier. */
export function resolvePortalBundleFlowRoute(
  bundle: Pick<PortalCryptoBundle, 'portfolioId' | 'code'>,
  mode: PortalVaultFlowMode = 'invest',
  options?: { from?: PortalBundleInvestFrom },
): string | null {
  const portfolioId = bundle.portfolioId?.trim()
  if (portfolioId) {
    return portalBundleInvestRoute(portfolioId, mode, options)
  }
  const code = bundle.code?.trim()
  if (!code) return null
  return portalBundleProductInvestRoute(code, mode)
}
