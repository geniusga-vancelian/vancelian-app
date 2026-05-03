'use client'

import { useEffect } from 'react'
import { PagePreviewPanel, type PagePreviewToolbarProps } from '@/components/admin/PagePreviewPanel'

type Props = {
  open: boolean
  title: string
  previewUrl: string
  onClose: () => void
  toolbar?: PagePreviewToolbarProps
  reloadEpoch?: number
}

/**
 * Aperçu plein écran / tiroir sur viewports étroits (masqué en lg+ quand la colonne split est utilisée).
 */
export function PagePreviewDrawer({
  open,
  title,
  previewUrl,
  onClose,
  toolbar,
  reloadEpoch = 0,
}: Props) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100] flex justify-end lg:hidden">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-[1px] transition-opacity"
        aria-label="Fermer l’aperçu"
        onClick={onClose}
      />
      <aside
        className="relative flex h-full w-full max-w-xl flex-col border-l border-slate-200 bg-white shadow-2xl animate-in slide-in-from-right duration-200"
        role="dialog"
        aria-modal="true"
        aria-label="Aperçu de la page"
      >
        <PagePreviewPanel
          title={title}
          previewUrl={previewUrl}
          onClose={onClose}
          toolbar={toolbar}
          className="h-full"
          reloadEpoch={reloadEpoch}
        />
      </aside>
    </div>
  )
}
