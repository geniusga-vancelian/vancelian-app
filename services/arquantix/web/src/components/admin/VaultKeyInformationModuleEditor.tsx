'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type Row = { label: string; value: string }

function readRows(content: Record<string, unknown>): Row[] {
  const raw = content.rows
  if (!Array.isArray(raw)) return [{ label: '', value: '' }]
  return raw.map((it) => {
    const o = it != null && typeof it === 'object' && !Array.isArray(it) ? (it as Record<string, unknown>) : {}
    return {
      label: readString(o.label),
      value: readString(o.value),
    }
  })
}

/**
 * Éditeur compact KeyInformationModule.
 * Données persistées identiques (`rows`, `ctaLabel`, `ctaHref`).
 */
export function VaultKeyInformationModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const ctaLabel = readString(content.ctaLabel)
  const ctaHref = readString(content.ctaHref)
  const rows = readRows(content)

  const setRows = (next: Row[]) => onPatch({ rows: next })

  const move = (index: number, dir: -1 | 1) => {
    const j = index + dir
    if (j < 0 || j >= rows.length) return
    const next = [...rows]
    ;[next[index], next[j]] = [next[j], next[index]]
    setRows(next)
  }

  return (
    <div className="mt-2 space-y-2 border-t border-gray-100 pt-3">
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre du module (ex. Informations clés)"
      />

      <div className="space-y-1">
        <p className="text-xs font-medium text-gray-700">
          Lignes <span className="font-normal text-gray-500">({rows.length})</span>
        </p>
        {rows.map((row, index) => (
          <div
            key={`row-${index}`}
            className="flex items-center gap-1 rounded border border-gray-200 bg-white p-1"
          >
            <input
              type="text"
              value={row.label}
              onChange={(e) => {
                const next = [...rows]
                next[index] = { ...row, label: e.target.value }
                setRows(next)
              }}
              className="min-w-0 flex-1 rounded border border-gray-200 px-2 py-1 text-xs"
              placeholder="Label"
            />
            <input
              type="text"
              value={row.value}
              onChange={(e) => {
                const next = [...rows]
                next[index] = { ...row, value: e.target.value }
                setRows(next)
              }}
              className="min-w-0 flex-1 rounded border border-gray-200 px-2 py-1 text-xs"
              placeholder="Valeur"
            />
            <div className="flex shrink-0 items-center gap-0.5">
              <button
                type="button"
                title="Monter"
                disabled={index === 0}
                onClick={() => move(index, -1)}
                className="rounded p-0.5 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
              >
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                title="Descendre"
                disabled={index >= rows.length - 1}
                onClick={() => move(index, 1)}
                className="rounded p-0.5 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
              >
                <ArrowDown className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                title="Retirer"
                onClick={() => setRows(rows.filter((_, i) => i !== index))}
                className="rounded p-0.5 text-red-600 hover:bg-red-50"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        ))}
        <button
          type="button"
          onClick={() => setRows([...rows, { label: '', value: '' }])}
          className="text-xs font-medium text-indigo-700 hover:text-indigo-900"
        >
          + Ligne
        </button>
      </div>

      <div className="grid gap-1.5 sm:grid-cols-2">
        <input
          type="text"
          value={ctaLabel}
          onChange={(e) => onPatch({ ctaLabel: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-xs"
          placeholder="CTA — libellé (optionnel)"
        />
        <input
          type="text"
          value={ctaHref}
          onChange={(e) => onPatch({ ctaHref: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-xs font-mono"
          placeholder="CTA — URL"
        />
      </div>
    </div>
  )
}
