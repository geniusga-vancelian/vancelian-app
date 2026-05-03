'use client'

import { MediaTile } from '@/components/admin/MediaTile'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

function readIds(content: Record<string, unknown>): string[] {
  const raw = content.imageMediaIds
  if (!Array.isArray(raw)) return []
  return raw.filter((x): x is string => typeof x === 'string' && x.length > 0)
}

/**
 * Éditeur Vault Builder — carrousel d'images.
 * Données persistées identiques (`imageMediaIds: string[]`) : seule l'UI a été
 * compressée en grille horizontale de vignettes 64×64.
 */
export function VaultMediaCarouselModuleEditor({ content, onPatch }: Props) {
  const moduleTitle = readString(content.moduleTitle)
  const description = readString(content.description)
  const imageMediaIds = readIds(content)

  const setIds = (next: string[]) => onPatch({ imageMediaIds: next })

  const move = (index: number, dir: -1 | 1) => {
    const j = index + dir
    if (j < 0 || j >= imageMediaIds.length) return
    const next = [...imageMediaIds]
    ;[next[index], next[j]] = [next[j], next[index]]
    setIds(next)
  }

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <div className="grid gap-2 sm:grid-cols-2">
        <input
          type="text"
          value={moduleTitle}
          onChange={(e) => onPatch({ moduleTitle: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Titre du module (optionnel)"
        />
        <input
          type="text"
          value={description}
          onChange={(e) => onPatch({ description: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Description (optionnelle)"
        />
      </div>

      <div>
        <p className="mb-1 text-xs font-medium text-gray-700">
          Images <span className="font-normal text-gray-500">({imageMediaIds.length}) — survol pour réordonner / remplacer / retirer</span>
        </p>
        <div className="flex flex-wrap gap-2">
          {imageMediaIds.map((id, index) => (
            <MediaTile
              key={`${id}-${index}`}
              mediaId={id}
              index={index}
              total={imageMediaIds.length}
              onChange={(newId) => {
                const next = [...imageMediaIds]
                next[index] = newId
                setIds(next)
              }}
              onRemove={() => setIds(imageMediaIds.filter((_, i) => i !== index))}
              onMoveUp={() => move(index, -1)}
              onMoveDown={() => move(index, 1)}
              pickerKind="image"
              pickerTitle="Sélectionner une image"
            />
          ))}
          <MediaTile
            variant="add"
            onSelect={(newId) => setIds([...imageMediaIds, newId])}
            pickerKind="image"
            pickerTitle="Ajouter une image"
          />
        </div>
      </div>
    </div>
  )
}
