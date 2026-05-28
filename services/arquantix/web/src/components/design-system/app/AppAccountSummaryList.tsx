import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
}

/** Liste comptes — Webapp4 `.v-card--list`. */
export function AppAccountSummaryList({ children, className }: Props) {
  return <div className={cn('v-card v-card--list', className)}>{children}</div>
}
