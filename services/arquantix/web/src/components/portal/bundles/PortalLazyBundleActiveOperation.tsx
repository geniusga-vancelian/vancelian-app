'use client'

import dynamic from 'next/dynamic'
import type { ComponentProps } from 'react'

import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'

const PortalBundleActiveOperationPanel = dynamic(
  () =>
    import('@/components/portal/bundles/PortalBundleActiveOperationPanel').then((m) => ({
      default: m.PortalBundleActiveOperationPanel,
    })),
  { ssr: false, loading: () => null },
)

type Props = ComponentProps<typeof PortalBundleActiveOperationPanel>

/** Worker bundle en cours — Web3 lazy (reprise signature legs au chargement page). */
export function PortalLazyBundleActiveOperation(props: Props) {
  return (
    <PortalWeb3BoundaryLazy>
      <PortalBundleActiveOperationPanel {...props} />
    </PortalWeb3BoundaryLazy>
  )
}
