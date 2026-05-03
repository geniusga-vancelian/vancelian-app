'use client'

/**
 * Rattachement Help : collection + slug URL + tags catégorie (metadata JSON).
 * URL publique canonique : `/help/[collection]/[helpSlug]`.
 */

import { useEffect, useMemo, useState } from 'react'
import { slugify } from '@/lib/utils/slugify'
import { normalizeCollectionTagsList } from '@/lib/articles/collectionTags'

interface HelpCollectionLite {
  id: string
  slug: string
  i18n: Array<{ locale: string; title: string }>
}

export interface HelpHierarchyValue {
  helpCollectionId: string | null
  helpSlug: string | null
  /** Slugs de tags (regroupement sous la collection). */
  collectionTags: string[]
  allowAnchors: boolean
}

interface Props {
  value: HelpHierarchyValue
  onChange: (next: HelpHierarchyValue) => void
  disabled?: boolean
  showErrors?: boolean
}

function pickI18nTitle(
  rows: Array<{ locale: string; title: string }> | undefined,
  fallback: string,
): string {
  if (!rows || rows.length === 0) return fallback
  return (
    rows.find((r) => r.locale === 'fr')?.title ||
    rows.find((r) => r.locale === 'en')?.title ||
    rows[0]?.title ||
    fallback
  )
}

export default function HelpHierarchyPicker({
  value,
  onChange,
  disabled,
  showErrors,
}: Props) {
  const [collections, setCollections] = useState<HelpCollectionLite[]>([])
  const [loadingCollections, setLoadingCollections] = useState(true)
  const [tagsInput, setTagsInput] = useState(() => value.collectionTags.join(', '))

  useEffect(() => {
    setTagsInput(value.collectionTags.join(', '))
  }, [value.collectionTags])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoadingCollections(true)
      try {
        const res = await fetch('/api/admin/help/collections')
        if (!res.ok) return
        const data = await res.json()
        if (!cancelled && Array.isArray(data.collections)) {
          setCollections(data.collections)
        }
      } finally {
        if (!cancelled) setLoadingCollections(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  const selectedCollection = useMemo(
    () => collections.find((c) => c.id === value.helpCollectionId) || null,
    [collections, value.helpCollectionId],
  )

  const previewUrl =
    selectedCollection && value.helpSlug
      ? `/help/${selectedCollection.slug}/${value.helpSlug}`
      : null

  const collectionMissing = showErrors && !value.helpCollectionId
  const slugMissing = showErrors && (!value.helpSlug || value.helpSlug.trim() === '')

  return (
    <div className="rounded border border-indigo-200 bg-indigo-50/40 p-3 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-indigo-900">Hiérarchie Help</span>
        <span className="text-[10px] text-indigo-700">
          (collection + slug ; tags pour les sections sous la collection)
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Collection</label>
          <select
            disabled={disabled || loadingCollections}
            value={value.helpCollectionId || ''}
            onChange={(e) => {
              const nextId = e.target.value || null
              onChange({
                ...value,
                helpCollectionId: nextId,
              })
            }}
            className={`w-full px-2 py-1 text-sm border rounded bg-white ${
              collectionMissing ? 'border-red-400' : 'border-gray-300'
            }`}
          >
            <option value="">— Sélectionner —</option>
            {collections.map((c) => (
              <option key={c.id} value={c.id}>
                {pickI18nTitle(c.i18n, c.slug)} ({c.slug})
              </option>
            ))}
          </select>
          {collectionMissing && (
            <p className="text-[11px] text-red-600 mt-0.5">Collection requise.</p>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Help slug (URL)</label>
          <input
            type="text"
            disabled={disabled}
            value={value.helpSlug || ''}
            onChange={(e) => {
              const normalized = slugify(e.target.value)
              onChange({ ...value, helpSlug: normalized || null })
            }}
            placeholder="e.g. comment-deposer-des-fonds"
            className={`w-full px-2 py-1 text-sm border rounded ${
              slugMissing ? 'border-red-400' : 'border-gray-300'
            }`}
            autoComplete="off"
            spellCheck={false}
          />
          <p className="mt-0.5 text-[10px] text-gray-500">
            Auto-formaté en slug URL (lowercase, sans accent ni espace).
          </p>
          {slugMissing && (
            <p className="text-[11px] text-red-600 mt-0.5">Help slug requis.</p>
          )}
        </div>
      </div>

      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Tags catégorie (slugs, séparés par virgule)
        </label>
        <input
          type="text"
          disabled={disabled}
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          onBlur={() => {
            const parts = tagsInput.split(/[,;]+/).map((s) => s.trim())
            const normalized = normalizeCollectionTagsList(parts)
            onChange({ ...value, collectionTags: normalized })
            setTagsInput(normalized.join(', '))
          }}
          placeholder="ex. depot-retrait, securite"
          className="w-full px-2 py-1 text-sm border rounded border-gray-300"
          autoComplete="off"
          spellCheck={false}
        />
        <p className="mt-0.5 text-[10px] text-gray-500">
          Le premier tag définit la section principale sur la page collection ; les autres permettent le filtrage.
        </p>
      </div>

      <div className="flex items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.allowAnchors}
            onChange={(e) => onChange({ ...value, allowAnchors: e.target.checked })}
            className="rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
          />
          <span>Allow anchors (table of contents)</span>
        </label>
        {previewUrl && (
          <a
            href={previewUrl}
            target="_blank"
            rel="noreferrer"
            className="text-[11px] text-indigo-700 underline hover:text-indigo-900 truncate"
            title={previewUrl}
          >
            {previewUrl}
          </a>
        )}
      </div>
    </div>
  )
}
