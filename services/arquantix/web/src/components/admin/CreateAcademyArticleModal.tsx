'use client'

/**
 * Modal de création d'un Article ACADEMY (Phase 4 — symétrique HELP).
 *
 * Réutilise `<AcademyHierarchyPicker>` pour collecter collection / category /
 * academySlug + allowAnchors, puis POST `/api/admin/articles` avec
 * `articleType=ACADEMY`. L'API calcule le slug global unique et persiste
 * les 3 ids ACADEMY. À la création, on redirige vers l'éditeur unifié
 * `/admin/articles/[id]` qui affiche le picker ACADEMY pour permettre de
 * modifier la hiérarchie ensuite.
 */

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import AcademyHierarchyPicker, {
  type AcademyHierarchyValue,
} from './AcademyHierarchyPicker'
import { messageFromAdminApiError } from '@/lib/admin/messageFromAdminApiError'
import { toastError, toastSuccess } from '@/lib/admin/toast'

interface Props {
  open: boolean
  onClose: () => void
}

export default function CreateAcademyArticleModal({ open, onClose }: Props) {
  const router = useRouter()
  const [authorName, setAuthorName] = useState('Vancelian')
  const [hierarchy, setHierarchy] = useState<AcademyHierarchyValue>({
    academyCollectionId: null,
    academySlug: null,
    collectionTags: [],
    allowAnchors: true,
  })
  const [submitting, setSubmitting] = useState(false)
  const [showErrors, setShowErrors] = useState(false)

  const reset = () => {
    setAuthorName('Vancelian')
    setHierarchy({
      academyCollectionId: null,
      academySlug: null,
      collectionTags: [],
      allowAnchors: true,
    })
    setShowErrors(false)
    setSubmitting(false)
  }

  const handleClose = () => {
    if (submitting) return
    reset()
    onClose()
  }

  const handleSubmit = async () => {
    if (!hierarchy.academyCollectionId || !hierarchy.academySlug || !authorName.trim()) {
      setShowErrors(true)
      return
    }
    setSubmitting(true)
    try {
      const res = await fetch('/api/admin/articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          authorName: authorName.trim(),
          articleType: 'ACADEMY',
          academyCollectionId: hierarchy.academyCollectionId,
          academySlug: hierarchy.academySlug,
          collectionTags:
            hierarchy.collectionTags.length > 0 ? hierarchy.collectionTags : undefined,
        }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(messageFromAdminApiError(err, 'Failed to create ACADEMY article'))
      }
      const data = await res.json()
      toastSuccess('Article Academy créé')
      const articleId = data?.article?.id
      reset()
      onClose()
      if (articleId) router.push(`/admin/articles/${encodeURIComponent(articleId)}`)
    } catch (e: any) {
      toastError(e?.message || 'Erreur lors de la création')
    } finally {
      setSubmitting(false)
    }
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-lg bg-white shadow-lg">
        <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Nouvel article Academy</h2>
            <p className="text-xs text-gray-500">
              Collection + slug URL ; les tags catégorie structurent les sections.
              URL publique :{' '}
              <code className="rounded bg-gray-100 px-1">/academy/[collection]/[slug]</code>.
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            disabled={submitting}
            className="rounded p-1 text-gray-500 hover:bg-gray-100"
            aria-label="Fermer"
          >
            ×
          </button>
        </div>

        <div className="space-y-4 px-4 py-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Author name</label>
            <input
              type="text"
              disabled={submitting}
              value={authorName}
              onChange={(e) => setAuthorName(e.target.value)}
              className={`w-full rounded border px-2 py-1 text-sm ${
                showErrors && !authorName.trim() ? 'border-red-400' : 'border-gray-300'
              }`}
              placeholder="Vancelian"
            />
            {showErrors && !authorName.trim() && (
              <p className="mt-0.5 text-[11px] text-red-600">Author name requis.</p>
            )}
          </div>

          <AcademyHierarchyPicker
            value={hierarchy}
            onChange={setHierarchy}
            disabled={submitting}
            showErrors={showErrors}
          />

          <p className="text-[11px] text-gray-500">
            Tu pourras ensuite ajouter le titre, le standfirst, les blocs (PARAGRAPH, IMAGE,
            VIDEO, etc.) directement depuis l'éditeur unifié de l'article.
          </p>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-gray-200 px-4 py-3">
          <Button variant="outline" onClick={handleClose} disabled={submitting}>
            Annuler
          </Button>
          <Button onClick={handleSubmit} disabled={submitting}>
            {submitting ? 'Création…' : "Créer l'article"}
          </Button>
        </div>
      </div>
    </div>
  )
}
