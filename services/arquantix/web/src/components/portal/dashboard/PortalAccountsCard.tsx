'use client'

import type { ReactNode } from 'react'
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
  registrationProgressPercent?: number
  registrationStepCompleted?: number
  registrationStepTotal?: number
}

const PORTFOLIO_ROW_IDS = new Set(['crypto', 'offers', 'savings'])

function resolveRegistrationProgressLabel(
  completed?: number,
  total?: number,
): ReactNode | undefined {
  if (completed == null || total == null || total <= 0) return undefined
  return (
    <>
      Étape <b>{completed}</b> sur {total}
    </>
  )
}

export function PortalAccountsCard({
  rows,
  title = 'Mes comptes',
  portfolioPending = false,
  registrationProgressPercent,
  registrationStepCompleted,
  registrationStepTotal,
}: Props) {
  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={title} size="sm" />
      <AppAccountSummaryList>
        {rows.map((row) => {
          const locked = row.locked === true
          const shimmerPending = portfolioPending && PORTFOLIO_ROW_IDS.has(row.id)
          const pending = locked || shimmerPending
          const href = resolveAccountsRowHref(row.id, locked)

          return (
            <AppAccountSummaryRow
              key={row.id}
              href={href ?? undefined}
              LinkComponent={href ? PortalNavLink : undefined}
              className={cn(locked && shimmerPending && 'opacity-70')}
              pending={pending}
              showChevron={Boolean(href) && !locked}
              leading={
                <PortalWalletRowAvatar
                  iconKey={row.iconKey}
                  iconTone={row.iconTone}
                  locked={locked}
                  surface="account"
                />
              }
              title={row.id === 'euro' && locked ? 'Compte euro' : row.title}
              subtitle={
                locked
                  ? 'Compte courant en euros'
                  : row.subtitle
              }
              amount={shimmerPending ? '' : locked ? '' : row.balance}
              amountNode={
                shimmerPending ? (
                  <span className="portal-shimmer h-5 w-16 rounded-v-input" aria-hidden />
                ) : undefined
              }
              ctaLabel={
                locked
                  ? 'Compléter mon inscription'
                  : row.ctaLabel
              }
              progressPercent={locked ? registrationProgressPercent : undefined}
              progressLabel={
                locked
                  ? resolveRegistrationProgressLabel(
                      registrationStepCompleted,
                      registrationStepTotal,
                    )
                  : undefined
              }
            />
          )
        })}
      </AppAccountSummaryList>
    </section>
  )
}
