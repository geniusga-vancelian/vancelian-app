'use client'

import { useEffect, useMemo, useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { slugify, isValidSlug } from '@/lib/utils/slugify'
import type { SiteTreeNode } from '@/lib/cms/buildSiteTree'

interface CreatePageModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
  /** Arborescence admin (même source que la page Pages). */
  siteTree: SiteTreeNode[] | null
  siteTreeLoading: boolean
}

function collectParentPageOptions(
  nodes: SiteTreeNode[],
  depth = 0,
): Array<{ id: string; label: string }> {
  const out: Array<{ id: string; label: string }> = []
  for (const n of nodes) {
    if (n.isVirtual) {
      if (n.children.length) out.push(...collectParentPageOptions(n.children, depth))
      continue
    }
    const name = n.title?.trim() || n.slug
    const indent = depth > 0 ? `${'\u2014 '.repeat(depth)}` : ''
    out.push({ id: n.id, label: `${indent}${name}` })
    out.push(...collectParentPageOptions(n.children, depth + 1))
  }
  return out
}

export function CreatePageModal({
  isOpen,
  onClose,
  onSuccess,
  siteTree,
  siteTreeLoading,
}: CreatePageModalProps) {
  const [template, setTemplate] = useState('homepage')
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')
  const [autoSlug, setAutoSlug] = useState(true)
  /** null = racine CMS (entrée menu primaire créée côté API, sauf home/blog). */
  const [parentId, setParentId] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const parentOptions = useMemo(
    () => (siteTree?.length ? collectParentPageOptions(siteTree) : []),
    [siteTree],
  )

  useEffect(() => {
    if (!isOpen) return
    setParentId(null)
    setError(null)
  }, [isOpen])

  if (!isOpen) return null

  const handleTitleChange = (value: string) => {
    setTitle(value)
    if (autoSlug) {
      setSlug(slugify(value))
    }
  }

  const handleSlugChange = (value: string) => {
    setSlug(value.toLowerCase())
    setAutoSlug(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!slug.trim()) {
      setError('Le slug est obligatoire')
      setLoading(false)
      return
    }

    if (!isValidSlug(slug)) {
      setError('Slug invalide : minuscules, chiffres et tirets uniquement (max. 60 caractères)')
      setLoading(false)
      return
    }

    try {
      const response = await fetch('/api/admin/pages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template,
          title: title.trim() || undefined,
          slug: slug.trim(),
          description: description.trim() || undefined,
          parentId,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Échec de la création')
      }

      const data = await response.json()
      onSuccess()
      onClose()
      setTitle('')
      setSlug('')
      setDescription('')
      setAutoSlug(true)
      setParentId(null)
      setError(null)
      window.location.href = `/admin/pages/${data.page.slug}`
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Échec de la création')
    } finally {
      setLoading(false)
    }
  }

  const atRoot = parentId === null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-lg bg-white shadow-xl">
        <div className="flex items-center justify-between border-b p-6">
          <h2 className="text-xl font-semibold">Nouvelle page</h2>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 transition-colors hover:text-gray-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          {error ? (
            <div className="rounded-md bg-red-100 p-3 text-sm text-red-800">{error}</div>
          ) : null}

          <div>
            <label htmlFor="create-page-placement" className="mb-1 block text-sm font-medium text-gray-700">
              Emplacement dans l’arborescence
            </label>
            <select
              id="create-page-placement"
              value={parentId ?? ''}
              onChange={(e) => setParentId(e.target.value ? e.target.value : null)}
              disabled={siteTreeLoading || loading}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500 disabled:bg-gray-100"
            >
              <option value="">
                Racine — barre de navigation principale + arborescence
              </option>
              {parentOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  Sous : {opt.label}
                </option>
              ))}
            </select>
            <p className="mt-1 text-xs text-gray-600">
              {siteTreeLoading
                ? 'Chargement de l’arborescence…'
                : atRoot
                  ? 'Une entrée du menu primaire sera créée automatiquement (sauf pour les slugs réservés home et blog).'
                  : 'La page est rattachée sous la page choisie : elle apparaît dans l’arborescence et le méga-menu selon la structure existante, sans nouvel onglet racine dans la barre.'}
            </p>
          </div>

          <div>
            <label htmlFor="template" className="mb-1 block text-sm font-medium text-gray-700">
              Gabarit
            </label>
            <select
              id="template"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
            >
              <option value="homepage">Homepage</option>
            </select>
            <p className="mt-1 text-xs text-gray-500">
              Le gabarit détermine quelles sections peuvent être ajoutées ensuite.
            </p>
          </div>

          <div>
            <label htmlFor="title" className="mb-1 block text-sm font-medium text-gray-700">
              Titre <span className="text-gray-400">(recommandé)</span>
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => handleTitleChange(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="À propos"
            />
          </div>

          <div>
            <label htmlFor="slug" className="mb-1 block text-sm font-medium text-gray-700">
              Slug <span className="text-red-500">*</span>
            </label>
            <input
              id="slug"
              type="text"
              value={slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-sm focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="a-propos"
              required
            />
            <p className="mt-1 text-xs text-gray-500">
              Minuscules, alphanumériques et tirets. Max. 60 caractères. « home » est réservé.
            </p>
            {slug && !isValidSlug(slug) ? (
              <p className="mt-1 text-xs text-red-600">Format de slug invalide</p>
            ) : null}
          </div>

          <div>
            <label htmlFor="description" className="mb-1 block text-sm font-medium text-gray-700">
              Description <span className="text-gray-400">(optionnel)</span>
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-gray-300 px-3 py-2 focus:border-indigo-500 focus:ring-indigo-500"
              placeholder="Brève description…"
            />
          </div>

          <div className="flex justify-end gap-3 border-t pt-4">
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              Annuler
            </Button>
            <Button type="submit" disabled={loading || !slug.trim() || !isValidSlug(slug)}>
              {loading ? 'Création…' : 'Créer la page'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
