import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
}

/** Carte liste comptes — preview/67-card-account (multi-currency). */
export function AppAccountSummaryList({ children, className }: Props) {
  return <div className={cn('acct-summary', className)}>{children}</div>
}
