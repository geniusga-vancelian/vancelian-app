'use client'

import dynamic from 'next/dynamic'
import type { ComponentProps } from 'react'

import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'

const PortalBundleAllocationActionsPanel = dynamic(
  () =>
    import('@/components/portal/bundles/PortalBundleAllocationActionsPanel').then((m) => ({
      default: m.PortalBundleAllocationActionsPanel,
    })),
  { ssr: false, loading: () => null },
)

type Props = ComponentProps<typeof PortalBundleAllocationActionsPanel>

/** Wallet bundle allocation actions — Web3 uniquement au montage (R4.5-F5-B). */
export function PortalLazyBundleAllocationActions({ ...props }: Props) {
  return (
    <PortalWeb3BoundaryLazy>
      <PortalBundleAllocationActionsPanel {...props} />
    </PortalWeb3BoundaryLazy>
  )
}
