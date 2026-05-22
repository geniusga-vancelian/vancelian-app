'use client'

import { Button } from '@/components/ui/button'
import { PortalSectionHeading } from '@/components/portal/PortalPageIntro'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { formatChangePct } from '@/lib/portal/marketsFormat'
import { cn } from '@/lib/utils'

type Props = {
  bundles: PortalCryptoBundle[]
}

function BundleCard({ bundle }: { bundle: PortalCryptoBundle }) {
  const perf = bundle.performance1d
  const perfLabel = perf == null ? '—' : formatChangePct(perf)

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
      <div className="relative aspect-[2/1] w-full overflow-hidden bg-v-fg-05 sm:aspect-[5/2]">
        {bundle.imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={bundle.imageUrl} alt="" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full w-full items-center justify-center font-ui text-[12px] text-v-fg-muted">
            Bundle
          </div>
        )}
        {bundle.riskLabel ? (
          <span className="absolute left-2 top-2 rounded-v-tag bg-white/95 px-2 py-0.5 font-ui text-[10px] font-medium uppercase tracking-v-wide text-v-fg">
            {bundle.riskLabel}
          </span>
        ) : null}
      </div>
      <div className="flex flex-1 flex-col gap-2 p-3 sm:p-3.5">
        <div className="min-w-0">
          <h3 className="m-0 line-clamp-1 font-ui text-[15px] font-semibold leading-snug text-v-fg">
            {bundle.title}
          </h3>
          {bundle.description ? (
            <p className="mt-1 mb-0 line-clamp-2 font-ui text-[12px] leading-snug text-v-fg-body">
              {bundle.description}
            </p>
          ) : null}
        </div>
        <div className="mt-auto flex items-center justify-between gap-2 pt-1">
          <div className="min-w-0">
            <p className="m-0 font-ui text-[11px] text-v-fg-muted">1d perf.</p>
            <p
              className={cn(
                'm-0 font-ui text-[13px] font-semibold',
                perf != null && perf >= 0 ? 'text-v-green' : 'text-v-error',
              )}
            >
              {perfLabel}
            </p>
          </div>
          <Button type="button" size="sm" variant="outline" className="h-8 shrink-0 px-3 text-[12px]" disabled>
            Invest
          </Button>
        </div>
      </div>
    </article>
  )
}

export function PortalCryptoBundlesSection({ bundles }: Props) {
  if (bundles.length === 0) return null

  return (
    <section className="flex flex-col gap-4">
      <PortalSectionHeading title="Crypto Bundles" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {bundles.map((bundle) => (
          <BundleCard key={bundle.id} bundle={bundle} />
        ))}
      </div>
    </section>
  )
}
