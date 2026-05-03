import { notFound, redirect } from 'next/navigation'
import { ArticleBlockType } from '@prisma/client'
import { getSessionFromCookie } from '@/lib/auth'
import {
  buildArticleBlockElements,
  type ArticleHeading,
} from '@/components/blog/ArticleBlockStream'
import {
  BLOCK_TYPE_LABELS,
  getDemoBlockData,
  type AddableBlockType,
} from '@/lib/admin/articleBlockCatalog'

interface PreviewArticleBlockDemoProps {
  params: { type: string }
}

const VALID_TYPES = new Set<string>(Object.keys(BLOCK_TYPE_LABELS))

/**
 * Aperçu admin d'un type de bloc d'article rendu seul, avec données de démo.
 * Utilisé par `/admin/articles/[id]/add-block` (panneau de droite) pour
 * montrer à quoi ressemble un bloc avant de l'ajouter.
 *
 * Auth admin obligatoire. Le rendu réutilise la même chaîne
 * (`buildArticleBlockElements`) que la page publique d'article ; aucun
 * fetch DB, juste les fixtures fournies par `getDemoBlockData`.
 */
export default async function PreviewArticleBlockDemoPage({
  params,
}: PreviewArticleBlockDemoProps) {
  const session = await getSessionFromCookie()
  if (!session) {
    redirect('/admin/login')
  }

  const rawType = decodeURIComponent(params.type)
  if (!VALID_TYPES.has(rawType)) {
    notFound()
  }
  const type = rawType as AddableBlockType

  const data = getDemoBlockData(type)
  // Les blocs avec médias (carousel, video posters, documents, how_it_works avec image)
  // n'ont pas de `mediaId` réel dans les fixtures : le rendu doit gérer le fallback.
  const demoBlock = {
    id: 'demo',
    type: type as ArticleBlockType,
    order: 0,
    data,
  }

  const headings: ArticleHeading[] = []
  const { elements } = buildArticleBlockElements([demoBlock])

  return (
    <main className="min-h-screen bg-white text-[#1a1d24]">
      <div className="mx-auto w-full max-w-[760px] px-4 py-10 sm:px-6">
        <div className="mb-6 flex flex-wrap items-center gap-2">
          <span className="rounded bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-indigo-800">
            Aperçu démo
          </span>
          <span className="text-xs text-slate-500">
            {BLOCK_TYPE_LABELS[type]} · données fictives
          </span>
        </div>
        {elements.map((entry) => (
          <div key={entry.blockId}>{entry.element}</div>
        ))}
        {/* Headings collectés (utilisé pour le sommaire dans l'article réel) — masqué ici. */}
        {headings.length > 0 ? <span className="hidden">{headings.length} headings</span> : null}
      </div>
    </main>
  )
}
