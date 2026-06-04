'use client'

import { PortalBundleInvestFlow } from '@/components/portal/bundles/PortalBundleInvestFlow'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'

type Props = {
  bundle: PortalCryptoBundle
  open: boolean
  onOpenChange: (open: boolean) => void
  /** @deprecated Utiliser la page `/app/invest/bundle/{portfolioId}` (comme swap). */
  asPage?: boolean
}

/**
 * @deprecated Ne plus ouvrir en modale — navigation vers `portalBundleInvestRoute`.
 * Conservé pour imports legacy ; redirige vers le flux page.
 */
export function PortalBundleInvestDialog({ bundle, open, onOpenChange }: Props) {
  if (!open) return null
  return <PortalBundleInvestFlow bundle={bundle} onExit={() => onOpenChange(false)} />
}
