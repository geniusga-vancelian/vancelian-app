'use client'

import { PortalCryptoWalletBundleDetailScreen } from '@/components/portal/wallet/PortalCryptoWalletBundleDetailScreen'

type Props = {
  params: { portfolioId: string }
}

export default function PortalCryptoWalletBundlePage({ params }: Props) {
  return <PortalCryptoWalletBundleDetailScreen portfolioId={params.portfolioId} />
}
