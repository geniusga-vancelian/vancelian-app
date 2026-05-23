'use client'

import { PortalCryptoWalletDetailScreen } from '@/components/portal/wallet/PortalCryptoWalletDetailScreen'

type Props = {
  params: { asset: string }
}

export default function PortalCryptoWalletAssetPage({ params }: Props) {
  return <PortalCryptoWalletDetailScreen asset={params.asset} />
}
