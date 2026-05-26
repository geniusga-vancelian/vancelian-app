import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
  /** Preview/83 variant A — lignes sans séparateurs. */
  seamless?: boolean
}

export function AppSettingsList({ children, className, seamless = false }: Props) {
  return (
    <div className={cn('stg-list', seamless && 'stg-list--seamless', className)}>{children}</div>
  )
}
