'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'
import { MediaTile } from '@/components/admin/MediaTile'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type VideoItem = {
  title: string
  posterMediaId?: string | null
  /** Rétrocompat : URL brute si pas d'ID médiathèque */
  posterImageUrl?: string
  videoUrl: string
  date?: string
}

function readItems(content: Record<string, unknown>): VideoItem[] {
  const raw = content.items
  if (!Array.isArray(raw)) return []
  return raw.map((it) => {
    const o = it != null && typeof it === 'object' ? (it as Record<string, unknown>) : {}
    const id =
      typeof o.posterMediaId === 'string' && o.posterMediaId.trim().length > 0
        ? o.posterMediaId.trim()
        : null
    return {
      title: readString(o.title),
      posterMediaId: id,
      posterImageUrl: readString(o.posterImageUrl),
      videoUrl: readString(o.videoUrl),
      date: readString(o.date),
    }
  })
}

function itemsToPatchPayload(items: VideoItem[]): unknown[] {
  return items.map((it) => {
    const row: Record<string, unknown> = {
      title: it.title,
      videoUrl: it.videoUrl,
    }
    if (it.date != null && String(it.date).length > 0) {
      row.date = it.date
    }
    if (it.posterMediaId) {
      row.posterMediaId = it.posterMediaId
    }
    if (!it.posterMediaId && it.posterImageUrl) {
      row.posterImageUrl = it.posterImageUrl
    }
    return row
  })
}

/**
 * Éditeur Vault Builder — bloc vidéos.
 * Données persistées identiques (`items[]` + `posterMediaId`) : seule l'UI a
 * été densifiée en cartes horizontales (poster vignette + champs à droite).
 */
export function VaultVideoBlockArticleModuleEditor({ content, onPatch }: Props) {
  const moduleTitle = readString(content.title)
  const items = readItems(content)

  const setItems = (next: VideoItem[]) => onPatch({ items: itemsToPatchPayload(next) })

  const move = (index: number, dir: -1 | 1) => {
    const j = index + dir
    if (j < 0 || j >= items.length) return
    const next = [...items]
    ;[next[index], next[j]] = [next[j], next[index]]
    setItems(next)
  }

  const updateItem = (index: number, patch: Partial<VideoItem>) => {
    const next = items.map((it, i) => (i === index ? { ...it, ...patch } : it))
    setItems(next)
  }

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index))
  }

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <input
        type="text"
        value={moduleTitle}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre du module (ex. Vidéos)"
      />

      <div>
        <p className="mb-1 text-xs font-medium text-gray-700">
          Vidéos <span className="font-normal text-gray-500">({items.length})</span>
        </p>
        <div className="space-y-1.5">
          {items.map((item, index) => (
            <div
              key={`video-card-${index}`}
              className="flex gap-2 rounded border border-gray-200 bg-white p-1.5"
            >
              <MediaTile
                size={80}
                mediaId={item.posterMediaId ?? ''}
                index={index}
                total={items.length}
                onChange={(newId) =>
                  updateItem(index, { posterMediaId: newId, posterImageUrl: '' })
                }
                onRemove={() => updateItem(index, { posterMediaId: null })}
                pickerKind="image"
                pickerTitle="Sélectionner un poster"
              />
              <div className="flex min-w-0 flex-1 flex-col gap-1">
                <input
                  type="text"
                  value={item.title}
                  onChange={(e) => updateItem(index, { title: e.target.value })}
                  className="w-full rounded border border-gray-200 px-2 py-1 text-sm font-medium"
                  placeholder="Titre de la vidéo"
                />
                <input
                  type="url"
                  value={item.videoUrl}
                  onChange={(e) => updateItem(index, { videoUrl: e.target.value })}
                  className="w-full rounded border border-gray-200 px-2 py-1 text-xs font-mono"
                  placeholder="https://www.youtube.com/watch?v=…"
                />
                <input
                  type="text"
                  value={item.date ?? ''}
                  onChange={(e) => updateItem(index, { date: e.target.value })}
                  className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
                  placeholder="Date / libellé (ex. 7 avril 2026)"
                />
                {!item.posterMediaId && item.posterImageUrl ? (
                  <p className="rounded border border-amber-100 bg-amber-50 px-2 py-0.5 text-[10px] text-amber-700">
                    URL legacy : {item.posterImageUrl.slice(0, 60)}
                    {item.posterImageUrl.length > 60 ? '…' : ''}
                  </p>
                ) : null}
              </div>
              <div className="flex shrink-0 flex-col items-center gap-0.5">
                <button
                  type="button"
                  title="Monter"
                  disabled={index === 0}
                  onClick={() => move(index, -1)}
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Descendre"
                  disabled={index >= items.length - 1}
                  onClick={() => move(index, 1)}
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                >
                  <ArrowDown className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Supprimer cette vidéo"
                  onClick={() => removeItem(index)}
                  className="rounded p-1 text-red-600 hover:bg-red-50"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
          <button
            type="button"
            onClick={() =>
              setItems([
                ...items,
                { title: 'Nouvelle vidéo', posterMediaId: null, videoUrl: '', date: '' },
              ])
            }
            className="text-xs font-medium text-indigo-700 hover:text-indigo-900"
          >
            + Ajouter une vidéo
          </button>
        </div>
      </div>
    </div>
  )
}
