'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'
import { MediaTile } from '@/components/admin/MediaTile'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

type DocumentEntryDraft = {
  mediaId: string
  /** Nom affiché dans le tableau du site (vide = repli sur le nom de fichier média). */
  documentName: string
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

function readDocumentEntries(content: Record<string, unknown>): DocumentEntryDraft[] {
  if (Array.isArray(content.documentEntries)) {
    const out: DocumentEntryDraft[] = []
    for (const x of content.documentEntries) {
      if (x != null && typeof x === 'object' && !Array.isArray(x)) {
        const o = x as Record<string, unknown>
        const mediaId = typeof o.mediaId === 'string' ? o.mediaId.trim() : ''
        if (!mediaId) continue
        const documentName = typeof o.documentName === 'string' ? o.documentName : ''
        out.push({ mediaId, documentName })
      }
    }
    return out
  }
  const rawIds = content.documentMediaIds
  if (!Array.isArray(rawIds)) return []
  return rawIds
    .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    .map((mediaId) => ({ mediaId, documentName: '' }))
}

/**
 * Éditeur Vault Builder — liste de fichiers (médiathèque).
 * Données persistées identiques (`documentEntries: { mediaId, documentName }[]`) :
 * seule l'UI a été densifiée en lignes horizontales (vignette + nom inline).
 */
export function VaultDocumentsListModuleEditor({ content, onPatch }: Props) {
  const subtitle = readString(content.subtitle)
  const moduleTitle = readString(content.moduleTitle)
  const description = readString(content.description)
  const entries = readDocumentEntries(content)

  const setEntries = (next: DocumentEntryDraft[]) => onPatch({ documentEntries: next })

  const move = (index: number, dir: -1 | 1) => {
    const j = index + dir
    if (j < 0 || j >= entries.length) return
    const next = [...entries]
    ;[next[index], next[j]] = [next[j], next[index]]
    setEntries(next)
  }

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <div className="grid gap-2 sm:grid-cols-3">
        <input
          type="text"
          value={subtitle}
          onChange={(e) => onPatch({ subtitle: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Surtitre (ex. DOCUMENTS)"
        />
        <input
          type="text"
          value={moduleTitle}
          onChange={(e) => onPatch({ moduleTitle: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Titre du module"
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
          Documents <span className="font-normal text-gray-500">({entries.length})</span>
        </p>
        <div className="space-y-1.5">
          {entries.map((entry, index) => (
            <div
              key={`${entry.mediaId}-${index}`}
              className="flex items-center gap-2 rounded border border-gray-200 bg-white p-1.5"
            >
              <MediaTile
                size={48}
                mediaId={entry.mediaId}
                index={index}
                total={entries.length}
                onChange={(newId) => {
                  const next = [...entries]
                  next[index] = { ...next[index], mediaId: newId }
                  setEntries(next)
                }}
                onRemove={() => setEntries(entries.filter((_, i) => i !== index))}
                pickerKind="pdf"
                pickerTitle="Sélectionner un fichier"
              />
              <input
                type="text"
                value={entry.documentName}
                onChange={(e) => {
                  const next = [...entries]
                  next[index] = { ...next[index], documentName: e.target.value }
                  setEntries(next)
                }}
                className="min-w-0 flex-1 rounded border border-gray-200 px-2 py-1 text-sm"
                placeholder="Nom affiché — vide = nom de fichier"
              />
              <div className="flex shrink-0 items-center gap-0.5">
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
                  disabled={index >= entries.length - 1}
                  onClick={() => move(index, 1)}
                  className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                >
                  <ArrowDown className="h-3.5 w-3.5" />
                </button>
                <button
                  type="button"
                  title="Retirer"
                  onClick={() => setEntries(entries.filter((_, i) => i !== index))}
                  className="rounded p-1 text-red-600 hover:bg-red-50"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <MediaTile
              variant="add"
              size={48}
              onSelect={(newId) => setEntries([...entries, { mediaId: newId, documentName: '' }])}
              pickerKind="pdf"
              pickerTitle="Ajouter un fichier"
            />
            <span className="text-xs text-gray-500">Cliquer la tuile + pour ajouter un document</span>
          </div>
        </div>
      </div>
    </div>
  )
}
