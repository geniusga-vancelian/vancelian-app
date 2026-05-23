'use client'

import Link from 'next/link'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
import { Button } from '@/components/ui/button'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'

type Props = {
  progressPercent?: number
}

export function PortalUnlockEuroBanner({ progressPercent }: Props) {
  const progress =
    progressPercent != null ? `${Math.max(0, Math.min(100, progressPercent))}% complete` : null

  return (
    <article className="rounded-v-card border border-v-fg-10 bg-v-card p-4 shadow-v-subtle sm:p-5">
      <VEyebrow className="mb-2">Euro account</VEyebrow>
      <h2 className="m-0 font-ui text-[18px] font-semibold text-v-fg">Unlock Euro account</h2>
      <p className="m-0 mt-2 font-ui text-[15px] leading-relaxed text-v-fg-body">
        Your crypto wallet is ready. Complete registration to add a Euro account and access all
        investment categories from your crypto balance.
      </p>
      {progress ? (
        <p className="m-0 mt-2 font-ui text-[13px] text-v-fg-muted">Registration · {progress}</p>
      ) : null}
      <Button type="button" asChild className="mt-4 w-full sm:w-auto">
        <Link href={PORTAL_ROUTES.registration}>Complete registration</Link>
      </Button>
    </article>
  )
}
