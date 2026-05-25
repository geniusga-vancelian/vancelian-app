'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { ChevronRight, TrendingUp } from 'lucide-react'
import {
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
  if (positions.length === 0) {
    return (
      <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card p-8 text-center shadow-v-subtle">
        <p className="m-0 font-ui text-[15px] text-v-fg-muted">{emptyMessage}</p>
      </article>
    )
  }

  return (
    <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
      <div className="border-b border-v-fg-10 px-4 py-3">
        <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">{title}</h2>
      </div>
      <ul className="m-0 list-none p-0">
        {positions.map((position) => {
          const valueLabel = formatSavingsMoney(resolveSavingsPositionValue(position, currency), currency)
          const pendingYield = position.yieldSyncStatus === 'pending'

          return (
            <li key={position.vaultAddress}>
              <PortalNavLink
                href={portalSavingsVaultRoute(position.vaultAddress)}
                className="flex w-full items-center gap-3 px-4 py-3.5 text-left no-underline transition-colors duration-v-fast hover:bg-v-card-hover"
              >
                <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-v-input bg-v-green text-white">
                  <TrendingUp className="h-5 w-5" strokeWidth={1.75} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-ui text-[15px] font-semibold text-v-fg">
                    {position.vaultName}
                  </span>
                  <span className="mt-0.5 block truncate font-ui text-[13px] text-v-fg-muted">
                    {resolveSavingsPositionSubtitle(position)}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-1">
                  <span className="flex flex-col items-end gap-0.5">
                    <span className="font-ui text-[15px] font-semibold tabular-nums text-v-fg">
                      {valueLabel}
                    </span>
                    <span
                      className={cn(
                        'font-ui text-[12px] tabular-nums',
                        pendingYield ? 'text-v-fg-muted' : 'text-v-green',
                      )}
                    >
                      {position.earnedYieldDisplay}
                    </span>
                  </span>
                  <ChevronRight className="h-4 w-4 text-v-fg-muted" aria-hidden />
                </span>
              </PortalNavLink>
            </li>
          )
        })}
      </ul>
    </article>
  )
}
