'use client'

type Props = {
  moduleType: 'HEADING' | 'PARAGRAPH' | 'QUOTE' | 'BULLET_LIST' | 'NUMBERED_LIST'
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readItems(content: Record<string, unknown>): string[] {
  const raw = content.items
  if (!Array.isArray(raw) || raw.length === 0) return ['']
  return raw.map((x) => (typeof x === 'string' ? x : String(x ?? '')))
}

/** PARAGRAPH : canon `content.text` ; repli `markdown` si confusion avec SimpleMarkdownContentModule. */
function readParagraphEditorText(c: Record<string, unknown>): string {
  const t = typeof c.text === 'string' ? c.text : ''
  if (t.trim().length > 0) return t
  return typeof c.markdown === 'string' ? c.markdown : ''
}

/**
 * Champs alignés sur les blocs blog (HEADING, PARAGRAPH, QUOTE, listes) — même JSON `content` que les articles.
 */
export function VaultBlogStyleModuleEditor({ moduleType, content, onPatch }: Props) {
  const text =
    moduleType === 'PARAGRAPH'
      ? readParagraphEditorText(content)
      : typeof content.text === 'string'
        ? content.text
        : ''
  const author = typeof content.author === 'string' ? content.author : ''
  const items = readItems(content)

  if (moduleType === 'HEADING') {
    return (
      <label className="block space-y-1">
        <span className="text-xs font-medium text-gray-600">Titre (intertitre)</span>
        <input
          type="text"
          value={text}
          onChange={(e) => onPatch({ text: e.target.value })}
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-lg font-semibold"
          placeholder="Sous-titre ou intertitre"
        />
      </label>
    )
  }

  if (moduleType === 'PARAGRAPH') {
    return (
      <label className="block space-y-1">
        <span className="text-xs font-medium text-gray-600">Paragraphe (Markdown)</span>
        <textarea
          value={text}
          onChange={(e) => onPatch({ text: e.target.value })}
          rows={6}
          className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm"
          placeholder="Texte — gras, italique, liens…"
        />
      </label>
    )
  }

  if (moduleType === 'QUOTE') {
    return (
      <div className="space-y-3">
        <label className="block space-y-1">
          <span className="text-xs font-medium text-gray-600">Citation</span>
          <textarea
            value={text}
            onChange={(e) => onPatch({ text: e.target.value })}
            rows={4}
            className="w-full rounded-md border border-gray-300 px-3 py-2 italic"
            placeholder="Texte de la citation"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-xs font-medium text-gray-600">Attribution</span>
          <input
            type="text"
            value={author}
            onChange={(e) => onPatch({ author: e.target.value })}
            className="w-full rounded-md border border-gray-300 px-3 py-2"
            placeholder="Auteur ou source"
          />
        </label>
      </div>
    )
  }

  if (moduleType === 'BULLET_LIST' || moduleType === 'NUMBERED_LIST') {
    const addLabel = moduleType === 'BULLET_LIST' ? '+ Ligne' : '+ Ligne'
    return (
      <div className="space-y-2">
        <span className="text-xs font-medium text-gray-600">
          {moduleType === 'BULLET_LIST' ? 'Liste à puces' : 'Liste numérotée'}
        </span>
        {items.map((item, i) => (
          <div key={i} className="flex gap-2">
            <input
              type="text"
              value={item}
              onChange={(e) => {
                const next = [...items]
                next[i] = e.target.value
                onPatch({ items: next })
              }}
              className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm"
              placeholder={`Élément ${i + 1}`}
            />
            {items.length > 1 ? (
              <button
                type="button"
                className="shrink-0 rounded border border-gray-200 px-2 text-xs text-red-600 hover:bg-red-50"
                onClick={() => {
                  const next = items.filter((_, j) => j !== i)
                  onPatch({ items: next.length ? next : [''] })
                }}
              >
                ✕
              </button>
            ) : null}
          </div>
        ))}
        <button
          type="button"
          className="text-xs font-medium text-indigo-600 hover:underline"
          onClick={() => onPatch({ items: [...items, ''] })}
        >
          {addLabel}
        </button>
      </div>
    )
  }

  return null
}
