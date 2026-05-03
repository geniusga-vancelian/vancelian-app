'use client'

/**
 * Rattachement Academy : collection + slug URL + tags catégorie (metadata JSON).
 * URL publique canonique : `/academy/[collection]/[academySlug]`.
 */

import { useEffect, useMemo, useState } from 'react'
import { slugify } from '@/lib/utils/slugify'
import { normalizeCollectionTagsList } from '@/lib/articles/collectionTags'

interface AcademyCollectionLite {
  id: string
  slug: string
  i18n: Array<{ locale: string; title: string }>
}

export interface AcademyHierarchyValue {
  academyCollectionId: string | null
  academySlug: string | null
  collectionTags: string[]
  allowAnchors: boolean
}

interface Props {
  value: AcademyHierarchyValue
  onChange: (next: AcademyHierarchyValue) => void
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

export default function AcademyHierarchyPicker({
  value,
  onChange,
  disabled,
  showErrors,
}: Props) {
  const [collections, setCollections] = useState<AcademyCollectionLite[]>([])
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
        const res = await fetch('/api/admin/academy/collections')
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
    () => collections.find((c) => c.id === value.academyCollectionId) || null,
    [collections, value.academyCollectionId],
  )

  const previewUrl =
    selectedCollection && value.academySlug
      ? `/academy/${selectedCollection.slug}/${value.academySlug}`
      : null

  const collectionMissing = showErrors && !value.academyCollectionId
  const slugMissing = showErrors && (!value.academySlug || value.academySlug.trim() === '')

  return (
    <div className="rounded border border-emerald-200 bg-emerald-50/40 p-3 space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-xs font-semibold text-emerald-900">Hiérarchie Academy</span>
        <span className="text-[10px] text-emerald-700">
          (collection + slug ; tags pour les sections sous la collection)
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 mb-1">Collection</label>
          <select
            disabled={disabled || loadingCollections}
            value={value.academyCollectionId || ''}
            onChange={(e) => {
              const nextId = e.target.value || null
              onChange({
                ...value,
                academyCollectionId: nextId,
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
          <label className="block text-xs font-medium text-gray-700 mb-1">Academy slug (URL)</label>
          <input
            type="text"
            disabled={disabled}
            value={value.academySlug || ''}
            onChange={(e) => {
              const normalized = slugify(e.target.value)
              onChange({ ...value, academySlug: normalized || null })
            }}
            placeholder="e.g. comprendre-les-actions"
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
            <p className="text-[11px] text-red-600 mt-0.5">Academy slug requis.</p>
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
          placeholder="ex. debutant, portefeuille"
          className="w-full px-2 py-1 text-sm border rounded border-gray-300"
          autoComplete="off"
          spellCheck={false}
        />
        <p className="mt-0.5 text-[10px] text-gray-500">
          Le premier tag définit la section principale sur la page collection.
        </p>
      </div>

      <div className="flex items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
          <input
            type="checkbox"
            disabled={disabled}
            checked={value.allowAnchors}
            onChange={(e) => onChange({ ...value, allowAnchors: e.target.checked })}
            className="rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
          />
          <span>Allow anchors (table of contents)</span>
        </label>
        {previewUrl && (
          <a
            href={previewUrl}
            target="_blank"
            rel="noreferrer"
            className="text-[11px] text-emerald-700 underline hover:text-emerald-900 truncate"
            title={previewUrl}
          >
            {previewUrl}
          </a>
        )}
      </div>
    </div>
  )
}
