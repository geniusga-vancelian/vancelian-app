'use client'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

function readUrlsText(content: Record<string, unknown>): string {
  const multi = content.promoVideoUrls
  if (Array.isArray(multi) && multi.length > 0) {
    return multi.map(String).join('\n')
  }
  return ''
}

export function VaultTitlePageModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const subtitle = readString(content.subtitle)
  const promoVideoUrl = readString(content.promoVideoUrl)
  const urlsText = readUrlsText(content)

  return (
    <div className="mt-2 space-y-2 border-t border-gray-100 pt-3">
      <p className="text-[11px] leading-snug text-indigo-900 bg-indigo-50/80 border border-indigo-100 rounded-md px-2.5 py-2">
        Bloc hero (titre + sous-titre). Les médias vidéo détaillés peuvent aussi être gérés via la carte produit /
        médias lorsque configuré.
      </p>
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre de section"
      />
      <input
        type="text"
        value={subtitle}
        onChange={(e) => onPatch({ subtitle: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Sous-titre (chapô)"
      />
      <input
        type="url"
        value={promoVideoUrl}
        onChange={(e) => onPatch({ promoVideoUrl: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-xs font-mono"
        placeholder="URL vidéo promo principale"
      />
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">
          Vidéos promo supplémentaires (une URL par ligne)
        </label>
        <textarea
          value={urlsText}
          onChange={(e) => {
            const lines = e.target.value
              .split(/\r?\n/)
              .map((s) => s.trim())
              .filter(Boolean)
            onPatch({
              promoVideoUrls: lines,
            })
          }}
          rows={3}
          className="w-full rounded-md border px-2 py-1.5 font-mono text-xs"
          placeholder={'https://…'}
        />
      </div>
    </div>
  )
}
