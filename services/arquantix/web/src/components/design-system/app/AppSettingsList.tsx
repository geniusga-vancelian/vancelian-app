import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

export function AppSettingsList({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn('stg-list', className)}>{children}</div>
}
