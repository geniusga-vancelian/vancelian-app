'use client'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type ItemKey = 'progress' | 'apr' | 'target'

function readItems(content: Record<string, unknown>): Array<{ key: ItemKey; label: string; enabled: boolean }> {
  const raw = content.items
  const defaults: Array<{ key: ItemKey; label: string; enabled: boolean }> = [
    { key: 'progress', label: '', enabled: true },
    { key: 'apr', label: '', enabled: true },
    { key: 'target', label: '', enabled: true },
  ]
  if (!Array.isArray(raw)) return defaults

  const byKey = new Map<ItemKey, { label: string; enabled: boolean }>()
  for (const row of raw) {
    if (row == null || typeof row !== 'object' || Array.isArray(row)) continue
    const o = row as Record<string, unknown>
    const k = o.key
    if (k !== 'progress' && k !== 'apr' && k !== 'target') continue
    byKey.set(k as ItemKey, {
      label: readString(o.label),
      enabled: o.enabled !== false,
    })
  }
  return defaults.map((d) => ({
    key: d.key,
    label: byKey.get(d.key)?.label ?? '',
    enabled: byKey.get(d.key)?.enabled ?? true,
  }))
}

function readManual(content: Record<string, unknown>): { progressPct: number; rateDisplay: string; totalDisplay: string } {
  const m = content.manual
  if (!m || typeof m !== 'object' || Array.isArray(m)) {
    return { progressPct: 0, rateDisplay: '', totalDisplay: '' }
  }
  const o = m as Record<string, unknown>
  const pct = typeof o.progressPct === 'number' ? o.progressPct : Number(o.progressPct) || 0
  return {
    progressPct: Number.isFinite(pct) ? pct : 0,
    rateDisplay: readString(o.rateDisplay),
    totalDisplay: readString(o.totalDisplay),
  }
}

export function VaultFundingModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const footnote = readString(content.footnote)
  const displayModeRaw = readString(content.displayMode)
  const displayMode = displayModeRaw === 'manual' ? 'manual' : 'auto_product'
  const items = readItems(content)
  const manual = readManual(content)

  const persistItems = (next: typeof items) => {
    onPatch({
      items: next.map(({ key, label, enabled }) => ({ key, label, enabled })),
    })
  }

  const labelProgress: Record<ItemKey, string> = {
    progress: 'Progression',
    apr: 'Taux APR',
    target: 'Cible montant',
  }

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <p className="text-[11px] leading-snug text-gray-600">
        Mode <strong className="text-gray-800">auto</strong> : les valeurs viennent du moteur lending (page publique).{' '}
        <strong className="text-gray-800">Manuel</strong> : utilisez les champs ci‑dessous pour l’aperçu / hors moteur.
      </p>
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre du bloc (optionnel)"
      />

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">Mode d’affichage</label>
        <select
          value={displayMode}
          onChange={(e) => onPatch({ displayMode: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
        >
          <option value="auto_product">Automatique (produit lié)</option>
          <option value="manual">Manuel</option>
        </select>
      </div>

      {displayMode === 'manual' ? (
        <div className="grid gap-2 sm:grid-cols-3 rounded-md border border-gray-200 bg-gray-50/80 p-2">
          <div>
            <label className="text-[10px] font-medium uppercase text-gray-600">Progression %</label>
            <input
              type="number"
              min={0}
              max={100}
              step={1}
              value={manual.progressPct}
              onChange={(e) =>
                onPatch({
                  manual: {
                    ...manual,
                    progressPct: Number(e.target.value) || 0,
                  },
                })
              }
              className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
            />
          </div>
          <div>
            <label className="text-[10px] font-medium uppercase text-gray-600">Taux (texte)</label>
            <input
              type="text"
              value={manual.rateDisplay}
              onChange={(e) =>
                onPatch({
                  manual: { ...manual, rateDisplay: e.target.value },
                })
              }
              className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              placeholder="ex. 10,5 % APR"
            />
          </div>
          <div>
            <label className="text-[10px] font-medium uppercase text-gray-600">Cible / total</label>
            <input
              type="text"
              value={manual.totalDisplay}
              onChange={(e) =>
                onPatch({
                  manual: { ...manual, totalDisplay: e.target.value },
                })
              }
              className="mt-0.5 w-full rounded border px-2 py-1 text-sm"
              placeholder="ex. 250 000 €"
            />
          </div>
        </div>
      ) : null}

      <div>
        <p className="mb-1 text-xs font-medium text-gray-700">Tuiles métriques (libellés personnalisés)</p>
        <div className="space-y-1.5">
          {items.map((row, i) => (
            <div key={row.key} className="flex flex-wrap items-center gap-2 rounded border border-gray-200 bg-white px-2 py-1.5">
              <span className="w-28 shrink-0 text-xs font-medium text-gray-500">{labelProgress[row.key]}</span>
              <input
                type="text"
                value={row.label}
                onChange={(e) => {
                  const next = [...items]
                  next[i] = { ...row, label: e.target.value }
                  persistItems(next)
                }}
                className="min-w-0 flex-1 rounded border px-2 py-1 text-xs"
                placeholder="Libellé optionnel sur la carte"
              />
              <label className="inline-flex shrink-0 items-center gap-1 text-xs text-gray-700">
                <input
                  type="checkbox"
                  checked={row.enabled}
                  onChange={(e) => {
                    const next = [...items]
                    next[i] = { ...row, enabled: e.target.checked }
                    persistItems(next)
                  }}
                />
                Afficher
              </label>
            </div>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-gray-700">Note de bas de bloc (Markdown)</label>
        <textarea
          value={footnote}
          onChange={(e) => onPatch({ footnote: e.target.value })}
          rows={3}
          className="w-full rounded-md border px-2 py-1.5 text-xs"
          placeholder="Asterisque légal…"
        />
      </div>
    </div>
  )
}
