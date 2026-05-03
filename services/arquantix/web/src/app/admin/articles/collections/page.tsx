'use client'

import type { ReactNode } from 'react'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ChevronDown, Layers } from 'lucide-react'
import { cn } from '@/lib/utils'
import { HierarchicalCollectionsWorkspace } from '@/components/admin/article-collections/HierarchicalCollectionsWorkspace'
import { ARTICLE_TYPES, type ArticleTypeKey } from '@/lib/admin/articleTypes'

const EDITORIAL_COLLECTION_STUB_ORDER: ArticleTypeKey[] = [
  'NEWS',
  'ANALYSIS',
  'RESEARCH',
  'USER_BLOG',
]

function FoldableCollectionSection({
  id,
  title,
  subtitle,
  children,
}: {
  id: string
  title: string
  subtitle: string
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (typeof window === 'undefined') return

    const syncHash = () => {
      const raw = window.location.hash.replace(/^#/, '')
      if (raw === id) setOpen(true)
    }

    syncHash()
    window.addEventListener('hashchange', syncHash)
    return () => window.removeEventListener('hashchange', syncHash)
  }, [id])

  return (
    <section
      id={id}
      className="scroll-mt-28 border-b border-slate-200 pb-6 last:border-b-0 last:pb-4"
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={`${id}-panel`}
        id={`${id}-heading`}
        className="flex w-full items-start gap-3 rounded-lg py-2 text-left transition-colors hover:bg-slate-50/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-500"
      >
        <ChevronDown
          aria-hidden
          className={cn(
            'mt-1 h-6 w-6 shrink-0 text-slate-500 transition-transform duration-200',
            open ? 'rotate-180' : 'rotate-0',
          )}
        />
        <span className="min-w-0 flex-1 border-l-4 border-indigo-500 pl-4">
          <span className="block text-2xl font-bold text-gray-900">{title}</span>
          <span className="mt-1 block max-w-3xl text-sm leading-relaxed text-gray-600">
            {subtitle}
          </span>
        </span>
      </button>
      {open ? (
        <div
          id={`${id}-panel`}
          role="region"
          aria-labelledby={`${id}-heading`}
          className="mt-6 border-t border-slate-100 pt-6"
        >
          {children}
        </div>
      ) : null}
    </section>
  )
}

export default function ArticleCollectionsHubPage() {
  return (
    <div>
      <div className="mb-10">
        <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-600">
          <Layers className="h-3.5 w-3.5" aria-hidden />
          Articles
        </div>
        <h1 className="text-3xl font-bold text-gray-900">Collections par type de contenu</h1>
        <p className="mt-2 max-w-3xl text-gray-600">
          Les <strong>collections hiérarchiques</strong> du Centre d&apos;aide et de l&apos;Academy utilisent
          désormais des <strong>articles à plat</strong> sous chaque collection, avec des{' '}
          <strong>tags catégorie</strong> pour les sections (sans obliger une administration des catégories).
          types éditoriaux (News, Analysis, etc.) s&apos;organisent via les{' '}
          <Link href="/admin/articles/categories" className="font-medium text-indigo-600 hover:underline">
            catégories blog
          </Link>{' '}
          et le filtre de type dans la liste des articles.
        </p>
      </div>

      <FoldableCollectionSection
        id="collections-help"
        title={`${ARTICLE_TYPES.HELP.label} — collections`}
        subtitle="Articles HELP à plat sous chaque collection ; regroupements via les tags catégorie (metadata)."
      >
        <HierarchicalCollectionsWorkspace workspace="help" compactHeader />
      </FoldableCollectionSection>

      <FoldableCollectionSection
        id="collections-academy"
        title={`${ARTICLE_TYPES.ACADEMY.label} — collections`}
        subtitle="Articles ACADEMY à plat sous chaque collection ; regroupements via les tags catégorie (metadata)."
      >
        <HierarchicalCollectionsWorkspace workspace="academy" compactHeader />
      </FoldableCollectionSection>

      {EDITORIAL_COLLECTION_STUB_ORDER.map((key) => {
        const d = ARTICLE_TYPES[key]
        return (
          <FoldableCollectionSection
            key={key}
            id={`collections-${key.toLowerCase()}`}
            title={`${d.label} — collections`}
            subtitle={`Il n’existe pas encore de table « collections » dédiée aux articles ${d.label} : ils utilisent le slug global, les catégories blog et les métadonnées éditoriales.`}
          >
            <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50/90 p-6 text-sm text-slate-700">
              <p>
                <Link
                  href={`/admin/articles?type=${key}`}
                  className="font-semibold text-indigo-700 hover:underline"
                >
                  Liste des articles {d.label}
                </Link>
                <span className="mx-2 text-slate-400">·</span>
                <Link
                  href="/admin/articles/categories"
                  className="font-semibold text-indigo-700 hover:underline"
                >
                  Catégories blog
                </Link>
              </p>
            </div>
          </FoldableCollectionSection>
        )
      })}
    </div>
  )
}
