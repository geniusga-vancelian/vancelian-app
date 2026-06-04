'use client'

import { PortalLedgityVaultInvestScreen } from '@/components/portal/invest/PortalLedgityVaultInvestScreen'

type Props = {
  params: { id: string }
}

export default function PortalLedgityVaultInvestPage({ params }: Props) {
  return <PortalLedgityVaultInvestScreen vaultId={params.id} />
}
