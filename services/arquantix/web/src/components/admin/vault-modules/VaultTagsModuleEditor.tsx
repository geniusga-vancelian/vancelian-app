'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readTags(content: Record<string, unknown>): string[] {
  const raw = content.tags
  if (!Array.isArray(raw) || raw.length === 0) return ['']
  return raw.map((t) => (typeof t === 'string' ? t : ''))
}

export function VaultTagsModuleEditor({ content, onPatch }: Props) {
  const tags = readTags(content)
  const setTags = (next: string[]) => onPatch({ tags: next })

  return (
    <div className="mt-2 space-y-2 border-t border-gray-100 pt-3">
      <p className="text-[11px] text-gray-600">Une ligne = une pastille affichée dans le hero.</p>
      {tags.map((tag, index) => (
        <div key={`tag-${index}`} className="flex items-center gap-1">
          <input
            type="text"
            value={tag}
            onChange={(e) => {
              const next = [...tags]
              next[index] = e.target.value
              setTags(next)
            }}
            className="min-w-0 flex-1 rounded-md border px-2 py-1 text-sm"
            placeholder="Texte du tag"
          />
          <button
            type="button"
            title="Monter"
            disabled={index === 0}
            onClick={() => {
              if (index === 0) return
              const next = [...tags]
              ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
              setTags(next)
            }}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
          >
            <ArrowUp className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            title="Descendre"
            disabled={index >= tags.length - 1}
            onClick={() => {
              if (index >= tags.length - 1) return
              const next = [...tags]
              ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
              setTags(next)
            }}
            className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
          >
            <ArrowDown className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            title="Retirer"
            onClick={() =>
              tags.length <= 1 ? setTags(['']) : setTags(tags.filter((_, i) => i !== index))
            }
            className="rounded p-1 text-red-600 hover:bg-red-50"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() => setTags([...tags, ''])}
        className="text-xs font-medium text-indigo-700 hover:text-indigo-900"
      >
        + Tag
      </button>
    </div>
  )
}
