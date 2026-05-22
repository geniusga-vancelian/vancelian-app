'use client'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

export function VaultBlogALaUneModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const limitRaw = content.limit
  const limit =
    typeof limitRaw === 'number'
      ? limitRaw
      : typeof limitRaw === 'string'
        ? Number.parseInt(limitRaw, 10) || 3
        : 3

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <p className="text-[11px] text-gray-600">
        Les cartes sont alimentées par les articles reliés au vault (Related → page). Contrôlez ici titre et nombre max.
      </p>
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre (ex. À la une)"
      />
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">Nombre d’articles</label>
        <input
          type="number"
          min={1}
          max={24}
          value={limit}
          onChange={(e) => {
            const n = Number.parseInt(e.target.value, 10)
            if (!Number.isFinite(n)) return
            onPatch({ limit: Math.min(24, Math.max(1, n)) })
          }}
          className="w-28 rounded-md border px-2 py-1.5 text-sm"
        />
      </div>
    </div>
  )
}

export function VaultTransactionLatestModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const limitRaw = content.limit
  const limit =
    typeof limitRaw === 'number'
      ? limitRaw
      : typeof limitRaw === 'string'
        ? Number.parseInt(limitRaw, 10) || 10
        : 10

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre"
      />
      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">Nombre de lignes</label>
        <input
          type="number"
          min={1}
          max={50}
          value={limit}
          onChange={(e) => {
            const n = Number.parseInt(e.target.value, 10)
            if (!Number.isFinite(n)) return
            onPatch({ limit: Math.min(50, Math.max(1, n)) })
          }}
          className="w-28 rounded-md border px-2 py-1.5 text-sm"
        />
      </div>
    </div>
  )
}

export function VaultPerformanceChartModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  return (
    <div className="mt-2 space-y-2 border-t border-gray-100 pt-3">
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre du graphique"
      />
    </div>
  )
}
