'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'

type Props = {
  moduleType: string
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type Card = { imageUrl: string; redirectUrl: string; title: string; description: string }

function readItems(content: Record<string, unknown>): Card[] {
  const raw = content.items
  if (!Array.isArray(raw) || raw.length === 0) {
    return [{ imageUrl: '', redirectUrl: '', title: '', description: '' }]
  }
  return raw.map((it) => {
    const o = it != null && typeof it === 'object' && !Array.isArray(it) ? (it as Record<string, unknown>) : {}
    return {
      imageUrl: readString(o.imageUrl),
      redirectUrl: readString(o.redirectUrl),
      title: readString(o.title),
      description: readString(o.description),
    }
  })
}

function cardsToPatch(cards: Card[]) {
  return cards.map((c) => ({
    imageUrl: c.imageUrl,
    redirectUrl: c.redirectUrl,
    title: c.title,
    description: c.description,
  }))
}

export function VaultMarketingModulesEditor({ moduleType, content, onPatch }: Props) {
  if (moduleType === 'MarktingCardLargePortrait') {
    const title = readString(content.title)
    const imageAssetPath = readString(content.imageAssetPath)
    const heightSize = readString(content.heightSize) || 'large'
    return (
      <div className="mt-2 space-y-2 border-t border-gray-100 pt-3">
        <input
          type="text"
          value={title}
          onChange={(e) => onPatch({ title: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Titre"
        />
        <input
          type="text"
          value={imageAssetPath}
          onChange={(e) => onPatch({ imageAssetPath: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-xs font-mono"
          placeholder="Chemin asset ou URL image"
        />
        <select
          value={heightSize}
          onChange={(e) => onPatch({ heightSize: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
        >
          <option value="large">Hauteur large</option>
          <option value="medium">Medium</option>
          <option value="small">Petit</option>
        </select>
      </div>
    )
  }

  const isSliding =
    moduleType === 'MarketingCardsSmallSlidingCarrousel_Portrait' ||
    moduleType === 'MarketingCardsSmallSlidingCarrousel_Paysage'
  const isPortrait = moduleType === 'MarketingCardsSmallSlidingCarrousel_Portrait'

  const title = readString(content.title)
  const items = readItems(content)
  const setItems = (next: Card[]) => onPatch({ items: cardsToPatch(next) })

  const carousel =
    typeof content.carousel === 'boolean' ? content.carousel : content.carousel === 'true'
  const showBullets =
    typeof content.showBullets === 'boolean' ? content.showBullets : content.showBullets !== false
  const visibleCardsCount =
    typeof content.visibleCardsCount === 'number'
      ? content.visibleCardsCount
      : Number(content.visibleCardsCount) || 1.2
  const cardAspectRatio = readString(content.cardAspectRatio) || '1:1'

  const heading =
    moduleType === 'MarketingCardsSmallCarouselModule'
      ? 'Cartes marketing (carousel)'
      : 'Cartes marketing (glissière)'

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <p className="text-[11px] text-gray-600">{heading} — ajoutez des cartes avec image, titre et lien.</p>
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre du bloc (optionnel)"
      />

      {isSliding ? (
        <div className="flex flex-wrap items-center gap-4 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs">
          <label className="inline-flex items-center gap-1.5 font-medium text-gray-700">
            <input
              type="checkbox"
              checked={carousel}
              onChange={(e) => onPatch({ carousel: e.target.checked })}
            />
            Carousel auto
          </label>
          <label className="inline-flex items-center gap-1.5 font-medium text-gray-700">
            <input
              type="checkbox"
              checked={showBullets}
              onChange={(e) => onPatch({ showBullets: e.target.checked })}
            />
            Points de navigation
          </label>
          {isPortrait ? (
            <>
              <label className="flex items-center gap-1 font-medium text-gray-700">
                Nb cartes visibles
                <input
                  type="number"
                  step={0.1}
                  value={visibleCardsCount}
                  onChange={(e) =>
                    onPatch({ visibleCardsCount: Number.parseFloat(e.target.value) || 1 })
                  }
                  className="w-24 rounded border px-2 py-1 font-mono"
                />
              </label>
              <label className="flex items-center gap-1 font-medium text-gray-700">
                Ratio
                <input
                  type="text"
                  value={cardAspectRatio}
                  onChange={(e) => onPatch({ cardAspectRatio: e.target.value })}
                  className="w-28 rounded border px-2 py-1 font-mono"
                  placeholder="1:1"
                />
              </label>
            </>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-2">
        {items.map((row, index) => (
          <div key={`mc-${index}`} className="rounded-lg border border-gray-200 bg-white p-2 space-y-1">
            <div className="flex items-start justify-between">
              <span className="text-[10px] font-semibold text-gray-400">Carte #{index + 1}</span>
              <div className="flex items-center gap-0.5">
                <button
                  type="button"
                  disabled={index === 0}
                  title="Monter"
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                  onClick={() => {
                    if (index === 0) return
                    const next = [...items]
                    ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                    setItems(next)
                  }}
                >
                  <ArrowUp className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  disabled={index >= items.length - 1}
                  title="Descendre"
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                  onClick={() => {
                    if (index >= items.length - 1) return
                    const next = [...items]
                    ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                    setItems(next)
                  }}
                >
                  <ArrowDown className="h-3 w-3" />
                </button>
                <button
                  type="button"
                  title="Retirer"
                  className="rounded p-1 text-red-600 hover:bg-red-50"
                  onClick={() =>
                    items.length <= 1
                      ? setItems([{ imageUrl: '', redirectUrl: '', title: '', description: '' }])
                      : setItems(items.filter((_, i) => i !== index))
                  }
                >
                  <X className="h-3 w-3" />
                </button>
              </div>
            </div>
            <input
              type="url"
              value={row.imageUrl}
              onChange={(e) => {
                const next = [...items]
                next[index] = { ...row, imageUrl: e.target.value }
                setItems(next)
              }}
              placeholder="URL image"
              className="w-full rounded border px-2 py-1 text-xs font-mono"
            />
            <input
              type="url"
              value={row.redirectUrl}
              onChange={(e) => {
                const next = [...items]
                next[index] = { ...row, redirectUrl: e.target.value }
                setItems(next)
              }}
              placeholder="URL cible au clic"
              className="w-full rounded border px-2 py-1 text-xs font-mono"
            />
            <input
              type="text"
              value={row.title}
              onChange={(e) => {
                const next = [...items]
                next[index] = { ...row, title: e.target.value }
                setItems(next)
              }}
              placeholder="Titre"
              className="w-full rounded border px-2 py-1 text-sm"
            />
            <textarea
              value={row.description}
              onChange={(e) => {
                const next = [...items]
                next[index] = { ...row, description: e.target.value }
                setItems(next)
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
            setItems([...items, { imageUrl: '', redirectUrl: '', title: '', description: '' }])
          }
          className="text-xs font-medium text-indigo-700 hover:text-indigo-900"
        >
          + Carte
        </button>
      </div>
    </div>
  )
}
