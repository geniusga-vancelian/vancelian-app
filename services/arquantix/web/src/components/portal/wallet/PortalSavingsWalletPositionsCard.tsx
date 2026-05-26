'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { TrendingUp } from 'lucide-react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { AppDataList } from '@/components/design-system/app/AppDataList'
import {
  formatSavingsApyLabel,
  formatSavingsMoney,
  resolveSavingsPositionSubtitle,
  resolveSavingsPositionValue,
} from '@/lib/portal/portalSavingsFormat'
import type { PortalSavingsPosition } from '@/lib/portal/portalSavingsTypes'
import { portalSavingsVaultRoute } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  positions: PortalSavingsPosition[]
  currency: string
  title?: string
  emptyMessage?: string
}

export function PortalSavingsWalletPositionsCard({
  positions,
  currency,
  title = 'Vaults',
  emptyMessage = 'Aucune position épargne pour le moment',
}: Props) {
  return (
    <AppDataList title={title} isEmpty={positions.length === 0} emptyMessage={emptyMessage}>
      {positions.map((position) => {
        const valueLabel = formatSavingsMoney(resolveSavingsPositionValue(position, currency), currency)
        const pendingYield = position.yieldSyncStatus === 'pending'
        const apyLabel =
          position.userApyBps != null && Number.isFinite(position.userApyBps)
            ? formatSavingsApyLabel(position.userApyBps)
            : null

        return (
          <PortalNavLink
            key={position.vaultAddress}
            href={portalSavingsVaultRoute(position.vaultAddress)}
            className="list__item flex w-full items-center gap-3 no-underline"
          >
            <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-v-input bg-v-green text-white">
              <TrendingUp className="h-5 w-5" strokeWidth={1.75} />
            </span>
            <div className="list__body min-w-0 flex-1">
              <div className="list__title">{position.vaultName}</div>
              <div className="list__sub">{resolveSavingsPositionSubtitle(position)}</div>
            </div>
            <div className="list__amt-col flex shrink-0 flex-col items-end gap-0.5">
              {pendingYield ? (
                <span className="portal-shimmer h-5 w-16 rounded-v-input" aria-hidden />
              ) : (
                <span className="list__amt">{valueLabel}</span>
              )}
              {apyLabel ? (
                <span className={cn('list__indic list__indic--up')}>{apyLabel}</span>
              ) : null}
              <KalaiIcon name="chevron-right" size={20} className="list__chv shrink-0" />
            </div>
          </PortalNavLink>
        )
      })}
    </AppDataList>
  )
}
