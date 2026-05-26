import type { ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

type Props = {
  leading: ReactNode
  title: string
  subtitle?: string
  trailing?: ReactNode
  href?: string
  onClick?: () => void
  className?: string
  staticRow?: boolean
}

/** Ligne liste données (comptes, positions) — DS 05-lists stacked. */
export function AppDataRow({
  leading,
  title,
  subtitle,
  trailing,
  href,
  onClick,
  className,
  staticRow = false,
}: Props) {
  const content = (
    <>
      {leading}
      <div className="list__body min-w-0 flex-1">
        <div className="list__title">{title}</div>
        {subtitle ? <div className="list__sub">{subtitle}</div> : null}
      </div>
      <div className="list__amt-col flex shrink-0 items-center gap-1">
        {trailing}
        {(href || onClick) && !staticRow ? (
          <span className="list__chv" aria-hidden>
            <KalaiIcon name="chevron-right" size={20} />
          </span>
        ) : null}
      </div>
    </>
  )

  const rowClass = cn(
    'list__item flex w-full items-center gap-3',
    staticRow && 'list__item--static',
    className,
  )

  if (href) {
    return (
      <Link href={href} className={cn(rowClass, 'no-underline')}>
        {content}
      </Link>
    )
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={rowClass}>
        {content}
      </button>
    )
  }

  return <div className={rowClass}>{content}</div>
}
