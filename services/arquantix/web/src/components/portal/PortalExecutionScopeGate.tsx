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
          Réseau incompatible
        </p>
        <p className="m-0 mt-2 font-ui text-[14px] leading-relaxed text-v-fg-muted">
          Cette opération nécessite le réseau <strong>{requiredLabel}</strong>. Sélectionnez{' '}
          {requiredLabel} dans la barre de navigation — réseau actuel : {chainLabel}.
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
        <p className="m-0 font-ui text-[15px] font-semibold text-v-fg">Wallet requis</p>
        <p className="m-0 font-ui text-[14px] leading-relaxed text-v-fg-muted">
          Aucun wallet disponible pour {chainLabel}
          {walletLabel !== 'Aucun wallet' ? ` (${walletLabel})` : ''}. Choisissez un wallet dans
          la navbar ou liez MetaMask depuis Mon wallet.
        </p>
        <Button type="button" asChild className="rounded-full">
          <PortalNavLink href={PORTAL_ROUTES.walletCreate}>Créer mon wallet crypto</PortalNavLink>
        </Button>
        <Button type="button" asChild variant="outline" className="rounded-full">
          <PortalNavLink href={portalProfileWalletsRoute()}>Lier MetaMask</PortalNavLink>
        </Button>
      </article>
    )
  }

  return <>{children}</>
}
