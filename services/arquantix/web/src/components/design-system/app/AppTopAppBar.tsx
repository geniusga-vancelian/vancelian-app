import type { ReactNode } from 'react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

export type AppTopAppBarProps = {
  title: string
  onBack?: () => void
  backLabel?: string
  trailing?: ReactNode
  className?: string
}

const SPACER = <span className="ic-btn invisible pointer-events-none" aria-hidden />

/** Barre supérieure flow — preview/40-topappbar · `.ic-btn` + titre centré. */
export function AppTopAppBar({
  title,
  onBack,
  backLabel = 'Back',
  trailing,
  className,
}: AppTopAppBarProps) {
  return (
    <header className={cn('flex shrink-0 items-center gap-3', className)}>
      {onBack ? (
        <button type="button" className="ic-btn" onClick={onBack} aria-label={backLabel}>
          <KalaiIcon name="arrow-left" size={18} />
        </button>
      ) : (
        SPACER
      )}
      <h1 className="m-0 min-w-0 flex-1 text-center font-ui text-[18px] font-bold leading-tight text-v-fg">
        {title}
      </h1>
      {trailing ?? SPACER}
    </header>
  )
}
