'use client'

import { PortalCryptoWalletTransactionsScreen } from '@/components/portal/wallet/PortalCryptoWalletTransactionsScreen'

type Props = {
  params: { asset: string }
}

export default function PortalCryptoWalletTransactionsPage({ params }: Props) {
  return <PortalCryptoWalletTransactionsScreen asset={params.asset} />
}
