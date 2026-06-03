'use client'

import { PortalSavingsVaultDetailScreen } from '@/components/portal/wallet/PortalSavingsVaultDetailScreen'

type Props = {
  params: { vault: string }
}

export default function PortalSavingsVaultDetailPage({ params }: Props) {
  return <PortalSavingsVaultDetailScreen vaultAddress={params.vault} />
}
