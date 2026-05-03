'use client'

import { ArrowDown, ArrowUp, ChevronDown, X } from 'lucide-react'
import { MediaTile } from '@/components/admin/MediaTile'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

type StepRow = {
  number: string
  title: string
  description: string
  imageMediaId: string
  stepButtonLabel: string
  stepButtonHref: string
}

function readSteps(content: Record<string, unknown>): StepRow[] {
  const raw = content.steps
  if (!Array.isArray(raw) || raw.length === 0) {
    return [
      {
        number: '01',
        title: '',
        description: '',
        imageMediaId: '',
        stepButtonLabel: '',
        stepButtonHref: '',
      },
    ]
  }
  return raw.map((it) => {
    const o = it != null && typeof it === 'object' && !Array.isArray(it) ? (it as Record<string, unknown>) : {}
    return {
      number: readString(o.number),
      title: readString(o.title),
      description: readString(o.description),
      imageMediaId: readString(o.imageMediaId),
      stepButtonLabel: readString(o.stepButtonLabel),
      stepButtonHref: readString(o.stepButtonHref),
    }
  })
}

/**
 * Éditeur compact du bloc article `HOW_IT_WORKS_CAROUSEL`.
 * Données persistées identiques (cf. `articleBlockDataSchemas.ts`) :
 * seule l'UI a été densifiée (étapes en cartes horizontales pliables).
 */
export function HowItWorksCarouselEditor({ content, onPatch }: Props) {
  const label = readString(content.label)
  const title = readString(content.title)
  const subtitle = readString(content.subtitle)
  const hideStepNumbering = content.hideStepNumbering === true
  const primaryCtaText = readString(content.primaryCtaText)
  const primaryCtaHref = readString(content.primaryCtaHref)
  const secondaryCtaText = readString(content.secondaryCtaText)
  const secondaryCtaHref = readString(content.secondaryCtaHref)
  const steps = readSteps(content)

  const setSteps = (next: StepRow[]) => {
    onPatch({
      steps: next.map((r) => ({
        number: r.number,
        title: r.title,
        description: r.description,
        ...(r.imageMediaId ? { imageMediaId: r.imageMediaId } : {}),
        ...(r.stepButtonLabel ? { stepButtonLabel: r.stepButtonLabel } : {}),
        ...(r.stepButtonHref ? { stepButtonHref: r.stepButtonHref } : {}),
      })),
    })
  }

  const updateStep = (index: number, field: keyof StepRow, value: string) => {
    const next = steps.map((s, i) => (i === index ? { ...s, [field]: value } : s))
    setSteps(next)
  }

  return (
    <div className="mt-2 space-y-3 border-t border-gray-100 pt-3">
      <div className="grid gap-2 sm:grid-cols-3">
        <input
          type="text"
          value={label}
          onChange={(e) => onPatch({ label: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Surtitre (HOW IT WORKS)"
        />
        <input
          type="text"
          value={title}
          onChange={(e) => onPatch({ title: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Titre du module"
        />
        <input
          type="text"
          value={subtitle}
          onChange={(e) => onPatch({ subtitle: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Sous-titre (optionnel)"
        />
      </div>

      <label className="flex items-center gap-2 text-xs text-gray-700">
        <input
          type="checkbox"
          checked={hideStepNumbering}
          onChange={(e) => onPatch({ hideStepNumbering: e.target.checked })}
          className="h-3.5 w-3.5 rounded border-gray-300"
        />
        Masquer les numéros d&apos;étape (web — le mobile affiche toujours la pill)
      </label>

      <div>
        <p className="mb-1 text-xs font-medium text-gray-700">
          Étapes <span className="font-normal text-gray-500">({steps.length})</span>
        </p>
        <div className="space-y-1.5">
          {steps.map((row, index) => {
            const summary = row.title?.trim() || `Étape ${index + 1}`
            return (
              <details
                key={`step-${index}`}
                open={steps.length <= 3}
                className="group rounded border border-gray-200 bg-white"
              >
                <summary className="flex cursor-pointer list-none items-center gap-2 p-1.5 hover:bg-gray-50">
                  <ChevronDown className="h-3.5 w-3.5 shrink-0 text-gray-400 transition group-open:rotate-180" />
                  <span className="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[11px] text-gray-700">
                    {row.number || String(index + 1).padStart(2, '0')}
                  </span>
                  <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900">
                    {summary}
                  </span>
                  <div className="flex shrink-0 items-center gap-0.5">
                    <button
                      type="button"
                      title="Monter"
                      disabled={index === 0}
                      onClick={(e) => {
                        e.preventDefault()
                        if (index === 0) return
                        const next = [...steps]
                        ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
                        setSteps(next)
                      }}
                      className="rounded p-1 text-gray-500 hover:bg-gray-100 disabled:opacity-40"
                    >
                      <ArrowUp className="h-3.5 w-3.5" />
                    </button>
                    <button
                      type="button"
                      title="Descendre"
                      disabled={index >= steps.length - 1}
                      onClick={(e) => {
                        e.preventDefault()
                        if (index >= steps.length - 1) return
                        const next = [...steps]
                        ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                        setSteps(next)
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
                        if (steps.length <= 1) {
                          setSteps([
                            {
                              number: '01',
                              title: '',
                              description: '',
                              imageMediaId: '',
                              stepButtonLabel: '',
                              stepButtonHref: '',
                            },
                          ])
                          return
                        }
                        setSteps(steps.filter((_, i) => i !== index))
                      }}
                      className="rounded p-1 text-red-600 hover:bg-red-50"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </summary>

                <div className="flex gap-2 border-t border-gray-100 p-2">
                  <MediaTile
                    size={64}
                    mediaId={row.imageMediaId}
                    index={index}
                    total={steps.length}
                    onChange={(newId) => updateStep(index, 'imageMediaId', newId)}
                    onRemove={() => updateStep(index, 'imageMediaId', '')}
                    pickerKind="image"
                    pickerTitle="Image de l'étape"
                  />
                  <div className="flex min-w-0 flex-1 flex-col gap-1">
                    <div className="grid gap-1 sm:grid-cols-[80px_1fr]">
                      <input
                        type="text"
                        value={row.number}
                        onChange={(e) => updateStep(index, 'number', e.target.value)}
                        className="w-full rounded border border-gray-200 px-2 py-1 text-sm"
                        placeholder="01"
                      />
                      <input
                        type="text"
                        value={row.title}
                        onChange={(e) => updateStep(index, 'title', e.target.value)}
                        className="w-full rounded border border-gray-200 px-2 py-1 text-sm font-medium"
                        placeholder="Titre de l'étape"
                      />
                    </div>
                    <textarea
                      value={row.description}
                      onChange={(e) => updateStep(index, 'description', e.target.value)}
                      className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
                      rows={2}
                      placeholder="Description (web uniquement)"
                    />
                    <div className="grid gap-1 sm:grid-cols-2">
                      <input
                        type="text"
                        value={row.stepButtonLabel}
                        onChange={(e) => updateStep(index, 'stepButtonLabel', e.target.value)}
                        className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
                        placeholder="Libellé bouton (optionnel)"
                      />
                      <input
                        type="text"
                        value={row.stepButtonHref}
                        onChange={(e) => updateStep(index, 'stepButtonHref', e.target.value)}
                        className="w-full rounded border border-gray-200 px-2 py-1 text-xs font-mono"
                        placeholder="URL bouton"
                      />
                    </div>
                  </div>
                </div>
              </details>
            )
          })}
          <button
            type="button"
            className="text-xs font-medium text-indigo-700 hover:text-indigo-900"
            onClick={() =>
              setSteps([
                ...steps,
                {
                  number: String(steps.length + 1).padStart(2, '0'),
                  title: '',
                  description: '',
                  imageMediaId: '',
                  stepButtonLabel: '',
                  stepButtonHref: '',
                },
              ])
            }
          >
            + Ajouter une étape
          </button>
        </div>
      </div>

      <details className="rounded border border-gray-100 bg-gray-50/60">
        <summary className="cursor-pointer list-none px-2 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100">
          CTAs globaux du module (web uniquement)
        </summary>
        <div className="grid gap-1.5 p-2 sm:grid-cols-2">
          <input
            type="text"
            value={primaryCtaText}
            onChange={(e) => onPatch({ primaryCtaText: e.target.value })}
            className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
            placeholder="Libellé CTA principal"
          />
          <input
            type="text"
            value={primaryCtaHref}
            onChange={(e) => onPatch({ primaryCtaHref: e.target.value })}
            className="w-full rounded border border-gray-200 px-2 py-1 text-xs font-mono"
            placeholder="URL CTA principal"
          />
          <input
            type="text"
            value={secondaryCtaText}
            onChange={(e) => onPatch({ secondaryCtaText: e.target.value })}
            className="w-full rounded border border-gray-200 px-2 py-1 text-xs"
            placeholder="Libellé CTA secondaire"
          />
          <input
            type="text"
            value={secondaryCtaHref}
            onChange={(e) => onPatch({ secondaryCtaHref: e.target.value })}
            className="w-full rounded border border-gray-200 px-2 py-1 text-xs font-mono"
            placeholder="URL CTA secondaire"
          />
        </div>
      </details>
    </div>
  )
}
