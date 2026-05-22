'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type Row = {
  icon: string
  iconBackgroundColor: string
  category: string
  title: string
  description: string
}

function readRows(content: Record<string, unknown>): Row[] {
  const raw = content.rows
  if (!Array.isArray(raw) || raw.length === 0) {
    return [{ icon: '', iconBackgroundColor: '#1E88E5', category: 'content', title: '', description: '' }]
  }
  return raw.map((it) => {
    const o = it != null && typeof it === 'object' && !Array.isArray(it) ? (it as Record<string, unknown>) : {}
    const cat = readString(o.category)
    const safe =
      cat === 'content' || cat === 'work' || cat === 'note' || cat === 'success' || cat === 'danger'
        ? cat
        : 'content'
    return {
      icon: readString(o.icon),
      iconBackgroundColor: readString(o.iconBackgroundColor) || '#1E88E5',
      category: safe,
      title: readString(o.title),
      description: readString(o.description),
    }
  })
}

const CATEGORY_OPTIONS = [
  { value: 'content', label: 'Neutre (content)' },
  { value: 'work', label: 'Travail (jaune)' },
  { value: 'note', label: 'Note (bleu)' },
  { value: 'success', label: 'Succès (vert)' },
  { value: 'danger', label: 'Alerte (rouge)' },
]

export function VaultCompetitiveAdvantagesModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const rows = readRows(content)
  const setRows = (next: Row[]) => onPatch({ rows: next })

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre du bloc"
      />

      <div className="space-y-2">
        {rows.map((row, index) => (
          <div key={`adv-${index}`} className="rounded-lg border border-gray-200 bg-white p-2 space-y-1.5">
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-gray-500">#{index + 1}</span>
              <div className="ml-auto flex items-center gap-0.5">
                <button
                  type="button"
                  disabled={index === 0}
                  title="Monter"
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                  onClick={() => {
                    if (index === 0) return
                    const next = [...rows]
                    ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                    setRows(next)
                  }}
                >
                  <ArrowUp className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  disabled={index >= rows.length - 1}
                  title="Descendre"
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                  onClick={() => {
                    if (index >= rows.length - 1) return
                    const next = [...rows]
                    ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                    setRows(next)
                  }}
                >
                  <ArrowDown className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  title="Retirer"
                  className="rounded p-1 text-red-600 hover:bg-red-50"
                  onClick={() =>
                    rows.length <= 1
                      ? setRows([
                          {
                            icon: '',
                            iconBackgroundColor: '#1E88E5',
                            category: 'content',
                            title: '',
                            description: '',
                          },
                        ])
                      : setRows(rows.filter((_, i) => i !== index))
                  }
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </div>
            <div className="grid gap-1 sm:grid-cols-2">
              <input
                type="text"
                value={row.icon}
                onChange={(e) => {
                  const next = [...rows]
                  next[index] = { ...row, icon: e.target.value }
                  setRows(next)
                }}
                placeholder="Icône (Material Icons name)"
                className="rounded border px-2 py-1 text-xs font-mono"
              />
              <input
                type="text"
                value={row.iconBackgroundColor}
                onChange={(e) => {
                  const next = [...rows]
                  next[index] = { ...row, iconBackgroundColor: e.target.value }
                  setRows(next)
                }}
                placeholder="#couleur fond icône"
                className="rounded border px-2 py-1 text-xs font-mono"
              />
            </div>
            <select
              value={row.category}
              onChange={(e) => {
                const next = [...rows]
                next[index] = { ...row, category: e.target.value }
                setRows(next)
              }}
              className="w-full rounded border px-2 py-1 text-xs"
            >
              {CATEGORY_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
            <input
              type="text"
              value={row.title}
              onChange={(e) => {
                const next = [...rows]
                next[index] = { ...row, title: e.target.value }
                setRows(next)
              }}
              placeholder="Titre carte"
              className="w-full rounded border px-2 py-1 text-sm font-medium"
            />
            <textarea
              value={row.description}
              onChange={(e) => {
                const next = [...rows]
                next[index] = { ...row, description: e.target.value }
                setRows(next)
              }}
              placeholder="Description"
              rows={2}
              className="w-full rounded border px-2 py-1 text-xs"
            />
          </div>
        ))}
        <button
          type="button"
          onClick={() =>
            setRows([
              ...rows,
              { icon: 'star_rounded', iconBackgroundColor: '#1E88E5', category: 'content', title: '', description: '' },
            ])
          }
          className="text-xs font-medium text-indigo-700 hover:text-indigo-900"
        >
          + Carte avantage
        </button>
      </div>
    </div>
  )
}
