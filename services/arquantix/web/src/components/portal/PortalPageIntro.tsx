'use client'

import type { ReactNode } from 'react'
import { AppEyebrow } from '@/components/design-system/app/AppEyebrow'
import { PortalModuleTitleLink } from '@/components/portal/PortalModuleTitleLink'
import { cn } from '@/lib/utils'

type Props = {
  eyebrow: string
  title: string
  description?: string
  className?: string
  children?: ReactNode
}

export function PortalPageIntro({ eyebrow, title, description, className, children }: Props) {
  return (
    <header className={cn('flex flex-col gap-3', className)}>
      <AppEyebrow>{eyebrow}</AppEyebrow>
      <h1 className="v-h3 m-0 sm:text-[32px]">{title}</h1>
      {description ? (
        <p className="m-0 max-w-2xl font-ui text-[16px] leading-relaxed text-v-fg-body">{description}</p>
      ) : null}
      {children}
    </header>
  )
}

export function PortalSectionHeading({
  title,
  href,
  action,
  className,
}: {
  title: string
  /** Lien sur le titre — flèche → collée au libellé (pas d’action à droite). */
  href?: string
  action?: ReactNode
  className?: string
}) {
  if (href) {
    return <PortalModuleTitleLink href={href} title={title} size="lg" className={className} />
  }

  if (action) {
    return (
      <div className={cn('flex items-end justify-between gap-4', className)}>
        <h2 className="v-h4 m-0 font-semibold">{title}</h2>
        {action}
      </div>
    )
  }

  return (
    <h2 className={cn('m-0 font-ui text-[20px] font-semibold tracking-v-tight text-v-fg', className)}>
      {title}
    </h2>
  )
}
