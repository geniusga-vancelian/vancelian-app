'use client'

import type { ComponentProps } from 'react'

import { PortalBundleWithdrawDialog } from '@/components/portal/bundles/PortalBundleWithdrawDialog'
import { PortalWeb3BoundaryLazy } from '@/components/portal/web3/PortalWeb3BoundaryLazy'

type Props = ComponentProps<typeof PortalBundleWithdrawDialog>

/** Withdraw bundle page — Web3 lazy minimal (R4.5-F5-A), UX withdraw inchangée (F5.1). */
export function PortalLazyBundleWithdrawShell({ open, ...rest }: Props) {
  if (!open) return null

  return (
    <PortalWeb3BoundaryLazy>
      <PortalBundleWithdrawDialog open={open} {...rest} />
    </PortalWeb3BoundaryLazy>
  )
}
