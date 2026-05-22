'use client'

import { ArrowDown, ArrowUp, ChevronDown, X } from 'lucide-react'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type StepRow = {
  dayLabel: string
  date: string
  title: string
  description: string
  isCompleted: boolean
}

function readItems(content: Record<string, unknown>): StepRow[] {
  const raw = Array.isArray(content.items)
    ? content.items
    : Array.isArray(content.steps)
      ? content.steps
      : null
  if (!Array.isArray(raw) || raw.length === 0) {
    return [
      {
        dayLabel: '',
        date: '',
        title: '',
        description: '',
        isCompleted: false,
      },
    ]
  }
  return raw.map((it) => {
    const o = it != null && typeof it === 'object' && !Array.isArray(it) ? (it as Record<string, unknown>) : {}
    return {
      dayLabel: readString(o.dayLabel),
      date: readString(o.date),
      title: readString(o.title),
      description: readString(o.description),
      isCompleted: o.isCompleted === true,
    }
  })
}

/**
 * Éditeur compact module Étapes (timeline).
 * Données persistées identiques (cf. `articleBlockDataSchemas.ts`) :
 * seule l'UI a été densifiée (étapes pliables, header / champs raccourcis).
 */
export function ArticleStepsModuleEditor({ content, onPatch }: Props) {
  const title = readString(content.title)
  const subtitle = readString(content.subtitle)
  const description = readString(content.description)
  const rightLabel = readString(content.rightLabel)
  const items = readItems(content)

  const setItems = (next: StepRow[]) => {
    onPatch({
      items: next.map((r) => ({
        dayLabel: r.dayLabel,
        date: r.date,
        title: r.title,
        description: r.description,
        isCompleted: r.isCompleted,
      })),
    })
  }

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <p className="rounded-md border border-indigo-100 bg-indigo-50/80 px-2.5 py-2 text-[11px] leading-snug text-indigo-900">
        <span className="font-semibold">Saisie guidée</span> — aucun JSON à taper : titre du bloc, puis une ligne par
        étape. « Terminé » = pastille validée ; la première étape non cochée affiche{' '}
        <span className="font-medium">EN COURS</span> dans l&apos;app.
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        <input
          type="text"
          value={subtitle}
          onChange={(e) => onPatch({ subtitle: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Surtitre / pastille"
        />
        <input
          type="text"
          value={title}
          onChange={(e) => onPatch({ title: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Titre du module"
        />
      </div>
      <div className="grid gap-2 sm:grid-cols-[2fr_1fr]">
        <input
          type="text"
          value={description}
          onChange={(e) => onPatch({ description: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Description (centrée sous le titre)"
        />
        <input
          type="text"
          value={rightLabel}
          onChange={(e) => onPatch({ rightLabel: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Libellé secondaire (ex. 5 étapes)"
        />
      </div>

      <div>
        <p className="mb-1 text-xs font-medium text-gray-700">
          Étapes <span className="font-normal text-gray-500">({items.length})</span>
          <span className="ml-2 font-normal text-gray-500">
            — cocher « Terminé » pour les pastilles validées ;{' '}
            <strong className="font-medium text-gray-700">« EN COURS »</strong> s’affiche sur la première étape{' '}
            non cochée (les autres restent à venir)
          </span>
        </p>
        <div className="space-y-1.5">
          {items.map((row, index) => {
            const summary = row.title?.trim() || `Étape ${index + 1}`
            return (
              <details
                key={`step-${index}`}
                open={items.length <= 4}
                className="group rounded border border-gray-200 bg-white"
              >
                <summary className="flex cursor-pointer list-none items-center gap-2 p-1.5 hover:bg-gray-50">
                  <ChevronDown className="h-3.5 w-3.5 shrink-0 text-gray-400 transition group-open:rotate-180" />
                  <span
                    className={
                      'shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ' +
                      (row.isCompleted
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-gray-100 text-gray-600')
                    }
                  >
                    {row.isCompleted ? 'OK' : index + 1}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900">
                    {summary}
                  </span>
                  <label className="inline-flex shrink-0 items-center gap-1 text-xs text-gray-700">
                    <input
                      type="checkbox"
                      checked={row.isCompleted}
                      onClick={(e) => e.stopPropagation()}
                      onChange={(e) => {
                        const next = [...items]
                        next[index] = { ...row, isCompleted: e.target.checked }
                        setItems(next)
                      }}
                    />
                    Terminé
                  </label>
                  <div className="flex shrink-0 items-center gap-0.5">
                    <button
                      type="button"
                      title="Monter"
                      disabled={index === 0}
                      onClick={(e) => {
                        e.preventDefault()
                        if (index === 0) return
                        const next = [...items]
                        ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                        setItems(next)
                      }}
                      className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                    >
                      <ArrowUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      title="Descendre"
                      disabled={index >= items.length - 1}
                      onClick={(e) => {
                        e.preventDefault()
                        if (index >= items.length - 1) return
                        const next = [...items]
                        ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                        setItems(next)
                      }}
                      className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                    >
                      <ArrowDown className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      title="Retirer"
                      onClick={(e) => {
                        e.preventDefault()
                        if (items.length <= 1) {
                          setItems([
                            { dayLabel: '', date: '', title: '', description: '', isCompleted: false },
                          ])
                          return
                        }
                        setItems(items.filter((_, i) => i !== index))
                      }}
                      className="rounded p-1 text-red-600 hover:bg-red-50"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </summary>

                <div className="space-y-1 border-t border-gray-100 p-2">
                  <input
                    type="text"
                    value={row.title}
                    onChange={(e) => {
                      const next = [...items]
                      next[index] = { ...row, title: e.target.value }
                      setItems(next)
                    }}
                    className="w-full rounded border border-gray-200 px-2 py-1 text-sm font-medium"
                    placeholder="Titre (requis)"
                  />
                  <div className="grid gap-1 sm:grid-cols-2">
                    <input
                      type="text"
                      value={row.date}
                      onChange={(e) => {
                        const next = [...items]
                        next[index] = { ...row, date: e.target.value }
                        setItems(next)
                      }}
                      className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
                      placeholder="Texte au-dessus du titre (ex. Over, mars 2025)"
                    />
                    <input
                      type="text"
                      value={row.dayLabel}
                      onChange={(e) => {
                        const next = [...items]
                        next[index] = { ...row, dayLabel: e.target.value }
                        setItems(next)
                      }}
                      className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
                      placeholder="Étiquette jour (optionnel, ex. Jour 1)"
                    />
                  </div>
                  <textarea
                    value={row.description}
                    onChange={(e) => {
                      const next = [...items]
                      next[index] = { ...row, description: e.target.value }
                      setItems(next)
                    }}
                    className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
                    rows={2}
                    placeholder="Description (gris, sous la ligne de statut)"
                  />
                </div>
              </details>
            )
          })}
          <button
            type="button"
            className="text-xs font-medium text-indigo-700 hover:text-indigo-900"
            onClick={() =>
              setItems([
                ...items,
                { dayLabel: '', date: '', title: '', description: '', isCompleted: false },
              ])
            }
          >
            + Ajouter une étape
          </button>
        </div>
      </div>
    </div>
  )
}
