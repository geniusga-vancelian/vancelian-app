'use client'

import Link from 'next/link'
import { ArrowLeftRight, ArrowUpRight, Plus } from 'lucide-react'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type Props = {
  displayName: string
  balanceLabel: string
  performanceLabel: string
  periodLabel?: string
  chartValues: number[]
  depositHref: string
  className?: string
}

/**
 * En-tête dashboard « plateforme web » — fond clair, carte patrimoine DS,
 * actions en boutons pill (pas de hero sombre ni cercles Flutter).
 */
export function PortalDashboardHeader({
  displayName,
  balanceLabel,
  performanceLabel,
  periodLabel = 'All time',
  chartValues,
  depositHref,
  className,
}: Props) {
  const perfPositive = !performanceLabel.startsWith('-')

  return (
    <section className={cn('flex flex-col gap-4 pb-2 pt-5', className)}>
      <div className="flex flex-col gap-1">
        <VEyebrow>Portfolio</VEyebrow>
        <h1 className="m-0 font-ui text-[22px] font-semibold leading-tight tracking-v-tight text-v-fg">
          Hello, {displayName}
        </h1>
      </div>

      <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card p-4 shadow-v-subtle sm:p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="m-0 font-ui text-[13px] font-medium text-v-fg-muted">Total balance</p>
            <p className="mt-1 mb-0 font-ui text-[28px] font-bold leading-none tracking-v-tight text-v-fg sm:text-[32px]">
              {balanceLabel}
            </p>
          </div>
          <span
            className={cn(
              'inline-flex shrink-0 flex-col items-end rounded-v-pill px-2.5 py-1 font-ui text-[12px] font-medium leading-tight sm:flex-row sm:items-center sm:gap-1',
              perfPositive ? 'bg-v-green-bg text-v-green' : 'bg-v-error-bg text-v-error',
            )}
          >
            <span>{performanceLabel}</span>
            <span className="text-v-fg-muted">{periodLabel}</span>
          </span>
        </div>

        <div className="mt-4 border-t border-v-fg-05 pt-4">
          <PortalPerformanceChart values={chartValues} tone="light" height={88} />
        </div>
      </article>

      <div className="flex flex-wrap gap-2">
        <Button type="button" size="sm" className="gap-1.5" asChild>
          <Link href={depositHref}>
            <Plus className="h-4 w-4" />
            Deposit
          </Link>
        </Button>
        <Button type="button" variant="outline" size="sm" className="gap-1.5" disabled>
          <ArrowUpRight className="h-4 w-4" />
          Send
        </Button>
        <Button type="button" variant="outline" size="sm" className="gap-1.5" disabled>
          <ArrowLeftRight className="h-4 w-4" />
          Exchange
        </Button>
      </div>
    </section>
  )
}
