import type { ReactNode } from 'react'
import Link from 'next/link'
import { AppButton } from './AppButton'
import { cn } from '@/lib/utils'

type Props = {
  title?: string
  lead: ReactNode
  poweredBy?: string
  ctaLabel: string
  onCtaClick?: () => void
  ctaHref?: string
  className?: string
}

/** Carte CTA « Avance de liquidité » — `.v-card.brw-cta` (Webapp-full). */
export function AppBorrowCtaCard({
  title = 'Avance de liquidité',
  lead,
  poweredBy = 'Morpho',
  ctaLabel,
  onCtaClick,
  ctaHref,
  className,
}: Props) {
  const cta = ctaHref ? (
    <Link href={ctaHref} className="btn btn--primary btn--lg brw-cta__btn">
      {ctaLabel}
    </Link>
  ) : (
    <AppButton variant="primary" size="lg" className="brw-cta__btn" onClick={onCtaClick}>
      {ctaLabel}
    </AppButton>
  )

  return (
    <article className={cn('v-card brw-cta', className)}>
      <div className="brw-cta__body">
        <h3 className="brw-cta__title">{title}</h3>
        <p className="brw-cta__lead">{lead}</p>
        {poweredBy ? (
          <p className="brw-cta__powered">
            <span className="brw-cta__powered-lbl">Propulsé par</span>
            <span className="brw-cta__powered-name">{poweredBy}</span>
          </p>
        ) : null}
      </div>
      {cta}
    </article>
  )
}
