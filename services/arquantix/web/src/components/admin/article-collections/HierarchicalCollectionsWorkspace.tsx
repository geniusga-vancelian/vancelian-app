'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Trash2, Eye, EyeOff, ArrowUp, ArrowDown, ImageIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { MediaPicker } from '@/components/admin/MediaPicker'
import { HelpCollectionIconPickerModal } from '@/components/admin/help/HelpCollectionIconPickerModal'
import { HelpCollectionLocaleFlagStrip } from '@/components/admin/help/HelpCollectionLocaleFlagStrip'
import { DSProjectCard, type Project } from '@/components/design-system/ProjetGallery/ProjetGallery'
import { computeHelpCollectionLocaleCompleteness } from '@/lib/admin/pageLocaleCompleteness'
import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'
import { adminMediaFileUrl } from '@/lib/admin/adminMediaFileUrl'
import { slugify } from '@/lib/utils/slugify'
import {
  ACADEMY_COLLECTION_ICON_OPTIONS,
  HIERARCHICAL_COLLECTIONS_CONFIG,
  collectionIconDisplay,
  type HierarchicalWorkspaceKind,
} from '@/config/hierarchicalCollectionsWorkspace'

interface CollectionI18n {
  id: string
  locale: string
  title: string
  subtitle?: string | null
  description?: string | null
  translationStatus: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
}

interface Collection {
  id: string
  slug: string
  iconKey: string
  colorHex: string
  coverMediaId?: string | null
  order: number
  isPublished: boolean
  i18n?: CollectionI18n[]
  _count?: {
    categories: number
    articles?: number
  }
}

/** Image de couverture DS carte projet — placeholder si aucun média en base. */
const HELP_COLLECTION_CARD_PLACEHOLDER_IMAGE =
  'data:image/svg+xml,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="800" height="440" viewBox="0 0 800 440"><rect fill="#e5e7eb" width="800" height="440"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#64748b" font-family="system-ui,sans-serif" font-size="18">Pas d'image</text></svg>`,
  )

function buildCollectionPreviewProject(
  collection: Collection,
  supportsCoverMedia: boolean,
): Project {
  const fr = collection.i18n?.find((i) => i.locale === defaultLocale)
  const anyTitle =
    fr?.title?.trim() ||
    collection.i18n?.find((i) => (i.title ?? '').trim().length > 0)?.title?.trim() ||
    collection.slug
  const subtitle = (fr?.subtitle ?? '').trim()
  const body = (fr?.description ?? '').trim() || subtitle || '—'
  const coverOk =
    supportsCoverMedia && collection.coverMediaId
      ? adminMediaFileUrl(collection.coverMediaId)
      : null

  return {
    id: collection.id,
    image: coverOk ?? HELP_COLLECTION_CARD_PLACEHOLDER_IMAGE,
    imageStatusLabel: '',
    /** Pas de surtitre type « Banque / compte » sur l’aperçu module Collections (corps carte uniquement). */
    infoTags: [],
    amount: '',
    title: anyTitle,
    description: body,
    fundedPercentage: 0,
    fundedText: '',
  }
}

function normalizeHexColor(value: string): string {
  const cleaned = value.trim().replace('#', '').toUpperCase()
  if (/^[0-9A-F]{6}$/.test(cleaned)) return `#${cleaned}`
  return '#0F172A'
}

/** Valeur contrôlée pour `<input type="color">` : évite de forcer #0F172A tant que l’hex tapé est incomplet. */
function hexForNativeColorInput(raw: string): string {
  const cleaned = raw.trim().replace(/^#/, '')
  if (/^[0-9A-Fa-f]{6}$/.test(cleaned)) {
    return `#${cleaned.toUpperCase()}`
  }
  return '#F4F4F5'
}

export function HierarchicalCollectionsWorkspace({
  workspace,
  compactHeader = false,
}: {
  workspace: HierarchicalWorkspaceKind
  compactHeader?: boolean
}) {
  const cfg = HIERARCHICAL_COLLECTIONS_CONFIG[workspace]
  const apiBase = cfg.apiBase
  const router = useRouter()
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(true)
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; collectionId: string | null }>({
    open: false,
    collectionId: null,
  })
  const [selectedCollectionId, setSelectedCollectionId] = useState<string | null>(null)
  const [i18nData, setI18nData] = useState<Record<string, Record<string, { title: string; subtitle: string; description: string }>>>({})
  const [i18nStatuses, setI18nStatuses] = useState<Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>>>({})
  const [showTranslateModal, setShowTranslateModal] = useState<string | null>(null)
  const [savingI18n, setSavingI18n] = useState<Record<string, boolean>>({})
  const [approving, setApproving] = useState<Record<string, string>>({})
  const [showAddModal, setShowAddModal] = useState(false)
  const [newCollection, setNewCollection] = useState({
    title: '',
    subtitle: '',
    slug: '',
    iconKey: cfg.defaultNewIconKey,
    colorHex: '#0F172A',
    coverMediaId: null as string | null,
    order: 0,
    isPublished: true,
  })
  const [creating, setCreating] = useState(false)
  const [checkingSlug, setCheckingSlug] = useState(false)
  const [styleSaving, setStyleSaving] = useState<Record<string, boolean>>({})
  const [iconPickerForId, setIconPickerForId] = useState<string | null>(null)
  const [iconPickerCreateOpen, setIconPickerCreateOpen] = useState(false)
  const [mediaPickerForId, setMediaPickerForId] = useState<string | null>(null)
  const [mediaPickerCreateOpen, setMediaPickerCreateOpen] = useState(false)

  const fetchCollections = async () => {
    setLoading(true)
    try {
      const response = await fetch(apiBase)
      if (!response.ok) {
        if (response.status === 401) {
          router.push('/admin/login')
          return
        }
        throw new Error('Failed to fetch collections')
      }

      const data = await response.json()
      setCollections(data.collections || [])

      // Initialize i18n data
      const i18nMap: Record<string, Record<string, { title: string; subtitle: string; description: string }>> = {}
      const statusMap: Record<string, Record<string, 'ORIGINAL' | 'MACHINE' | 'APPROVED'>> = {}

      data.collections.forEach((col: Collection) => {
        i18nMap[col.id] = {}
        statusMap[col.id] = {}
        col.i18n?.forEach((i18n) => {
          i18nMap[col.id][i18n.locale] = {
            title: i18n.title || '',
            subtitle: i18n.subtitle || '',
            description: i18n.description || '',
          }
          statusMap[col.id][i18n.locale] = i18n.translationStatus
        })
      })

      setI18nData(i18nMap)
      setI18nStatuses(statusMap)
      setSelectedCollectionId((id) => {
        const list = data.collections || []
        if (list.length === 0) return null
        if (id && list.some((c: Collection) => c.id === id)) return id
        return list[0].id
      })
    } catch (error) {
      console.error('Error fetching collections:', error)
      toastError('Failed to fetch collections')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCollections()
    // Intentionnel : re-fetch uniquement au montage ; `workspace` est fixe par instance.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleDelete = async (collectionId: string) => {
    try {
      const response = await fetch(`${apiBase}/${collectionId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to delete collection')
      }

      toastSuccess('Collection deleted successfully')
      fetchCollections()
    } catch (error: any) {
      console.error('Error deleting collection:', error)
      toastError(error.message || 'Failed to delete collection')
    } finally {
      setDeleteDialog({ open: false, collectionId: null })
    }
  }

  const handleTogglePublish = async (collection: Collection) => {
    try {
      const response = await fetch(`${apiBase}/${collection.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isPublished: !collection.isPublished }),
      })

      if (!response.ok) throw new Error('Failed to update collection')

      toastSuccess(`Collection ${!collection.isPublished ? 'published' : 'unpublished'}`)
      fetchCollections()
    } catch (error) {
      console.error('Error toggling publish:', error)
      toastError('Failed to update collection')
    }
  }

  const handleSaveI18n = async (collectionId: string, locale: string) => {
    setSavingI18n((prev) => ({ ...prev, [`${collectionId}-${locale}`]: true }))
    try {
      const data = i18nData[collectionId]?.[locale]
      if (!data) return

      const response = await fetch(`${apiBase}/${collectionId}/i18n`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locale,
          title: data.title,
          subtitle: data.subtitle || null,
          description: data.description || null,
        }),
      })

      if (!response.ok) throw new Error('Failed to save translation')

      toastSuccess('Translation saved')
      fetchCollections()
    } catch (error) {
      console.error('Error saving i18n:', error)
      toastError('Failed to save translation')
    } finally {
      setSavingI18n((prev) => ({ ...prev, [`${collectionId}-${locale}`]: false }))
    }
  }

  const handleApprove = async (collectionId: string, locale: string) => {
    setApproving((prev) => ({ ...prev, [`${collectionId}-${locale}`]: locale }))
    try {
      const response = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: cfg.approveEntityType,
          entityId: collectionId,
          locale,
        }),
      })

      if (!response.ok) throw new Error('Failed to approve translation')

      toastSuccess('Translation approved')
      fetchCollections()
    } catch (error) {
      console.error('Error approving translation:', error)
      toastError('Failed to approve translation')
    } finally {
      setApproving((prev) => {
        const newState = { ...prev }
        delete newState[`${collectionId}-${locale}`]
        return newState
      })
    }
  }

  const slugGenSeqRef = useRef(0)

  const generateUniqueSlug = async (baseSlug: string): Promise<string> => {
    const root = baseSlug.trim() || 'collection'
    const maxAttempts = 80

    for (let counter = 0; counter < maxAttempts; counter++) {
      const slug = counter === 0 ? root : `${root}-${counter}`
      const response = await fetch(
        `${apiBase}/check-slug?slug=${encodeURIComponent(slug)}`,
      )

      if (!response.ok) {
        throw new Error(
          `Vérification du slug impossible (HTTP ${response.status}). ${cfg.slugCheckErrorSuffix}`,
        )
      }

      const data = (await response.json()) as { exists?: boolean }
      if (!data.exists) return slug
    }

    throw new Error('Impossible de générer un slug unique.')
  }

  const handleTitleChange = async (title: string) => {
    const seq = ++slugGenSeqRef.current
    setNewCollection((prev) => ({ ...prev, title }))

    if (!title.trim()) {
      setNewCollection((prev) => ({ ...prev, slug: '' }))
      setCheckingSlug(false)
      return
    }

    setCheckingSlug(true)
    try {
      const baseSlug = slugify(title)
      const uniqueSlug = await generateUniqueSlug(baseSlug)
      if (slugGenSeqRef.current !== seq) return
      setNewCollection((prev) => ({ ...prev, slug: uniqueSlug }))
    } catch (error) {
      console.error('Error generating slug:', error)
      toastError(
        error instanceof Error ? error.message : 'Erreur lors de la génération du slug',
      )
    } finally {
      if (slugGenSeqRef.current === seq) {
        setCheckingSlug(false)
      }
    }
  }

  const handleCreate = async () => {
    if (!newCollection.title.trim()) {
      toastError('Title is required')
      return
    }

    if (!newCollection.slug.trim()) {
      toastError('Slug is required')
      return
    }

    setCreating(true)
    try {
      const response = await fetch(apiBase, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          slug: newCollection.slug,
          title: newCollection.title,
          subtitle: newCollection.subtitle || null,
          iconKey: newCollection.iconKey,
          colorHex: normalizeHexColor(newCollection.colorHex),
          ...(cfg.supportsCoverMedia ? { coverMediaId: newCollection.coverMediaId } : {}),
          order: newCollection.order,
          isPublished: newCollection.isPublished,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to create collection')
      }

      toastSuccess('Collection created successfully')
      setShowAddModal(false)
      setNewCollection({
        title: '',
        subtitle: '',
        slug: '',
        iconKey: cfg.defaultNewIconKey,
        colorHex: '#0F172A',
        coverMediaId: null,
        order: 0,
        isPublished: true,
      })
      fetchCollections()
    } catch (error: any) {
      console.error('Error creating collection:', error)
      toastError(error.message || 'Failed to create collection')
    } finally {
      setCreating(false)
    }
  }

  const handleMoveOrder = async (collectionId: string, direction: 'up' | 'down') => {
    const collection = collections.find((c) => c.id === collectionId)
    if (!collection) return

    const currentIndex = collections.findIndex((c) => c.id === collectionId)
    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1

    if (targetIndex < 0 || targetIndex >= collections.length) return

    const targetCollection = collections[targetIndex]
    const newOrder = targetCollection.order

    try {
      await fetch(`${apiBase}/${collectionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: newOrder }),
      })

      await fetch(`${apiBase}/${targetCollection.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ order: collection.order }),
      })

      fetchCollections()
    } catch (error) {
      console.error('Error moving collection:', error)
      toastError('Failed to reorder collection')
    }
  }

  const handleSaveStyle = async (collection: Collection) => {
    setStyleSaving((prev) => ({ ...prev, [collection.id]: true }))
    try {
      const response = await fetch(`${apiBase}/${collection.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          iconKey: collection.iconKey,
          colorHex: normalizeHexColor(collection.colorHex),
          ...(cfg.supportsCoverMedia ? { coverMediaId: collection.coverMediaId ?? null } : {}),
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to save style')
      }

      toastSuccess('Collection style saved')
      fetchCollections()
    } catch (error: any) {
      toastError(error.message || 'Failed to save style')
    } finally {
      setStyleSaving((prev) => ({ ...prev, [collection.id]: false }))
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div>
      {compactHeader ? (
        <div className="mb-4 flex justify-end">
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Ajouter une collection
          </Button>
        </div>
      ) : (
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold text-gray-900">Collections</h1>
          <Button onClick={() => setShowAddModal(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Add Collection
          </Button>
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold mb-4">Create Collection</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Title *
                </label>
                <input
                  type="text"
                  value={newCollection.title}
                  onChange={(e) => handleTitleChange(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="À propos de Shares"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={newCollection.subtitle}
                  onChange={(e) =>
                    setNewCollection({ ...newCollection, subtitle: e.target.value })
                  }
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                  placeholder="Petite description de la collection"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Slug {checkingSlug && <span className="text-xs text-gray-500">(generating...)</span>}
                </label>
                <input
                  type="text"
                  value={newCollection.slug}
                  onChange={(e) =>
                    setNewCollection({ ...newCollection, slug: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
                  placeholder="Auto-generated from title"
                  readOnly
                />
                <p className="text-xs text-gray-500 mt-1">Auto-generated and unique</p>
              </div>
              <div className="space-y-3 rounded-lg border border-gray-200 bg-gray-50 p-3">
                <p className="text-xs font-medium uppercase tracking-wide text-gray-600">
                  {cfg.styleBlocSubtitle}
                </p>
                {cfg.supportsCoverMedia ? (
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      {newCollection.coverMediaId ? (
                        <img
                          src={adminMediaFileUrl(newCollection.coverMediaId)}
                          alt=""
                          className="h-14 w-14 rounded-lg border border-gray-200 bg-white object-cover"
                        />
                      ) : (
                        <div className="flex h-14 w-14 items-center justify-center rounded-lg border border-dashed border-gray-300 bg-white text-gray-400">
                          <ImageIcon className="h-6 w-6" />
                        </div>
                      )}
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => setMediaPickerCreateOpen(true)}
                      >
                        Image
                      </Button>
                      {newCollection.coverMediaId ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="text-red-600"
                          onClick={() => setNewCollection({ ...newCollection, coverMediaId: null })}
                        >
                          Retirer
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ) : null}
                <div className="flex flex-wrap items-end gap-3">
                  <div>
                    <label className="mb-1 block text-xs font-medium text-gray-700">
                      {cfg.iconMode === 'help_ds' ? 'Icône DS' : 'Icône'}
                    </label>
                    {cfg.iconMode === 'help_ds' ? (
                      <Button
                        type="button"
                        variant="outline"
                        className="gap-2"
                        onClick={() => setIconPickerCreateOpen(true)}
                      >
                        {(() => {
                          const { Icon: IconCmp, label } = collectionIconDisplay(
                            workspace,
                            newCollection.iconKey,
                          )
                          return (
                            <>
                              <IconCmp className="h-4 w-4" />
                              <span className="text-sm">{label}</span>
                            </>
                          )
                        })()}
                      </Button>
                    ) : (
                      <select
                        className="w-full max-w-xs rounded-md border border-gray-300 px-2 py-2 text-sm"
                        value={newCollection.iconKey}
                        onChange={(e) =>
                          setNewCollection({ ...newCollection, iconKey: e.target.value })
                        }
                      >
                        {ACADEMY_COLLECTION_ICON_OPTIONS.map((o) => (
                          <option key={o.value} value={o.value}>
                            {o.label}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                  <div className="flex-1 min-w-[140px]">
                    <label className="block text-xs font-medium text-gray-700 mb-1">Couleur de fond (cartes)</label>
                    <div className="flex items-center gap-2">
                      <input
                        type="color"
                        value={hexForNativeColorInput(newCollection.colorHex)}
                        onChange={(e) =>
                          setNewCollection({ ...newCollection, colorHex: normalizeHexColor(e.target.value) })
                        }
                        className="w-10 h-10 border border-gray-300 rounded-md cursor-pointer"
                      />
                      <input
                        type="text"
                        value={newCollection.colorHex}
                        onChange={(e) => setNewCollection({ ...newCollection, colorHex: e.target.value })}
                        className="flex-1 px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
                      />
                    </div>
                  </div>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Order
                </label>
                <input
                  type="number"
                  value={newCollection.order}
                  onChange={(e) =>
                    setNewCollection({ ...newCollection, order: parseInt(e.target.value) || 0 })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                />
              </div>
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={newCollection.isPublished}
                  onChange={(e) =>
                    setNewCollection({ ...newCollection, isPublished: e.target.checked })
                  }
                  className="mr-2"
                />
                <label className="text-sm text-gray-700">Published</label>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-6">
              <Button variant="outline" onClick={() => setShowAddModal(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? 'Creating...' : 'Create'}
              </Button>
            </div>
          </div>
        </div>
      )}

      {collections.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg shadow border border-slate-100">
          <p className="text-gray-500">No collections yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="flex min-h-[min(760px,calc(100vh-11rem))] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm lg:flex-row lg:divide-x lg:divide-slate-200">
          {/* Liste compacte */}
          <div className="flex min-h-0 w-full min-w-0 flex-1 flex-col lg:w-1/2 lg:max-w-[50%]">
            <div className="overflow-auto">
              <table className="min-w-full divide-y divide-gray-200 text-sm">
                <thead className="sticky top-0 z-[1] bg-gray-50 shadow-[0_1px_0_0_rgb(229_231_235)]">
                  <tr>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Ordre
                    </th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Slug
                    </th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Titre (FR)
                    </th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Contenu
                    </th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Statut
                    </th>
                    <th className="px-3 py-2 text-left text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Langues
                    </th>
                    <th className="px-3 py-2 text-right text-[10px] font-semibold uppercase tracking-wide text-gray-500">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  {collections.map((collection) => {
                    const frI18n = collection.i18n?.find((i) => i.locale === 'fr')
                    const selected = collection.id === selectedCollectionId
                    const localeLevels = computeHelpCollectionLocaleCompleteness(collection)
                    return (
                      <tr
                        key={collection.id}
                        tabIndex={0}
                        aria-selected={selected}
                        onClick={() => setSelectedCollectionId(collection.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setSelectedCollectionId(collection.id)
                          }
                        }}
                        className={`cursor-pointer transition-colors hover:bg-slate-50/90 ${
                          selected ? 'bg-indigo-50/70 ring-1 ring-inset ring-indigo-200/80' : ''
                        }`}
                      >
                        <td className="whitespace-nowrap px-3 py-2 align-middle">
                          <div className="flex items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
                            <button
                              type="button"
                              onClick={() => handleMoveOrder(collection.id, 'up')}
                              disabled={collections.findIndex((c) => c.id === collection.id) === 0}
                              className="rounded p-0.5 hover:bg-gray-100 disabled:opacity-40"
                              aria-label="Monter"
                            >
                              <ArrowUp className="h-3.5 w-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => handleMoveOrder(collection.id, 'down')}
                              disabled={
                                collections.findIndex((c) => c.id === collection.id) ===
                                collections.length - 1
                              }
                              className="rounded p-0.5 hover:bg-gray-100 disabled:opacity-40"
                              aria-label="Descendre"
                            >
                              <ArrowDown className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        </td>
                        <td className="max-w-[140px] truncate px-3 py-2 align-middle font-mono text-xs text-gray-800">
                          {collection.slug}
                        </td>
                        <td className="max-w-[min(200px,28vw)] truncate px-3 py-2 align-middle text-xs text-gray-700">
                          {frI18n?.title || '—'}
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 align-middle text-xs text-gray-500">
                          {collection._count?.categories ?? 0} cat. · {collection._count?.articles ?? 0}{' '}
                          art.
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 align-middle" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => handleTogglePublish(collection)}
                            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                              collection.isPublished
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-700'
                            }`}
                          >
                            {collection.isPublished ? (
                              <>
                                <Eye className="mr-1 h-3 w-3" />
                                Publié
                              </>
                            ) : (
                              <>
                                <EyeOff className="mr-1 h-3 w-3" />
                                Brouillon
                              </>
                            )}
                          </button>
                        </td>
                        <td className="px-3 py-2 align-middle">
                          <HelpCollectionLocaleFlagStrip levels={localeLevels} />
                        </td>
                        <td className="whitespace-nowrap px-3 py-2 text-right align-middle" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => setDeleteDialog({ open: true, collectionId: collection.id })}
                            className="inline-flex rounded p-1 text-red-600 hover:bg-red-50 hover:text-red-800"
                            aria-label="Supprimer"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Détail + aperçu carte projet DS */}
          <div className="flex w-full min-w-0 flex-col border-t border-slate-200 bg-slate-50/95 lg:w-1/2 lg:max-w-[50%] lg:border-t-0">
            {(() => {
              const collection = collections.find((c) => c.id === selectedCollectionId)
              if (!collection) {
                return (
                  <div className="flex flex-1 items-center justify-center p-8 text-sm text-slate-500">
                    Sélectionnez une collection dans la liste.
                  </div>
                )
              }
              const previewProject = buildCollectionPreviewProject(collection, cfg.supportsCoverMedia)
              return (
                <div className="flex max-h-[min(920px,calc(100vh-8rem))] flex-1 flex-col gap-5 overflow-y-auto p-4 lg:p-5">
                  <div>
                    <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Aperçu — carte projet (DS)
                    </h2>
                    <p className="mt-0.5 text-[11px] leading-snug text-slate-600">
                      Rendu aligné sur la galerie projets : couverture, libellés et barre de pied (résumé contenus).
                    </p>
                    <div className="mx-auto mt-4 max-w-[420px]">
                      <DSProjectCard project={previewProject} preview hideFooter hideImageEyebrow />
                    </div>
                  </div>

                  <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                    <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                      Style &amp; couverture
                    </h3>
                    <div className="mt-3 flex flex-wrap items-start gap-3">
                      {cfg.supportsCoverMedia ? (
                      <div className="flex flex-wrap items-center gap-2">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        {collection.coverMediaId ? (
                          <button
                            type="button"
                            onClick={() => setMediaPickerForId(collection.id)}
                            className="shrink-0 overflow-hidden rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          >
                            <img
                              src={adminMediaFileUrl(collection.coverMediaId)}
                              alt=""
                              className="block h-14 w-14 bg-gray-100 object-cover"
                            />
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setMediaPickerForId(collection.id)}
                            className="flex h-14 w-14 shrink-0 items-center justify-center rounded-lg border border-dashed border-gray-300 text-gray-400 hover:bg-gray-50"
                          >
                            <ImageIcon className="h-6 w-6" />
                          </button>
                        )}
                        <Button type="button" variant="outline" size="sm" onClick={() => setMediaPickerForId(collection.id)}>
                          Média
                        </Button>
                        {collection.coverMediaId ? (
                          <button
                            type="button"
                            className="text-xs text-red-600 hover:underline"
                            onClick={() =>
                              setCollections((prev) =>
                                prev.map((c) =>
                                  c.id === collection.id ? { ...c, coverMediaId: null } : c,
                                ),
                              )
                            }
                          >
                            Retirer
                          </button>
                        ) : null}
                      </div>
                      ) : null}
                      {cfg.iconMode === 'help_ds' ? (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="gap-1.5"
                        onClick={() => setIconPickerForId(collection.id)}
                      >
                        {(() => {
                          const { Icon: IconCmp, label } = collectionIconDisplay(
                            workspace,
                            collection.iconKey,
                          )
                          return (
                            <>
                              <IconCmp className="h-4 w-4 shrink-0" />
                              <span className="max-w-[160px] truncate text-xs">{label}</span>
                            </>
                          )
                        })()}
                      </Button>
                      ) : (
                        <select
                          className="max-w-[220px] rounded-md border border-gray-300 px-2 py-2 text-xs"
                          value={collection.iconKey}
                          onChange={(e) =>
                            setCollections((prev) =>
                              prev.map((c) =>
                                c.id === collection.id ? { ...c, iconKey: e.target.value } : c,
                              ),
                            )
                          }
                        >
                          {ACADEMY_COLLECTION_ICON_OPTIONS.map((o) => (
                            <option key={o.value} value={o.value}>
                              {o.label}
                            </option>
                          ))}
                        </select>
                      )}
                      <div className="flex flex-wrap items-center gap-2">
                        <input
                          type="color"
                          value={hexForNativeColorInput(collection.colorHex)}
                          onChange={(e) =>
                            setCollections((prev) =>
                              prev.map((c) =>
                                c.id === collection.id
                                  ? { ...c, colorHex: normalizeHexColor(e.target.value) }
                                  : c,
                              ),
                            )
                          }
                          title="Couleur de fond"
                          className="h-9 w-9 shrink-0 cursor-pointer rounded border border-gray-300"
                        />
                        <input
                          type="text"
                          value={collection.colorHex}
                          onChange={(e) =>
                            setCollections((prev) =>
                              prev.map((c) =>
                                c.id === collection.id ? { ...c, colorHex: e.target.value } : c,
                              ),
                            )
                          }
                          className="w-24 rounded border border-gray-300 px-2 py-1 font-mono text-xs"
                          aria-label="Hex couleur"
                        />
                        <Button
                          type="button"
                          variant="secondary"
                          size="sm"
                          onClick={() => handleSaveStyle(collection)}
                          disabled={styleSaving[collection.id]}
                        >
                          {styleSaving[collection.id] ? '…' : 'Enregistrer le style'}
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div className="flex flex-wrap items-end justify-between gap-2">
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-600">
                          Traductions
                        </h3>
                        <HelpCollectionLocaleFlagStrip levels={computeHelpCollectionLocaleCompleteness(collection)} />
                      </div>
                      <p className="text-[10px] text-slate-500">
                        Vert = validé / source · Ambre = auto-trad · Rouge = manquant
                      </p>
                    </div>
                    <div className="space-y-3">
                      {supportedLocales.map((locale) => {
                        const data = i18nData[collection.id]?.[locale] || {
                          title: '',
                          subtitle: '',
                          description: '',
                        }
                        const status = i18nStatuses[collection.id]?.[locale] || 'ORIGINAL'
                        const isSaving = savingI18n[`${collection.id}-${locale}`]
                        const isApproving = approving[`${collection.id}-${locale}`] === locale

                        return (
                          <div key={locale} className="rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
                            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="text-xs font-semibold uppercase text-gray-800">{locale}</span>
                                <span
                                  className={`rounded px-2 py-0.5 text-[10px] font-medium ${
                                    status === 'ORIGINAL'
                                      ? 'bg-blue-100 text-blue-800'
                                      : status === 'MACHINE'
                                        ? 'bg-yellow-100 text-yellow-800'
                                        : 'bg-green-100 text-green-800'
                                  }`}
                                >
                                  {status}
                                </span>
                              </div>
                              <div className="flex flex-wrap gap-1.5">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => setShowTranslateModal(`${collection.id}::${locale}`)}
                                >
                                  Auto-translate
                                </Button>
                                {status === 'MACHINE' ? (
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => handleApprove(collection.id, locale)}
                                    disabled={isApproving}
                                  >
                                    {isApproving ? 'Approving...' : 'Approve'}
                                  </Button>
                                ) : null}
                                <Button
                                  size="sm"
                                  onClick={() => handleSaveI18n(collection.id, locale)}
                                  disabled={isSaving}
                                >
                                  {isSaving ? 'Saving...' : 'Save'}
                                </Button>
                              </div>
                            </div>
                            <div className="space-y-2">
                              <div>
                                <label className="mb-1 block text-[10px] font-medium text-gray-700">Title *</label>
                                <input
                                  type="text"
                                  value={data.title}
                                  onChange={(e) => {
                                    setI18nData((prev) => ({
                                      ...prev,
                                      [collection.id]: {
                                        ...prev[collection.id],
                                        [locale]: { ...data, title: e.target.value },
                                      },
                                    }))
                                  }}
                                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                                />
                              </div>
                              <div>
                                <label className="mb-1 block text-[10px] font-medium text-gray-700">Subtitle</label>
                                <input
                                  type="text"
                                  value={data.subtitle}
                                  onChange={(e) => {
                                    setI18nData((prev) => ({
                                      ...prev,
                                      [collection.id]: {
                                        ...prev[collection.id],
                                        [locale]: { ...data, subtitle: e.target.value },
                                      },
                                    }))
                                  }}
                                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                                />
                              </div>
                              <div>
                                <label className="mb-1 block text-[10px] font-medium text-gray-700">
                                  Description
                                </label>
                                <textarea
                                  value={data.description}
                                  onChange={(e) => {
                                    setI18nData((prev) => ({
                                      ...prev,
                                      [collection.id]: {
                                        ...prev[collection.id],
                                        [locale]: { ...data, description: e.target.value },
                                      },
                                    }))
                                  }}
                                  rows={2}
                                  className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm"
                                />
                              </div>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                </div>
              )
            })()}
          </div>
        </div>
      )}

      {cfg.iconMode === 'help_ds' ? (
      <HelpCollectionIconPickerModal
        open={iconPickerCreateOpen}
        onOpenChange={setIconPickerCreateOpen}
        value={newCollection.iconKey}
        onSelect={(key) => setNewCollection((prev) => ({ ...prev, iconKey: key }))}
      />
      ) : null}
      {cfg.supportsCoverMedia ? (
      <MediaPicker
        isOpen={mediaPickerCreateOpen}
        onClose={() => setMediaPickerCreateOpen(false)}
        onSelect={(media) => {
          setNewCollection((prev) => ({ ...prev, coverMediaId: media.id }))
          setMediaPickerCreateOpen(false)
        }}
        currentMediaId={newCollection.coverMediaId ?? undefined}
        title="Image de collection"
      />
      ) : null}

      {/* Pickers édition ligne */}
      {cfg.iconMode === 'help_ds' ? (
      <HelpCollectionIconPickerModal
        open={!!iconPickerForId}
        onOpenChange={(open) => {
          if (!open) setIconPickerForId(null)
        }}
        value={
          collections.find((c) => c.id === iconPickerForId)?.iconKey ?? cfg.defaultNewIconKey
        }
        onSelect={(key) => {
          if (!iconPickerForId) return
          setCollections((prev) =>
            prev.map((c) => (c.id === iconPickerForId ? { ...c, iconKey: key } : c)),
          )
        }}
      />
      ) : null}
      {cfg.supportsCoverMedia ? (
      <MediaPicker
        isOpen={!!mediaPickerForId}
        onClose={() => setMediaPickerForId(null)}
        onSelect={(media) => {
          if (!mediaPickerForId) return
          setCollections((prev) =>
            prev.map((c) => (c.id === mediaPickerForId ? { ...c, coverMediaId: media.id } : c)),
          )
          setMediaPickerForId(null)
        }}
        currentMediaId={
          collections.find((c) => c.id === mediaPickerForId)?.coverMediaId ?? undefined
        }
        title="Image de collection"
      />
      ) : null}

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={deleteDialog.open}
        onOpenChange={(open) =>
          setDeleteDialog({ open, collectionId: deleteDialog.collectionId })
        }
        title="Delete Collection"
        description="Are you sure you want to delete this collection? This action cannot be undone."
        onConfirm={() => {
          if (deleteDialog.collectionId) {
            handleDelete(deleteDialog.collectionId)
          }
        }}
      />

      {/* Translate Modal */}
      {showTranslateModal && (() => {
        const sep = showTranslateModal.indexOf('::')
        const collectionId = sep >= 0 ? showTranslateModal.slice(0, sep) : showTranslateModal
        const sourceLocale = (sep >= 0 ? showTranslateModal.slice(sep + 2) : defaultLocale) as Locale
        return (
        <TranslateModal
          open={!!showTranslateModal}
          onOpenChange={(open) => !open && setShowTranslateModal(null)}
          sourceLocale={sourceLocale}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch(cfg.translateApiPath, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                collectionId,
                sourceLocale,
                targetLocales,
                mode,
              }),
            })

            if (!response.ok) {
              const error = await response.json()
              throw new Error(error.error || 'Translation failed')
            }

            const data = await response.json()
            await fetchCollections()
            return data
          }}
        />
        )
      })()}
    </div>
  )
}

