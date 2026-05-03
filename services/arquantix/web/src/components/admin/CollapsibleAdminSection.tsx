'use client'

import { useState, type ReactNode } from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'

type Props = {
  /** Titre court de la section (ex. « Settings », « Header Content »). */
  title: string
  /** Résumé d'une ligne affiché à côté du titre quand replié (ex. « slug : foo · author : Bar »). */
  summary?: string
  /** Bloc à droite du header (ex. badge de validation, bouton inline). */
  headerActions?: ReactNode
  /** Icône à gauche du titre (composant lucide). */
  icon?: ReactNode
  /** Ouvert par défaut. Voir aussi `forceOpen` pour contrôle externe. */
  defaultOpen?: boolean
  /** Force l'état (utilisé pour « Tout déplier / replier »). */
  forceOpen?: boolean
  /** Notifié quand l'état change manuellement (chevron). */
  onOpenChange?: (open: boolean) => void
  className?: string
  bodyClassName?: string
  children: ReactNode
}

/**
 * Section admin pliable réutilisable. Pattern unifié : header sticky avec
 * chevron + titre + résumé + actions, body conditionnel. Toutes les sections
 * admin article (Settings, Header Media, Categories, Related, Editorial,
 * Documents, Header Content) utilisent ce composant pour densité et lisibilité.
 */
export function CollapsibleAdminSection({
  title,
  summary,
  headerActions,
  icon,
  defaultOpen = false,
  forceOpen,
  onOpenChange,
  className,
  bodyClassName,
  children,
}: Props) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen)
  const open = forceOpen ?? internalOpen

  const toggle = () => {
    const next = !open
    setInternalOpen(next)
    onOpenChange?.(next)
  }

  return (
    <div className={cn('rounded-lg border border-gray-200 bg-white shadow-sm', className)}>
      <div className="flex items-center gap-2 px-3 py-2">
        <button
          type="button"
          onClick={toggle}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
          aria-expanded={open}
        >
          <ChevronDown
            className={cn(
              'h-4 w-4 shrink-0 text-gray-500 transition-transform',
              !open && '-rotate-90',
            )}
          />
          {icon ? <span className="shrink-0 text-gray-500">{icon}</span> : null}
          <span className="shrink-0 text-sm font-semibold text-gray-900">{title}</span>
          {summary ? (
            <span className="min-w-0 flex-1 truncate text-xs text-gray-500" title={summary}>
              · {summary}
            </span>
          ) : null}
        </button>
        {headerActions ? (
          <div className="flex shrink-0 items-center gap-1">{headerActions}</div>
        ) : null}
      </div>
      {open ? (
        <div className={cn('border-t border-gray-100 p-3', bodyClassName)}>{children}</div>
      ) : null}
    </div>
  )
}
