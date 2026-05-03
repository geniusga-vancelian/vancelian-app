'use client'

import { Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { HELP_COLLECTION_DS_ICONS } from '@/config/helpCollectionDsIcons'
import { cn } from '@/lib/utils'

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  value: string
  onSelect: (key: string) => void
}

export function HelpCollectionIconPickerModal({
  open,
  onOpenChange,
  value,
  onSelect,
}: Props) {
  const [query, setQuery] = useState('')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return HELP_COLLECTION_DS_ICONS
    return HELP_COLLECTION_DS_ICONS.filter(
      (e) =>
        e.label.toLowerCase().includes(q) ||
        e.key.toLowerCase().includes(q),
    )
  }, [query])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col gap-0 p-0 overflow-hidden">
        <DialogHeader className="px-6 pt-6 pb-3 shrink-0 border-b border-gray-100">
          <DialogTitle>Icônes (design system)</DialogTitle>
          <p className="text-sm text-gray-500 font-normal pt-1">
            Sélectionnez une icône alignée avec le centre d’aide mobile (clé enregistrée :{' '}
            <code className="text-xs bg-gray-100 px-1 rounded">{value || '—'}</code>).
          </p>
          <div className="relative mt-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="search"
              placeholder="Rechercher par nom ou clé…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm"
            />
          </div>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto px-6 py-4">
          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2">
            {filtered.map(({ key, label, Icon }) => {
              const selected = key === value
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    onSelect(key)
                    onOpenChange(false)
                  }}
                  className={cn(
                    'flex flex-col items-center gap-1.5 p-3 rounded-xl border text-center transition-colors',
                    selected
                      ? 'border-indigo-600 bg-indigo-50 ring-2 ring-indigo-200'
                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50',
                  )}
                >
                  <Icon className="w-6 h-6 text-gray-900 shrink-0" aria-hidden />
                  <span className="text-[10px] leading-tight text-gray-600 line-clamp-2">
                    {label}
                  </span>
                </button>
              )
            })}
          </div>
          {filtered.length === 0 && (
            <p className="text-center text-sm text-gray-500 py-12">Aucune icône ne correspond.</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
