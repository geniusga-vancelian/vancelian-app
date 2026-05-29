import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  figure: ReactNode
  figureTone?: 'gain' | 'loss' | 'neutral'
  subtitle?: ReactNode
  children: ReactNode
  className?: string
}

/** Barre d’action fixe mobile — `.mstick` (Webapp-full layout.css). */
export function AppMobileStickyBar({
  figure,
  figureTone = 'neutral',
  subtitle,
  children,
  className,
}: Props) {
  return (
    <div className={cn('mstick', className)} role="region" aria-label="Actions">
      <div className="mstick__inner">
        <div className="mstick__meta">
          <span
            className={cn(
              'mstick__k',
              figureTone === 'gain' && 'mstick__k--gain',
              figureTone === 'loss' && 'mstick__k--loss',
            )}
          >
            {figure}
          </span>
          {subtitle ? <span className="mstick__sub">{subtitle}</span> : null}
        </div>
        <div className="mstick__cta">{children}</div>
      </div>
    </div>
  )
}
