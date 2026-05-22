'use client'

import { ArrowDown, ArrowUp, X } from 'lucide-react'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type FaqItem = {
  articleSlug: string
  question: string
  collectionSlug: string
  categorySlug: string
  standfirst: string
}

function readItems(content: Record<string, unknown>): FaqItem[] {
  const raw = content.items
  if (!Array.isArray(raw) || raw.length === 0) {
    return [{ articleSlug: '', question: '', collectionSlug: '', categorySlug: '', standfirst: '' }]
  }
  return raw.map((it) => {
    const o = it != null && typeof it === 'object' && !Array.isArray(it) ? (it as Record<string, unknown>) : {}
    return {
      articleSlug: readString(o.articleSlug),
      question: readString(o.question),
      collectionSlug: readString(o.collectionSlug),
      categorySlug: readString(o.categorySlug),
      standfirst: readString(o.standfirst),
    }
  })
}

export function VaultFaqAccordionModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const intro = readString(content.intro)
  const footerLinkLabel = readString(content.footerLinkLabel)
  const footerLinkUrl = readString(content.footerLinkUrl)
  const footerCollectionSlug = readString(content.footerCollectionSlug)
  const footerCategorySlug = readString(content.footerCategorySlug)
  const footerFilterLabel = readString(content.footerFilterLabel)
  const items = readItems(content)
  const setItems = (next: FaqItem[]) => onPatch({ items: next })

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <p className="text-[11px] text-gray-600">
        Chaque entrée référence un article Help (slug + collection + catégorie) pour l’app mobile. Le bandeau web
        affiche surtout titre, intro et lien pied de page.
      </p>
      <input
        type="text"
        value={title}
        onChange={(e) => onPatch({ title: e.target.value })}
        className="w-full rounded-md border px-2 py-1.5 text-sm"
        placeholder="Titre FAQ"
      />
      <textarea
        value={intro}
        onChange={(e) => onPatch({ intro: e.target.value })}
        rows={2}
        className="w-full rounded-md border px-2 py-1.5 text-xs"
        placeholder="Introduction (texte)"
      />

      <div className="rounded-md border border-indigo-100 bg-indigo-50/40 p-3 space-y-2">
        <p className="text-xs font-semibold text-indigo-900">Lien « tout voir » sous le bloc FAQ</p>
        <p className="text-[11px] text-gray-600">
          Sans <span className="font-medium">titre de lien</span>, aucun lien n&apos;est affiché (ni web ni app). La
          cible par défaut est la <span className="font-medium">liste des articles</span> de la catégorie Help (
          <span className="font-mono">/help/collection/catégorie</span>
          ). Vous pouvez aussi coller une <span className="font-medium">URL complète</span> (campagne, page hors
          Help) — elle remplace collection/catégorie.
        </p>
        <p className="text-[11px] text-gray-600">
          <span className="font-medium">Alternative (même URL) :</span> le segment Help peut résoudre une{' '}
          <span className="font-medium">catégorie</span> ou un <span className="font-medium">tag</span> — si votre
          FAQ projet est structurée par tag, mettez le slug du tag dans « catégorie » (même champ).
        </p>
        <input
          type="text"
          value={footerLinkLabel}
          onChange={(e) => onPatch({ footerLinkLabel: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Titre du lien (ex. Voir les FAQ du projet)"
        />
        <input
          type="text"
          value={footerLinkUrl}
          onChange={(e) => onPatch({ footerLinkUrl: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-xs font-mono"
          placeholder="URL optionnelle (https://… ou /fr/help/…)"
        />
        <div className="grid gap-2 sm:grid-cols-2">
          <input
            type="text"
            value={footerCollectionSlug}
            onChange={(e) => onPatch({ footerCollectionSlug: e.target.value })}
            className="rounded-md border px-2 py-1.5 text-xs font-mono"
            placeholder="Collection Help (slug)"
          />
          <input
            type="text"
            value={footerCategorySlug}
            onChange={(e) => onPatch({ footerCategorySlug: e.target.value })}
            className="rounded-md border px-2 py-1.5 text-xs font-mono"
            placeholder="Catégorie Help ou tag (slug)"
          />
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <input
          type="text"
          value={footerFilterLabel}
          onChange={(e) => onPatch({ footerFilterLabel: e.target.value })}
          className="rounded-md border px-2 py-1.5 text-xs"
          placeholder="Filtre / tag (optionnel, usage futur)"
        />
      </div>

      <div>
        <p className="mb-1 text-xs font-medium text-gray-700">Entrées FAQ ({items.length})</p>
        <div className="space-y-2">
          {items.map((row, index) => (
            <div key={`faq-${index}`} className="rounded-lg border border-gray-200 bg-white p-2 space-y-1">
              <div className="flex items-start justify-between gap-2">
                <span className="text-[10px] font-semibold uppercase text-gray-400">#{index + 1}</span>
                <div className="flex items-center gap-0.5">
                  <button
                    type="button"
                    disabled={index === 0}
                    title="Monter"
                    className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                    onClick={() => {
                      if (index === 0) return
                      const next = [...items]
                      ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                      setItems(next)
                    }}
                  >
                    <ArrowUp className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    disabled={index >= items.length - 1}
                    title="Descendre"
                    className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                    onClick={() => {
                      if (index >= items.length - 1) return
                      const next = [...items]
                      ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                      setItems(next)
                    }}
                  >
                    <ArrowDown className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    title="Retirer"
                    className="rounded p-1 text-red-600 hover:bg-red-50"
                    onClick={() =>
                      items.length <= 1
                        ? setItems([
                            {
                              articleSlug: '',
                              question: '',
                              collectionSlug: '',
                              categorySlug: '',
                              standfirst: '',
                            },
                          ])
                        : setItems(items.filter((_, i) => i !== index))
                    }
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
              <input
                type="text"
                value={row.question}
                onChange={(e) => {
                  const next = [...items]
                  next[index] = { ...row, question: e.target.value }
                  setItems(next)
                }}
                placeholder="Question affichée"
                className="w-full rounded border px-2 py-1 text-sm"
              />
              <div className="grid gap-1 sm:grid-cols-2">
                <input
                  type="text"
                  value={row.articleSlug}
                  onChange={(e) => {
                    const next = [...items]
                    next[index] = { ...row, articleSlug: e.target.value }
                    setItems(next)
                  }}
                  placeholder="articleSlug"
                  className="rounded border px-2 py-1 font-mono text-xs"
                />
                <input
                  type="text"
                  value={row.collectionSlug}
                  onChange={(e) => {
                    const next = [...items]
                    next[index] = { ...row, collectionSlug: e.target.value }
                    setItems(next)
                  }}
                  placeholder="collectionSlug"
                  className="rounded border px-2 py-1 font-mono text-xs"
                />
                <input
                  type="text"
                  value={row.categorySlug}
                  onChange={(e) => {
                    const next = [...items]
                    next[index] = { ...row, categorySlug: e.target.value }
                    setItems(next)
                  }}
                  placeholder="categorySlug"
                  className="rounded border px-2 py-1 font-mono text-xs sm:col-span-2"
                />
              </div>
              <textarea
                value={row.standfirst}
                onChange={(e) => {
                  const next = [...items]
                  next[index] = { ...row, standfirst: e.target.value }
                  setItems(next)
                }}
                rows={2}
                placeholder="Réponse courte / standfirst (optionnel)"
                className="w-full rounded border px-2 py-1 text-xs"
              />
            </div>
          ))}
        </div>
        <button
          type="button"
          onClick={() =>
            setItems([
              ...items,
              { articleSlug: '', question: '', collectionSlug: '', categorySlug: '', standfirst: '' },
            ])
          }
          className="mt-1 text-xs font-medium text-indigo-700 hover:text-indigo-900"
        >
          + Entrée FAQ
        </button>
      </div>
    </div>
  )
}
