import type { ReactNode } from 'react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

type Props = {
  label: string
  value: ReactNode
  className?: string
  valueClassName?: string
  /** Icône Kalai en tête de label (variant « with icons »). */
  leadingIcon?: string
  /** Affiche l’icône info à droite de la valeur. */
  infoLabel?: string
}

/** Ligne métrique — preview/33-card-data-list. */
export function AppMetricsRow({
  label,
  value,
  className,
  valueClassName,
  leadingIcon,
  infoLabel,
}: Props) {
  return (
    <div className={cn('stat', className)}>
      <span className="stat__label">
        {leadingIcon ? (
          <KalaiIcon name={leadingIcon} size={20} className="stat__lead" aria-hidden />
        ) : null}
        {label}
      </span>
      <span className={cn('stat__value', valueClassName)}>
        {value}
        {infoLabel ? (
          <KalaiIcon name="info" size={16} className="stat__info" title={infoLabel} />
        ) : null}
      </span>
    </div>
  )
}
