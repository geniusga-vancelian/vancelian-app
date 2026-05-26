import * as React from 'react'
import { cn } from '@/lib/utils'

export type AppCardVariant = 'simple' | 'warm'

export interface AppCardProps extends React.HTMLAttributes<HTMLElement> {
  variant?: AppCardVariant
  title?: string
  children: React.ReactNode
}

/** Carte produit webapp — fond blanc (`card-simple`) ou warm (`card-warm`). */
export function AppCard({ variant = 'simple', title, className, children, ...rest }: AppCardProps) {
  const Tag = 'article'
  return (
    <Tag
      {...rest}
      className={cn(variant === 'warm' ? 'card-warm' : 'card-simple', className)}
    >
      {title ? <p className="card-title m-0">{title}</p> : null}
      <div className="card-body">{children}</div>
    </Tag>
  )
}
