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

export type PortalCreditLineRow = {
  title?: string
  subtitle: string
  balanceLabel: string
  href: string
  pending?: boolean
}

type Props = {
  rows: PortalWalletRow[]
  creditLine?: PortalCreditLineRow | null
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
      Step <b>{completed}</b> of {total}
    </>
  )
}

export function PortalAccountsCard({
  rows,
  creditLine,
  title = 'My accounts',
  portfolioPending = false,
  registrationProgressPercent,
  registrationStepCompleted,
  registrationStepTotal,
}: Props) {
  return (
    <section className="flex w-full flex-col gap-3">
      <AppSectionHeader title={title} size="lg" />
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
                <PortalWalletRowAvatar rowId={row.id} locked={locked} />
              }
              title={row.id === 'euro' && locked ? 'Euro account' : row.title}
              subtitle={
                locked
                  ? 'Euro current account'
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
                  ? 'Complete registration'
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

      {creditLine ? (
        <AppAccountSummaryList className="mt-2">
          <AppAccountSummaryRow
            href={creditLine.href}
            LinkComponent={PortalNavLink}
            showChevron
            pending={creditLine.pending}
            leading={<PortalWalletRowAvatar rowId="credit-line" />}
            title={creditLine.title ?? 'Credit Line'}
            subtitle={creditLine.subtitle}
            amount={creditLine.pending ? '' : creditLine.balanceLabel}
            amountNode={
              creditLine.pending ? (
                <span className="portal-shimmer h-5 w-20 rounded-v-input" aria-hidden />
              ) : undefined
            }
          />
        </AppAccountSummaryList>
      ) : null}
    </section>
  )
}
