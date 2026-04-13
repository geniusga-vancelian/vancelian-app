'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Boxes,
  DollarSign,
  FileText,
  Globe,
  Image as ImageIcon,
  Package,
  Pencil,
  Plus,
  Shield,
  Tag,
  Trash2,
  TrendingUp,
  type LucideIcon,
} from 'lucide-react'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import { MediaField } from '@/components/admin/MediaField'
import { Button } from '@/components/ui/button'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'

interface ThematicCategory {
  id: string
  slug: string
  label: string
  description: string | null
  imageUrl: string | null
  mediaId: string | null
  sortOrder: number
  imageResolved: string | null
}

interface InvestmentType {
  id: string
  slug: string
  label: string
  description: string | null
  colorHex: string
  iconKey: string
  sortOrder: number
}

const ICON_OPTIONS: Array<{ value: string; label: string; Icon: LucideIcon }> = [
  { value: 'trending-up', label: 'Trending up', Icon: TrendingUp },
  { value: 'boxes', label: 'Boxes', Icon: Boxes },
  { value: 'shield', label: 'Shield', Icon: Shield },
  { value: 'tag', label: 'Tag', Icon: Tag },
  { value: 'file-text', label: 'File text', Icon: FileText },
  { value: 'package', label: 'Package', Icon: Package },
  { value: 'globe', label: 'Globe', Icon: Globe },
  { value: 'dollar-sign', label: 'Dollar sign', Icon: DollarSign },
]

function iconByKey(iconKey: string): LucideIcon {
  const found = ICON_OPTIONS.find((i) => i.value === iconKey)
  return found?.Icon ?? Tag
}

function normalizeHexColor(value: string): string {
  const v = value.trim()
  if (!v) return '#6366F1'
  const withHash = v.startsWith('#') ? v : `#${v}`
  return /^#[0-9A-Fa-f]{6}$/.test(withHash) ? withHash.toUpperCase() : '#6366F1'
}

export default function AdminInvestmentCategoriesPage() {
  const router = useRouter()

  const [loading, setLoading] = useState(true)

  const [thematicCategories, setThematicCategories] = useState<ThematicCategory[]>([])
  const [thematicCreating, setThematicCreating] = useState(false)
  const [thematicEditingId, setThematicEditingId] = useState<string | null>(null)
  const [thematicDeleteId, setThematicDeleteId] = useState<string | null>(null)
  const [thematicDeleting, setThematicDeleting] = useState(false)
  const [thematicSaving, setThematicSaving] = useState(false)
  const [thematicLabel, setThematicLabel] = useState('')
  const [thematicDescription, setThematicDescription] = useState('')
  const [thematicMediaId, setThematicMediaId] = useState<string | null>(null)

  const [investmentTypes, setInvestmentTypes] = useState<InvestmentType[]>([])
  const [typeCreating, setTypeCreating] = useState(false)
  const [typeEditingId, setTypeEditingId] = useState<string | null>(null)
  const [typeDeleteId, setTypeDeleteId] = useState<string | null>(null)
  const [typeDeleting, setTypeDeleting] = useState(false)
  const [typeSaving, setTypeSaving] = useState(false)
  const [typeLabel, setTypeLabel] = useState('')
  const [typeDescription, setTypeDescription] = useState('')
  const [typeColorHex, setTypeColorHex] = useState('#6366F1')
  const [typeIconKey, setTypeIconKey] = useState('tag')

  const typePreviewIcon = useMemo(() => iconByKey(typeIconKey), [typeIconKey])

  const fetchThematicCategories = async () => {
    const res = await fetch('/api/admin/investment-categories')
    if (res.status === 401) {
      router.push('/admin/login')
      return
    }
    if (!res.ok) {
      throw new Error('Failed to fetch thematic categories')
    }
    const data = await res.json()
    setThematicCategories(data.categories ?? [])
  }

  const fetchInvestmentTypes = async () => {
    const res = await fetch('/api/admin/investment-types')
    if (res.status === 401) {
      router.push('/admin/login')
      return
    }
    if (!res.ok) {
      throw new Error('Failed to fetch investment types')
    }
    const data = await res.json()
    setInvestmentTypes(data.investmentTypes ?? [])
  }

  const fetchAll = async () => {
    try {
      await Promise.all([fetchThematicCategories(), fetchInvestmentTypes()])
    } catch (e) {
      console.error(e)
      toastError('Erreur lors du chargement des categories')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  const resetThematicForm = () => {
    setThematicLabel('')
    setThematicDescription('')
    setThematicMediaId(null)
  }

  const openThematicCreate = () => {
    setThematicCreating(true)
    setThematicEditingId(null)
    resetThematicForm()
  }

  const openThematicEdit = (item: ThematicCategory) => {
    setThematicCreating(false)
    setThematicEditingId(item.id)
    setThematicLabel(item.label)
    setThematicDescription(item.description ?? '')
    setThematicMediaId(item.mediaId ?? null)
  }

  const closeThematicForm = () => {
    setThematicCreating(false)
    setThematicEditingId(null)
    resetThematicForm()
  }

  const saveThematicCreate = async () => {
    if (!thematicLabel.trim()) {
      toastError('Le libelle est obligatoire')
      return
    }
    setThematicSaving(true)
    try {
      const res = await fetch('/api/admin/investment-categories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: thematicLabel.trim(),
          description: thematicDescription.trim() || null,
          mediaId: thematicMediaId,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        toastError(data.error || 'Erreur a la creation')
        return
      }
      toastSuccess('Thematic category creee')
      closeThematicForm()
      await fetchThematicCategories()
    } catch (e) {
      console.error(e)
      toastError('Erreur reseau')
    } finally {
      setThematicSaving(false)
    }
  }

  const saveThematicEdit = async () => {
    if (!thematicEditingId || !thematicLabel.trim()) return
    setThematicSaving(true)
    try {
      const res = await fetch(`/api/admin/investment-categories/${thematicEditingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: thematicLabel.trim(),
          description: thematicDescription.trim() || null,
          mediaId: thematicMediaId,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        toastError(data.error || 'Erreur a l enregistrement')
        return
      }
      toastSuccess('Thematic category enregistree')
      closeThematicForm()
      await fetchThematicCategories()
    } catch (e) {
      console.error(e)
      toastError('Erreur reseau')
    } finally {
      setThematicSaving(false)
    }
  }

  const deleteThematic = async (id: string) => {
    setThematicDeleting(true)
    try {
      const res = await fetch(`/api/admin/investment-categories/${id}`, { method: 'DELETE' })
      const data = await res.json()
      if (!res.ok) {
        toastError(data.error || 'Impossible de supprimer')
        return
      }
      toastSuccess('Thematic category supprimee')
      setThematicDeleteId(null)
      await fetchThematicCategories()
    } catch (e) {
      console.error(e)
      toastError('Erreur reseau')
    } finally {
      setThematicDeleting(false)
    }
  }

  const resetTypeForm = () => {
    setTypeLabel('')
    setTypeDescription('')
    setTypeColorHex('#6366F1')
    setTypeIconKey('tag')
  }

  const openTypeCreate = () => {
    setTypeCreating(true)
    setTypeEditingId(null)
    resetTypeForm()
  }

  const openTypeEdit = (item: InvestmentType) => {
    setTypeCreating(false)
    setTypeEditingId(item.id)
    setTypeLabel(item.label)
    setTypeDescription(item.description ?? '')
    setTypeColorHex(normalizeHexColor(item.colorHex))
    setTypeIconKey(item.iconKey || 'tag')
  }

  const closeTypeForm = () => {
    setTypeCreating(false)
    setTypeEditingId(null)
    resetTypeForm()
  }

  const saveTypeCreate = async () => {
    if (!typeLabel.trim()) {
      toastError('Le libelle est obligatoire')
      return
    }
    setTypeSaving(true)
    try {
      const res = await fetch('/api/admin/investment-types', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: typeLabel.trim(),
          description: typeDescription.trim() || null,
          colorHex: normalizeHexColor(typeColorHex),
          iconKey: typeIconKey,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        toastError(data.error || 'Erreur a la creation')
        return
      }
      toastSuccess('Investment type cree')
      closeTypeForm()
      await fetchInvestmentTypes()
    } catch (e) {
      console.error(e)
      toastError('Erreur reseau')
    } finally {
      setTypeSaving(false)
    }
  }

  const saveTypeEdit = async () => {
    if (!typeEditingId || !typeLabel.trim()) return
    setTypeSaving(true)
    try {
      const res = await fetch(`/api/admin/investment-types/${typeEditingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: typeLabel.trim(),
          description: typeDescription.trim() || null,
          colorHex: normalizeHexColor(typeColorHex),
          iconKey: typeIconKey,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        toastError(data.error || 'Erreur a l enregistrement')
        return
      }
      toastSuccess('Investment type enregistre')
      closeTypeForm()
      await fetchInvestmentTypes()
    } catch (e) {
      console.error(e)
      toastError('Erreur reseau')
    } finally {
      setTypeSaving(false)
    }
  }

  const deleteType = async (id: string) => {
    setTypeDeleting(true)
    try {
      const res = await fetch(`/api/admin/investment-types/${id}`, { method: 'DELETE' })
      const data = await res.json()
      if (!res.ok) {
        toastError(data.error || 'Impossible de supprimer')
        return
      }
      toastSuccess('Investment type supprime')
      setTypeDeleteId(null)
      await fetchInvestmentTypes()
    } catch (e) {
      console.error(e)
      toastError('Erreur reseau')
    } finally {
      setTypeDeleting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <span className="text-gray-500">Chargement...</span>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Category</h1>
        <p className="text-sm text-gray-500 mt-1">
          Manage thematic categories and investment types used by offers and projects.
        </p>
      </div>

      <section className="space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Thematic categories</h2>
            <p className="text-sm text-gray-500">Existing list used for offer themes (Real estate, Energy, etc.).</p>
          </div>
          {!thematicCreating && !thematicEditingId && (
            <Button onClick={openThematicCreate}>
              <Plus className="w-4 h-4 mr-2" />
              Add thematic category
            </Button>
          )}
        </div>

        {(thematicCreating || thematicEditingId) && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <h3 className="font-semibold text-gray-900">
              {thematicCreating ? 'New thematic category' : 'Edit thematic category'}
            </h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Label *</label>
              <input
                type="text"
                value={thematicLabel}
                onChange={(e) => setThematicLabel(e.target.value)}
                className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md"
                placeholder="ex. Real estate"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
              <textarea
                value={thematicDescription}
                onChange={(e) => setThematicDescription(e.target.value)}
                rows={2}
                className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div className="max-w-md">
              <MediaField
                label="Image (optional)"
                value={thematicMediaId}
                onChange={setThematicMediaId}
                allowClear
                preview
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={thematicCreating ? saveThematicCreate : saveThematicEdit} disabled={thematicSaving}>
                {thematicSaving ? 'Saving...' : thematicCreating ? 'Create' : 'Save'}
              </Button>
              <Button variant="outline" onClick={closeThematicForm} disabled={thematicSaving}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {thematicCategories.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No thematic categories yet.</p>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 w-20">Image</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Label</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Description</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {thematicCategories.map((item) => (
                  <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      {item.imageResolved ? (
                        <img
                          src={item.imageResolved}
                          alt=""
                          className="w-12 h-12 object-cover rounded border border-gray-200"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded border border-gray-200 bg-gray-100 flex items-center justify-center">
                          <ImageIcon className="w-5 h-5 text-gray-400" />
                        </div>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span className="font-medium text-gray-900">{item.label}</span>
                      <span className="text-gray-400 text-xs ml-2 font-mono">{item.slug}</span>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600 max-w-xs truncate">
                      {item.description || '—'}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={() => openThematicEdit(item)}
                        className="p-2 text-gray-500 hover:text-indigo-600"
                        title="Edit"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => setThematicDeleteId(item.id)}
                        className="p-2 text-gray-500 hover:text-red-600"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <section className="space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Investment Type</h2>
            <p className="text-sm text-gray-500">
              Manage investment type entries with dedicated color and icon.
            </p>
          </div>
          {!typeCreating && !typeEditingId && (
            <Button onClick={openTypeCreate}>
              <Plus className="w-4 h-4 mr-2" />
              Add investment type
            </Button>
          )}
        </div>

        {(typeCreating || typeEditingId) && (
          <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <h3 className="font-semibold text-gray-900">
              {typeCreating ? 'New investment type' : 'Edit investment type'}
            </h3>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Label *</label>
              <input
                type="text"
                value={typeLabel}
                onChange={(e) => setTypeLabel(e.target.value)}
                className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md"
                placeholder="ex. Crypto Assets"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
              <textarea
                value={typeDescription}
                onChange={(e) => setTypeDescription(e.target.value)}
                rows={2}
                className="w-full max-w-md px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Color</label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={normalizeHexColor(typeColorHex)}
                    onChange={(e) => setTypeColorHex(normalizeHexColor(e.target.value))}
                    className="w-12 h-10 border border-gray-300 rounded-md"
                  />
                  <input
                    type="text"
                    value={typeColorHex}
                    onChange={(e) => setTypeColorHex(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono"
                    placeholder="#6366F1"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Icon</label>
                <select
                  value={typeIconKey}
                  onChange={(e) => setTypeIconKey(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md"
                >
                  {ICON_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-200 bg-gray-50">
              {(() => {
                const Icon = typePreviewIcon
                return <Icon className="w-4 h-4" style={{ color: normalizeHexColor(typeColorHex) }} />
              })()}
              <span className="text-sm text-gray-700">{typeLabel.trim() || 'Preview label'}</span>
            </div>
            <div className="flex gap-2">
              <Button onClick={typeCreating ? saveTypeCreate : saveTypeEdit} disabled={typeSaving}>
                {typeSaving ? 'Saving...' : typeCreating ? 'Create' : 'Save'}
              </Button>
              <Button variant="outline" onClick={closeTypeForm} disabled={typeSaving}>
                Cancel
              </Button>
            </div>
          </div>
        )}

        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          {investmentTypes.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No investment type yet.</p>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200 bg-gray-50">
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700 w-24">Style</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Label</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-700">Description</th>
                  <th className="text-right py-3 px-4 text-sm font-medium text-gray-700">Actions</th>
                </tr>
              </thead>
              <tbody>
                {investmentTypes.map((item) => {
                  const Icon = iconByKey(item.iconKey)
                  const color = normalizeHexColor(item.colorHex)
                  return (
                    <tr key={item.id} className="border-b border-gray-100 hover:bg-gray-50">
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span
                            className="inline-flex items-center justify-center w-8 h-8 rounded-full border border-gray-200"
                            style={{ backgroundColor: `${color}1A` }}
                          >
                            <Icon className="w-4 h-4" style={{ color }} />
                          </span>
                          <span className="text-xs font-mono text-gray-500">{color}</span>
                        </div>
                      </td>
                      <td className="py-3 px-4">
                        <span className="font-medium text-gray-900">{item.label}</span>
                        <span className="text-gray-400 text-xs ml-2 font-mono">{item.slug}</span>
                      </td>
                      <td className="py-3 px-4 text-sm text-gray-600 max-w-xs truncate">
                        {item.description || '—'}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          type="button"
                          onClick={() => openTypeEdit(item)}
                          className="p-2 text-gray-500 hover:text-indigo-600"
                          title="Edit"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          onClick={() => setTypeDeleteId(item.id)}
                          className="p-2 text-gray-500 hover:text-red-600"
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </section>

      <AlertDialog open={thematicDeleteId !== null} onOpenChange={(open) => !open && setThematicDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogTitle>Delete this thematic category?</AlertDialogTitle>
          <AlertDialogDescription>
            Deletion is possible only when no project is still linked to this category.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => thematicDeleteId && deleteThematic(thematicDeleteId)}
              disabled={thematicDeleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {thematicDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={typeDeleteId !== null} onOpenChange={(open) => !open && setTypeDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogTitle>Delete this investment type?</AlertDialogTitle>
          <AlertDialogDescription>
            This will remove the entry from the investment type list.
          </AlertDialogDescription>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => typeDeleteId && deleteType(typeDeleteId)}
              disabled={typeDeleting}
              className="bg-red-600 hover:bg-red-700"
            >
              {typeDeleting ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
