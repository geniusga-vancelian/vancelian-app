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
  LinkComponent?: ComponentType<LinkLikeProps>
  className?: string
}

/** Carte Flash (texte) — preview/26-cards-flash-actu. */
export function AppFlashCard({ title, meta, href, LinkComponent, className }: Props) {
  const LinkImpl = LinkComponent ?? Link
  return (
    <LinkImpl href={href} className={cn('flash-card', className)}>
      <h3 className="flash-card__title">{title}</h3>
      <div className="flash-card__meta">
        <KalaiIcon name="timer" size={16} />
        <span>{meta}</span>
      </div>
    </LinkImpl>
  )
}
