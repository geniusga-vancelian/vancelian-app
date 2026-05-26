import type { ReactNode } from 'react'
import { AppSurfaceCard } from './AppSurfaceCard'

type Props = {
  title?: string
  action?: ReactNode
  emptyMessage?: string
  isEmpty?: boolean
  children: ReactNode
  className?: string
}

export function AppTxList({ title, action, emptyMessage, isEmpty, children, className }: Props) {
  return (
    <AppSurfaceCard title={title} action={action} stacked className={className}>
      {isEmpty && emptyMessage ? (
        <p className="m-0 px-4 py-6 v-body text-v-fg-muted">{emptyMessage}</p>
      ) : (
        <div>{children}</div>
      )}
    </AppSurfaceCard>
  )
}
