import type { ReactNode } from 'react'
import Link from 'next/link'
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
    <div className={cn('sh-app', className)}>
      <span className="sh-app__dot" aria-hidden />
      <h2 className="sh-app__title m-0">{title}</h2>
      {action ??
        (moreHref ? (
          <Link href={moreHref} className="sh-app__more no-underline">
            {moreLabel}
          </Link>
        ) : null)}
    </div>
  )
}
