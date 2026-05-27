'use client'

import { AppAccountSummaryList } from '@/components/design-system/app/AppAccountSummaryList'
import { AppAccountSummaryRow } from '@/components/design-system/app/AppAccountSummaryRow'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PortalWalletRowAvatar } from '@/components/portal/dashboard/portalWalletIcons'
import type { PortalWalletRow } from '@/lib/portal/dashboardTypes'
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
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={title} />
      <AppAccountSummaryList>
        {rows.map((row) => {
          const locked = row.locked === true
          const href = resolveAccountsRowHref(row.id, locked)
          const rowPending = portfolioPending && PORTFOLIO_ROW_IDS.has(row.id)

          const amountNode = rowPending ? (
            <span className="portal-shimmer h-5 w-16 rounded-v-input" aria-hidden />
          ) : locked && row.ctaLabel ? (
            <div className="acct-summary__amt font-medium text-v-blue">{row.ctaLabel}</div>
          ) : undefined

          return (
            <AppAccountSummaryRow
              key={row.id}
              href={href ?? undefined}
              LinkComponent={href ? PortalNavLink : undefined}
              className={cn(locked && 'opacity-70')}
              leading={
                <PortalWalletRowAvatar
                  iconKey={row.iconKey}
                  iconTone={row.iconTone}
                  locked={locked}
                  surface="account"
                />
              }
              title={row.title}
              subtitle={row.subtitle}
              amount={amountNode ? '' : row.balance}
              amountNode={amountNode}
              showChevron={false}
            />
          )
        })}
      </AppAccountSummaryList>
    </section>
  )
}
