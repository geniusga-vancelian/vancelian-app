'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { useNavPending } from '@/components/site/NavPendingContext'

type Props = {
  children: React.ReactNode
  className?: string
}

/** Zone contenu : léger feedback visuel pendant une navigation SPA. */
export function SiteContentPending({ children, className }: Props) {
  const { isNavigating } = useNavPending()

  return (
    <div
      className={cn(
        'flex min-h-0 flex-col transition-opacity duration-150 ease-out',
        isNavigating && 'opacity-60',
        className,
      )}
      aria-busy={isNavigating || undefined}
    >
      {children}
    </div>
  )
}
