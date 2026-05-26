import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'

type Props = {
  children: ReactNode
  className?: string
  /** Titre barre supérieure (My accounts, Transactions, …). */
  title?: string
  action?: ReactNode
  /** Liste empilée avec séparateurs (pas de padding carte sur le corps). */
  stacked?: boolean
}

/** Carte surface produit — fond blanc, radius 8–12, ombre subtle (DS app). */
export function AppSurfaceCard({ children, className, title, action, stacked = false }: Props) {
  return (
    <article
      className={cn(
        stacked ? 'tx-list overflow-hidden' : 'card-simple overflow-hidden !w-full p-0',
        className,
      )}
    >
      {title ? (
        <header className="module-head">
          <h2 className="module-head__title">{title}</h2>
          {action ? <div className="shrink-0">{action}</div> : null}
        </header>
      ) : null}
      {children}
    </article>
  )
}
