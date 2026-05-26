import { cn } from '@/lib/utils'

type Props = {
  label: string
  selected?: boolean
  onClick?: () => void
  className?: string
}

/** Filtre pill — preview/50-selection-chips. */
export function AppFilterChip({ label, selected = false, onClick, className }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={cn('chip', selected && 'is-selected', className)}
    >
      {label}
    </button>
  )
}
