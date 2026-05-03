'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { defaultLocale, type Locale } from '@/config/locales'
import { Plus } from 'lucide-react'

const LOCALE_LABELS: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  readOnly?: boolean
  onCreated?: () => void | Promise<void>
}

/**
 * Création d’un bouton zone droite (menu primaire) — ouverte depuis la structure du site.
 */
export function AddPrimaryNavButtonDialog({
  open,
  onOpenChange,
  readOnly = false,
  onCreated,
}: Props) {
  const [adding, setAdding] = useState(false)
  const [newLabel, setNewLabel] = useState('')
  const [newUrl, setNewUrl] = useState('')
  const [newStyle, setNewStyle] = useState<'primary' | 'secondary'>('primary')

  const handleAdd = async () => {
    if (readOnly) return
    const label = newLabel.trim()
    if (!label) {
      toastError('Indiquez un libellé')
      return
    }
    setAdding(true)
    try {
      const res = await fetch('/api/admin/menus/primary/items', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label,
          type: 'BUTTON',
          enabled: true,
          buttonStyle: newStyle,
          externalUrl: newUrl.trim() || null,
          buttonAction: null,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Création impossible')
      toastSuccess('Bouton ajouté')
      setNewLabel('')
      setNewUrl('')
      setNewStyle('primary')
      onOpenChange(false)
      await onCreated?.()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setAdding(false)
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        onOpenChange(v)
        if (!v) {
          setNewLabel('')
          setNewUrl('')
          setNewStyle('primary')
        }
      }}
    >
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Ajouter un bouton menu</DialogTitle>
          <DialogDescription>
            Bouton à droite du menu (ex. Connexion, S’inscrire). Libellé de référence en{' '}
            <strong>{LOCALE_LABELS[defaultLocale]}</strong> ; traduisez ensuite via « Éditer » sur la ligne dans la
            structure du site.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-3 py-2">
          <label className="text-sm">
            <span className="mb-1 block font-medium text-gray-700">Libellé ({LOCALE_LABELS[defaultLocale]})</span>
            <input
              type="text"
              value={newLabel}
              disabled={readOnly}
              onChange={(e) => setNewLabel(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium text-gray-700">Lien (URL)</span>
            <input
              type="text"
              value={newUrl}
              disabled={readOnly}
              placeholder="/inscription ou https://…"
              onChange={(e) => setNewUrl(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
            />
          </label>
          <label className="text-sm">
            <span className="mb-1 block font-medium text-gray-700">Style</span>
            <select
              value={newStyle}
              disabled={readOnly}
              onChange={(e) => setNewStyle(e.target.value as 'primary' | 'secondary')}
              className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="primary">Primary (plein)</option>
              <option value="secondary">Secondary (contour)</option>
            </select>
          </label>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
            Annuler
          </Button>
          <Button type="button" disabled={readOnly || adding} onClick={() => void handleAdd()}>
            <Plus className="mr-1 h-4 w-4" />
            Ajouter
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
