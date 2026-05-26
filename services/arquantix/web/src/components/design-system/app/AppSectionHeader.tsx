import type { ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

type Props = {
  title: string
  moreHref?: string
  moreLabel?: string
  action?: ReactNode
  className?: string
}

/** En-tête de section in-page — pattern `sh-app` du DS. */
export function AppSectionHeader({
  title,
  moreHref,
  moreLabel = 'Voir tout',
  action,
  className,
}: Props) {
  return (
    <div className={cn('sh-app w-full', className)}>
      <span className="sh-app__dot" aria-hidden />
      <h2 className="sh-app__title m-0">{title}</h2>
      {action ??
        (moreHref ? (
          <Link href={moreHref} className="sh-app__more inline-flex items-center gap-1 no-underline">
            {moreLabel}
            <KalaiIcon name="chevron-right" size={16} className="text-current" aria-hidden />
          </Link>
        ) : null)}
    </div>
  )
}
