'use client'

import { PortalMorphoVaultInvestScreen } from '@/components/portal/invest/PortalMorphoVaultInvestScreen'

type Props = {
  params: { address: string }
}

export default function PortalMorphoVaultInvestPage({ params }: Props) {
  return <PortalMorphoVaultInvestScreen vaultAddress={params.address} />
}
