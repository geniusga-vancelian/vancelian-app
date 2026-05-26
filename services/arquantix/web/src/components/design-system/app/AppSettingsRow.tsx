import type { ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

type Props = {
  title: string
  subtitle?: string
  leading?: ReactNode
  trailing?: ReactNode
  href?: string
  onClick?: () => void
  staticRow?: boolean
  danger?: boolean
  className?: string
}

export function AppSettingsRow({
  title,
  subtitle,
  leading,
  trailing,
  href,
  onClick,
  staticRow = false,
  danger = false,
  className,
}: Props) {
  const content = (
    <>
      {leading ? <span className="stg-row__lead">{leading}</span> : null}
      <span className="stg-row__body">
        <span className="stg-row__title">{title}</span>
        {subtitle ? <span className="stg-row__sub">{subtitle}</span> : null}
      </span>
      <span className="stg-row__trail">
        {trailing}
        {(href || onClick) && !staticRow ? (
          <KalaiIcon name="chevron-right" size={16} className="stg-row__chev" />
        ) : null}
      </span>
    </>
  )

  const rowClass = cn(
    'stg-row',
    staticRow && 'is-static',
    danger && 'is-danger',
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
