'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { AppDataList } from '@/components/design-system/app/AppDataList'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { PortalWalletRow } from '@/lib/portal/dashboardTypes'
import { portalWalletIcon, portalWalletIconToneClass } from '@/components/portal/dashboard/portalWalletIcons'
import { resolveAccountsRowHref } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

type Props = {
  rows: PortalWalletRow[]
  title?: string
  portfolioPending?: boolean
}

const PORTFOLIO_ROW_IDS = new Set(['crypto', 'offers', 'savings'])

export function PortalAccountsCard({ rows, title = 'My accounts', portfolioPending = false }: Props) {
  return (
    <AppDataList title={title}>
      {rows.map((row) => {
        const Icon = portalWalletIcon(row.iconKey)
        const locked = row.locked === true
        const href = resolveAccountsRowHref(row.id, locked)
        const rowPending = portfolioPending && PORTFOLIO_ROW_IDS.has(row.id)

        const leading = (
          <span
            className={cn(
              'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-v-input',
              portalWalletIconToneClass(row.iconTone),
              locked && 'opacity-50',
            )}
          >
            <Icon className="h-5 w-5" strokeWidth={1.75} />
          </span>
        )

        const trailing = (
          <>
            {rowPending ? (
              <span className="portal-shimmer h-5 w-16 rounded-v-input" aria-hidden />
            ) : locked && row.ctaLabel ? (
              <span className="list__amt font-medium text-v-blue">{row.ctaLabel}</span>
            ) : (
              <span className="list__amt">{row.balance}</span>
            )}
          </>
        )

        const body = (
          <>
            {leading}
            <div className="list__body min-w-0 flex-1">
              <div className={cn('list__title', locked && 'text-v-fg-muted')}>{row.title}</div>
              <div className="list__sub">{row.subtitle}</div>
            </div>
            <div className="list__amt-col flex shrink-0 items-center gap-1">
              {trailing}
              {href ? (
                <KalaiIcon name="chevron-right" size={20} className="list__chv shrink-0" />
              ) : null}
            </div>
          </>
        )

        const rowClass = cn(
          'list__item flex w-full items-center gap-3 no-underline',
          locked && 'opacity-70',
        )

        if (href) {
          return (
            <PortalNavLink key={row.id} href={href} className={rowClass}>
              {body}
            </PortalNavLink>
          )
        }

        return (
          <div key={row.id} className={cn(rowClass, 'list__item--static')}>
            {body}
          </div>
        )
      })}
    </AppDataList>
  )
}
