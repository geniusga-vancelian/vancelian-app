import type { ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

type Props = {
  title: string
  moreHref?: string
  moreLabel?: string
  action?: ReactNode
  size?: 'lg' | 'md' | 'sm'
  className?: string
}

/** En-tête de section — pattern Webapp4 `.sec` (remplace `sh-app`). */
export function AppSectionHeader({
  title,
  moreHref,
  moreLabel = 'Voir tout',
  action,
  size = 'sm',
  className,
}: Props) {
  return (
    <section className={cn('sec', size === 'lg' && 'sec--lg', size === 'md' && 'sec--md', size === 'sm' && 'sec--sm', className)}>
      <div className="sec__head">
        <h2 className="sec__title">{title}</h2>
        {action ?? (moreHref ? (
          <div className="sec__actions">
            <Link href={moreHref} className="sec__more inline-flex items-center gap-1 no-underline">
              {moreLabel}
              <KalaiIcon name="chevron-right" size={16} className="text-current" aria-hidden />
            </Link>
          </div>
        ) : null)}
      </div>
    </section>
  )
}
