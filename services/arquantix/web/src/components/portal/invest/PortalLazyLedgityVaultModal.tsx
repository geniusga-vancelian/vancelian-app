'use client'

import dynamic from 'next/dynamic'
import type { ComponentProps } from 'react'

import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'

const PortalLedgityVaultModal = dynamic(
  () =>
    import('@/components/portal/invest/PortalLedgityVaultModal').then((m) => ({
      default: m.PortalLedgityVaultModal,
    })),
  { ssr: false, loading: () => null },
)

type Props = ComponentProps<typeof PortalLedgityVaultModal>

export function PortalLazyLedgityVaultModal(props: Props) {
  return (
    <PortalWeb3BoundaryLazy>
      <PortalLedgityVaultModal {...props} />
    </PortalWeb3BoundaryLazy>
  )
}
