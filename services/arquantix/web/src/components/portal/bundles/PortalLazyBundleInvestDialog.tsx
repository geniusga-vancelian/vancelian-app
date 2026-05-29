'use client'

import dynamic from 'next/dynamic'
import type { ComponentProps } from 'react'

import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'

const PortalBundleInvestDialog = dynamic(
  () =>
    import('@/components/portal/bundles/PortalBundleInvestDialog').then((m) => ({
      default: m.PortalBundleInvestDialog,
    })),
  {
    ssr: false,
    loading: () => null,
  },
)

type Props = ComponentProps<typeof PortalBundleInvestDialog>

/** Invest bundle — Web3 + Li.FI chargés uniquement à l’ouverture du dialog. */
export function PortalLazyBundleInvestDialog({ open, ...rest }: Props) {
  if (!open) return null

  return (
    <PortalWeb3BoundaryLazy>
      <PortalBundleInvestDialog open={open} {...rest} />
    </PortalWeb3BoundaryLazy>
  )
}
