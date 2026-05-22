'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type LinkRow = { label: string; url: string }

function readLinks(content: Record<string, unknown>): LinkRow[] {
  const raw = content.links
  if (!Array.isArray(raw) || raw.length === 0) return [{ label: '', url: '' }]
  return raw.map((it) => {
    const o = it != null && typeof it === 'object' && !Array.isArray(it) ? (it as Record<string, unknown>) : {}
    return { label: readString(o.label), url: readString(o.url) }
  })
}

export function VaultSimpleMarkdownModuleEditor({ content, onPatch }: Props) {
  const moduleTitle = readString(content.moduleTitle)
  const markdown = readString(content.markdown)
  const links = readLinks(content)

  const setLinks = (next: LinkRow[]) => onPatch({ links: next })

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <input
        type="text"
        value={moduleTitle}
        onChange={(e) => onPatch({ moduleTitle: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre du bloc (facultatif)"
      />
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">Corps (Markdown)</label>
        <textarea
          value={markdown}
          onChange={(e) => onPatch({ markdown: e.target.value })}
          rows={10}
          className="w-full rounded-md border px-2 py-1.5 font-mono text-xs"
          placeholder={'Paragraphe **gras**, listes…'}
        />
      </div>

      <div>
        <p className="mb-1 text-xs font-medium text-gray-700">
          Liens sous le bloc <span className="font-normal text-gray-500">({links.length})</span>
        </p>
        <div className="space-y-1">
          {links.map((row, index) => (
            <div key={`lnk-${index}`} className="flex items-start gap-1">
              <input
                type="text"
                value={row.label}
                onChange={(e) => {
                  const next = [...links]
                  next[index] = { ...row, label: e.target.value }
                  setLinks(next)
                }}
                className="min-w-0 w-[40%] rounded border px-2 py-1 text-xs"
                placeholder="Libellé"
              />
              <input
                type="url"
                value={row.url}
                onChange={(e) => {
                  const next = [...links]
                  next[index] = { ...row, url: e.target.value }
                  setLinks(next)
                }}
                className="min-w-0 flex-1 rounded border px-2 py-1 text-xs font-mono"
                placeholder="https://"
              />
              <div className="flex shrink-0 items-center gap-0.5">
                <button
                  type="button"
                  disabled={index === 0}
                  title="Monter"
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                  onClick={() => {
                    if (index === 0) return
                    const next = [...links]
                    ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                    setLinks(next)
                  }}
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  disabled={index >= links.length - 1}
                  title="Descendre"
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                  onClick={() => {
                    if (index >= links.length - 1) return
                    const next = [...links]
                    ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                    setLinks(next)
                  }}
                >
                  <ArrowDown className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Retirer"
                  className="rounded p-1 text-red-600 hover:bg-red-50"
                  onClick={() =>
                    links.length <= 1
                      ? setLinks([{ label: '', url: '' }])
                      : setLinks(links.filter((_, i) => i !== index))
                  }
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() => setLinks([...links, { label: '', url: '' }])}
          className="mt-1 text-xs font-medium text-indigo-700 hover:text-indigo-900"
        >
          + Lien
        </button>
      </div>
    </div>
  )
}
