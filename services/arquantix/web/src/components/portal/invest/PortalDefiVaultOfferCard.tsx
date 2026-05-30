'use client'

import { Banknote, TrendingUp, Wallet } from 'lucide-react'

import { AppExclusiveOfferCard } from '@/components/design-system/app/AppExclusiveOfferCard'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import type { PortalLedgityVaultDetails } from '@/lib/portal/ledgity/ledgityVaultTypes'
import {
  formatEarnApyFromBps as formatLedgityApyFromBps,
} from '@/lib/portal/ledgity/ledgityVaultFormat'
import { formatEarnApyFromBps, formatEarnUsd } from '@/lib/portal/morphoVaultFormat'
import type { PortalMorphoVaultDetails } from '@/lib/portal/morphoVaultTypes'
import { cn } from '@/lib/utils'

type Props = {
  vault: PortalMorphoVaultDetails | PortalLedgityVaultDetails
  href: string
  className?: string
}

function isLedgityVault(
  vault: PortalMorphoVaultDetails | PortalLedgityVaultDetails,
): vault is PortalLedgityVaultDetails {
  return vault.integrationMode === 'ledgity_vault'
}

export function PortalDefiVaultOfferCard({ vault, href, className }: Props) {
  const ledgity = isLedgityVault(vault)
  const apyLabel = ledgity
    ? formatLedgityApyFromBps(vault.userApyBps)
    : formatEarnApyFromBps(vault.userApyBps)

  return (
    <PortalNavLink href={href} className="block no-underline">
      <AppExclusiveOfferCard
        className={cn(className)}
        imageSeed={vault.id}
        category={ledgity ? 'Ledgity (RWA)' : vault.provider}
        title={vault.name}
        description={vault.description ?? undefined}
        ctaLabel="Deposit / Withdraw"
        href={href}
        chips={[
          {
            key: 'apy',
            label: apyLabel,
            icon: <TrendingUp aria-hidden />,
          },
          {
            key: 'tvl',
            label: formatEarnUsd(vault.tvlUsd),
            icon: <Banknote aria-hidden />,
          },
          {
            key: 'asset',
            label: vault.asset.symbol,
            icon: <Wallet aria-hidden />,
          },
        ]}
      />
    </PortalNavLink>
  )
}
