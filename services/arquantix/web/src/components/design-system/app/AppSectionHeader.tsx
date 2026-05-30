import type { ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

type Props = {
  title: string
  count?: number
  moreHref?: string
  moreLabel?: string
  action?: ReactNode
  desc?: string
  size?: 'lg' | 'md' | 'sm'
  className?: string
}

/** En-tête de section — pattern Webapp4 `.sec` (remplace `sh-app`). */
export function AppSectionHeader({
  title,
  count,
  moreHref,
  moreLabel = 'View all',
  action,
  desc,
  size = 'sm',
  className,
}: Props) {
  return (
    <section className={cn('sec', size === 'lg' && 'sec--lg', size === 'md' && 'sec--md', size === 'sm' && 'sec--sm', className)}>
      <div className="sec__head">
        <h2 className="sec__title">
          {title}
          {count != null ? <span className="sec__count">{`\u00a0·\u00a0${count}`}</span> : null}
        </h2>
        {action ?? (moreHref ? (
          <div className="sec__actions">
            <Link href={moreHref} className="sec__more no-underline">
              {moreLabel}
              <KalaiIcon name="chevron-right" size={16} className="text-current" aria-hidden />
            </Link>
          </div>
        ) : null)}
      </div>
      {desc ? <p className="sec__desc">{desc}</p> : null}
    </section>
  )
}
