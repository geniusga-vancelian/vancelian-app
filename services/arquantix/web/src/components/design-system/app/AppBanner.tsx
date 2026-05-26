import type { ReactNode } from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

export type AppBannerVariant = 'success' | 'warning' | 'info' | 'error' | 'neutral'

type Props = {
  variant?: AppBannerVariant
  title: string
  message?: string
  ctaLabel?: string
  ctaHref?: string
  onCtaClick?: () => void
  className?: string
  children?: ReactNode
}

export function AppBanner({
  variant = 'info',
  title,
  message,
  ctaLabel,
  ctaHref,
  onCtaClick,
  className,
  children,
}: Props) {
  const cta =
    ctaLabel && ctaHref ? (
      <Link href={ctaHref} className="bnr__cta no-underline">
        {ctaLabel}
      </Link>
    ) : ctaLabel && onCtaClick ? (
      <button type="button" className="bnr__cta" onClick={onCtaClick}>
        {ctaLabel}
      </button>
    ) : null

  return (
    <article className={cn('bnr !w-full', `bnr--${variant}`, className)}>
      <div className="bnr__body">
        <div className="bnr__title">{title}</div>
        {message ? <div className="bnr__msg">{message}</div> : null}
        {children}
      </div>
      {cta}
    </article>
  )
}
