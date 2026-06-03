'use client'

import { PortalCryptoWalletBundleTransactionDetailScreen } from '@/components/portal/wallet/PortalCryptoWalletBundleTransactionDetailScreen'

type Props = {
  params: { portfolioId: string; txId: string }
}

export default function PortalCryptoWalletBundleTransactionDetailPage({ params }: Props) {
  return (
    <PortalCryptoWalletBundleTransactionDetailScreen
      portfolioId={params.portfolioId}
      txId={params.txId}
    />
  )
}
