'use client'

import dynamic from 'next/dynamic'
import type { ComponentProps } from 'react'

import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'

const PortalEarnVaultModal = dynamic(
  () =>
    import('@/components/portal/invest/PortalEarnVaultModal').then((m) => ({
      default: m.PortalEarnVaultModal,
    })),
  { ssr: false, loading: () => null },
)

type Props = ComponentProps<typeof PortalEarnVaultModal>

export function PortalLazyEarnVaultModal(props: Props) {
  return (
    <PortalWeb3BoundaryLazy>
      <PortalEarnVaultModal {...props} />
    </PortalWeb3BoundaryLazy>
  )
}
