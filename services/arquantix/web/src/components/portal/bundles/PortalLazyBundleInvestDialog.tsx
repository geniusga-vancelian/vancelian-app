'use client'

import dynamic from 'next/dynamic'
import type { ComponentProps } from 'react'

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

/** Invest bundle modal — code-split ; Web3 uniquement à Review+ (R4.5-F5-A). */
export function PortalLazyBundleInvestDialog({ open, ...rest }: Props) {
  if (!open) return null
  return <PortalBundleInvestDialog open={open} {...rest} />
}
