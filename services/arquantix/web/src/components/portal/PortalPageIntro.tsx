'use client'

import type { ReactNode } from 'react'
import { VEyebrow } from '@/components/design-system/vancelian/VEyebrow'
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
      <VEyebrow>{eyebrow}</VEyebrow>
      <h1 className="m-0 font-ui text-[28px] font-semibold tracking-v-tight text-v-fg sm:text-[32px]">
        {title}
      </h1>
      {description ? (
        <p className="m-0 max-w-2xl font-ui text-[16px] leading-relaxed text-v-fg-body">{description}</p>
      ) : null}
      {children}
    </header>
  )
}

export function PortalSectionHeading({
  title,
  action,
  className,
}: {
  title: string
  action?: ReactNode
  className?: string
}) {
  return (
    <div className={cn('flex items-end justify-between gap-4', className)}>
      <h2 className="m-0 font-ui text-[20px] font-semibold tracking-v-tight text-v-fg">{title}</h2>
      {action}
    </div>
  )
}
