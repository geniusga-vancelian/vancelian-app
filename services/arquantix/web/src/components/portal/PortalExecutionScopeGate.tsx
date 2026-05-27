'use client'

import type { ReactNode } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { Button } from '@/components/ui/button'
import { PORTAL_ROUTES, portalProfileWalletsRoute } from '@/lib/portal/portalRouting'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { cn } from '@/lib/utils'

type Requirement = 'swap' | 'defi' | 'wallet'

type Props = {
  requirement: Requirement
  children: ReactNode
  className?: string
}

const REQUIRED_CHAIN_LABEL: Record<'defi', string> = {
  defi: 'Base',
}

export function PortalExecutionScopeGate({ requirement, children, className }: Props) {
  const {
    chainLabel,
    walletLabel,
    scopeLoading,
    deFiEnabled,
    walletReady,
  } = usePortalExecutionScope()

  const requiresDeFiChain = requirement === 'defi'
  const enabled = requiresDeFiChain ? deFiEnabled : true
  const requiredLabel = requiresDeFiChain ? REQUIRED_CHAIN_LABEL.defi : null

  if (scopeLoading) {
    return (
      <div className={cn('flex min-h-[30vh] items-center justify-center py-10', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-v-fg-muted" />
      </div>
    )
  }

  if (!enabled && requiredLabel) {
    return (
      <article
        className={cn(
          'mx-auto max-w-lg rounded-v-card border border-v-border bg-v-card px-5 py-6 text-center shadow-v-subtle',
          className,
        )}
      >
        <p className="m-0 font-ui text-[15px] font-semibold text-v-fg">
          Incompatible network
        </p>
        <p className="m-0 mt-2 font-ui text-[14px] leading-relaxed text-v-fg-muted">
          This action requires the <strong>{requiredLabel}</strong> network. Select{' '}
          {requiredLabel} in the navigation bar — current network: {chainLabel}.
        </p>
      </article>
    )
  }

  if (!walletReady) {
    return (
      <article
        className={cn(
          'mx-auto flex max-w-lg flex-col gap-3 rounded-v-card border border-v-border bg-v-card px-5 py-6 shadow-v-subtle',
          className,
        )}
      >
        <p className="m-0 font-ui text-[15px] font-semibold text-v-fg">Wallet required</p>
        <p className="m-0 font-ui text-[14px] leading-relaxed text-v-fg-muted">
          No wallet available for {chainLabel}
          {walletLabel !== 'No wallet' ? ` (${walletLabel})` : ''}. Choose a wallet in the navbar
          or link MetaMask from My wallets.
        </p>
        <Button type="button" asChild className="rounded-full">
          <PortalNavLink href={PORTAL_ROUTES.walletCreate}>Create my crypto wallet</PortalNavLink>
        </Button>
        <Button type="button" asChild variant="outline" className="rounded-full">
          <PortalNavLink href={portalProfileWalletsRoute()}>Link MetaMask</PortalNavLink>
        </Button>
      </article>
    )
  }

  return <>{children}</>
}
