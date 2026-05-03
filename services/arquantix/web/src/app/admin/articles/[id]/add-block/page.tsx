'use client'

import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { messageFromAdminApiError } from '@/lib/admin/messageFromAdminApiError'
import { getDefaultBlockData } from '@/lib/admin/articleBlockCatalog'
import { AddBlockModal } from '@/components/admin/AddBlockModal'

/**
 * Page modale plein écran « Ajouter un bloc » pour l'admin article.
 * Délègue toute la mécanique UI/preview à `<AddBlockModal>` (composant
 * partagé) ; ne reste ici que la spécificité de l'API article :
 * POST `/api/admin/articles/[id]/blocks` puis retour à l'éditeur.
 */
export default function AddArticleBlockPage() {
  const router = useRouter()
  const params = useParams()
  const articleId = (params?.id as string | undefined) ?? ''

  if (!articleId) {
    return (
      <div className="p-8">
        <p className="text-slate-600">Identifiant d'article manquant.</p>
        <Link href="/admin/articles" className="text-indigo-600">
          Retour
        </Link>
      </div>
    )
  }

  const backHref = `/admin/articles/${encodeURIComponent(articleId)}`

  return (
    <AddBlockModal
      backHref={backHref}
      headerTitle="Ajouter un bloc à l'article"
      backLabel="← Retour à l'article"
      onValidate={async (selected) => {
        try {
          const res = await fetch(`/api/admin/articles/${articleId}/blocks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              type: selected.type,
              data: getDefaultBlockData(selected.type),
            }),
          })
          const data = await res.json().catch(() => ({}))
          if (!res.ok) {
            throw new Error(messageFromAdminApiError(data, 'Impossible d\u2019ajouter ce bloc.'))
          }
          toastSuccess('Bloc ajouté')
          router.push(backHref)
        } catch (e: unknown) {
          toastError(e instanceof Error ? e.message : 'Erreur')
        }
      }}
    />
  )
}
