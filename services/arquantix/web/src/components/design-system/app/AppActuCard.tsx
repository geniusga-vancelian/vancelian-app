import type { ComponentType, ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

type LinkLikeProps = {
  href: string
  className?: string
  children: ReactNode
}

type Props = {
  title: string
  meta: string
  href: string
  imageUrl?: string
  imageAlt?: string
  LinkComponent?: ComponentType<LinkLikeProps>
  className?: string
}

/** Carte Actu (image hero) — preview/26-cards-flash-actu. */
export function AppActuCard({
  title,
  meta,
  href,
  imageUrl,
  imageAlt = '',
  LinkComponent,
  className,
}: Props) {
  const LinkImpl = LinkComponent ?? Link
  return (
    <LinkImpl href={href} className={cn('actu-card', className)}>
      <div className="actu-card__img">
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={imageUrl} alt={imageAlt} />
        ) : (
          <KalaiIcon name="photo" size={32} className="opacity-60" />
        )}
      </div>
      <h3 className="actu-card__title">{title}</h3>
      <div className="actu-card__meta">
        <KalaiIcon name="timer" size={16} />
        <span>{meta}</span>
      </div>
    </LinkImpl>
  )
}
