import type { ReactNode } from 'react'
import { AppSurfaceCard } from './AppSurfaceCard'
import { cn } from '@/lib/utils'

type Props = {
  title?: string
  action?: ReactNode
  emptyMessage?: string
  isEmpty?: boolean
  children: ReactNode
  className?: string
}

export function AppDataList({ title, action, emptyMessage, isEmpty, children, className }: Props) {
  if (isEmpty && emptyMessage) {
    return (
      <article className={cn('card-simple !w-full p-8 text-center', className)}>
        <p className="m-0 v-body text-v-fg-muted">{emptyMessage}</p>
      </article>
    )
  }

  return (
    <AppSurfaceCard title={title} action={action} className={className}>
      <div className="list list--stacked">{children}</div>
    </AppSurfaceCard>
  )
}
