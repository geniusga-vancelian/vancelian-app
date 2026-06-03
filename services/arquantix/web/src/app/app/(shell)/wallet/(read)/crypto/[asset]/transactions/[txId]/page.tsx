'use client'

import { PortalCryptoTransactionDetailScreen } from '@/components/portal/wallet/PortalCryptoTransactionDetailScreen'

type Props = {
  params: { asset: string; txId: string }
}

export default function PortalCryptoWalletTransactionDetailPage({ params }: Props) {
  return <PortalCryptoTransactionDetailScreen asset={params.asset} txId={params.txId} />
}
