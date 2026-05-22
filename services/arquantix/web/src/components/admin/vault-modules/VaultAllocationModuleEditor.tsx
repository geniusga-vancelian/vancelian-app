'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type Slice = { label: string; percentage: number; colorHex: string }

function readSlices(content: Record<string, unknown>): Slice[] {
  const raw = content.slices
  if (!Array.isArray(raw) || raw.length === 0) {
    return [{ label: '', percentage: 0, colorHex: '#6B7280' }]
  }
  return raw.map((sl) => {
    const o = sl != null && typeof sl === 'object' && !Array.isArray(sl) ? (sl as Record<string, unknown>) : {}
    const pct = typeof o.percentage === 'number' ? o.percentage : Number(o.percentage) || 0
    return {
      label: readString(o.label),
      percentage: Number.isFinite(pct) ? pct : 0,
      colorHex: readString(o.colorHex) || '#6B7280',
    }
  })
}

export function VaultAllocationModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const introText = readString(content.introText)
  const sizeRaw = readString(content.size)
  const size = sizeRaw === 'compact' ? 'compact' : 'large'
  const slices = readSlices(content)
  const setSlices = (next: Slice[]) => onPatch({ slices: next })

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre"
      />
      <textarea
        value={introText}
        onChange={(e) => onPatch({ introText: e.target.value })}
        rows={3}
        className="w-full rounded-md border px-2 py-1.5 text-xs"
        placeholder="Texte d’introduction"
      />
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">Taille visuelle</label>
        <select
          value={size}
          onChange={(e) => onPatch({ size: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
        >
          <option value="large">Large</option>
          <option value="compact">Compact</option>
        </select>
      </div>

      <div>
        <p className="mb-1 text-xs font-medium text-gray-700">Parts ({slices.length})</p>
        <div className="space-y-1.5">
          {slices.map((slice, index) => (
            <div
              key={`sl-${index}`}
              className="flex flex-wrap items-center gap-2 rounded border border-gray-200 bg-white p-2"
            >
              <input
                type="text"
                value={slice.label}
                onChange={(e) => {
                  const next = [...slices]
                  next[index] = { ...slice, label: e.target.value }
                  setSlices(next)
                }}
                className="min-w-[8rem] flex-1 rounded border px-2 py-1 text-xs"
                placeholder="Libellé"
              />
              <input
                type="number"
                step={0.1}
                value={slice.percentage}
                onChange={(e) => {
                  const next = [...slices]
                  next[index] = { ...slice, percentage: Number(e.target.value) || 0 }
                  setSlices(next)
                }}
                className="w-24 rounded border px-2 py-1 text-xs"
                placeholder="%"
              />
              <input
                type="text"
                value={slice.colorHex}
                onChange={(e) => {
                  const next = [...slices]
                  next[index] = { ...slice, colorHex: e.target.value }
                  setSlices(next)
                }}
                className="w-[7rem] rounded border px-2 py-1 font-mono text-xs"
                placeholder="#hex"
              />
              <button
                type="button"
                disabled={index === 0}
                className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                onClick={() => {
                  if (index === 0) return
                  const next = [...slices]
                  ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                  setSlices(next)
                }}
              >
                <ArrowUp className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                disabled={index >= slices.length - 1}
                className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                onClick={() => {
                  if (index >= slices.length - 1) return
                  const next = [...slices]
                  ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                  setSlices(next)
                }}
              >
                <ArrowDown className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                title="Retirer"
                className="rounded p-1 text-red-600 hover:bg-red-50"
                onClick={() =>
                  slices.length <= 1
                    ? setSlices([{ label: '', percentage: 0, colorHex: '#6B7280' }])
                    : setSlices(slices.filter((_, i) => i !== index))
                }
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setSlices([...slices, { label: '', percentage: 0, colorHex: '#9CA3AF' }])}
          className="mt-1 text-xs font-medium text-indigo-700 hover:text-indigo-900"
        >
          + Part
        </button>
      </div>
    </div>
  )
}
