import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export type AppMetricsListVariant = 'plain' | 'lined'

type Props = {
  children: ReactNode
  className?: string
  /** `plain` = preview/33 default · `lined` = séparateurs entre lignes. */
  variant?: AppMetricsListVariant
}

/** Carte liste métriques — preview/33-card-data-list. */
export function AppMetricsList({ children, className, variant = 'plain' }: Props) {
  return (
    <article className={cn('stats', variant === 'lined' && 'stats--lined', className)}>
      {children}
    </article>
  )
}
