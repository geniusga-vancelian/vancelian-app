'use client'

/**
 * Lot 4–5 — écarts menu ↔ arbre, synchronisation contrôlée, libellés lisibles, actions rapides.
 */

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { Info, AlertTriangle, RefreshCw, GitBranch, Sparkles, ArrowDown } from 'lucide-react'

type Warning = {
  code: string
  severity: 'info' | 'warning'
  message: string
}

type AlignmentResponse = {
  navPageOrder: { id: string; slug: string; title: string | null }[]
  warnings: Warning[]
  orderMatchesNavTree: boolean
  missingMenuPageIds: string[]
  menuNavSequence: string[]
  applyHints: {
    missingCount: number
    canAddMissing: boolean
    canReorder: boolean
  }
}

const WARNING_TITLE: Record<string, string> = {
  MISSING_ROOT: 'Accueil du menu',
  MULTIPLE_ROOTS: 'Plusieurs racines',
  DUPLICATE_MENU_LINK_PAGE: 'Doublon dans le menu',
  TREE_PAGE_NOT_IN_MENU: 'Pages absentes du menu',
  MENU_LINK_PAGE_HIDDEN_FROM_NAV: 'Lien menu vs visibilité',
  MENU_ORPHAN_LINK: 'Lien cassé',
  VAULT_URL_PATH_MISMATCH: 'URL vault incohérente',
  ORDER_DIVERGENCE: 'Ordre différent de l’arbre',
}

function friendlyWarningTitle(code: string): string {
  return WARNING_TITLE[code] ?? code.replace(/_/g, ' ')
}

export function MenuStructureAlignmentPanel({
  active,
  onApplied,
}: {
  active: boolean
  onApplied: () => Promise<void>
}) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<AlignmentResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [addMissing, setAddMissing] = useState(true)
  const [reorderNavLinks, setReorderNavLinks] = useState(false)
  const [applying, setApplying] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [justSynced, setJustSynced] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/admin/menus/primary/structure-alignment')
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Erreur analyse')
      setData(json as AlignmentResponse)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!active) return
    void load()
  }, [active, load])

  useEffect(() => {
    if (!justSynced) return
    const t = setTimeout(() => setJustSynced(false), 2400)
    return () => clearTimeout(t)
  }, [justSynced])

  const handleApply = async () => {
    if (!addMissing && !reorderNavLinks) {
      toastError('Cochez au moins une action')
      return
    }
    setApplying(true)
    try {
      const res = await fetch('/api/admin/menus/primary/structure-alignment', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ addMissing, reorderNavLinks }),
      })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Échec de la synchronisation')
      toastSuccess('Menu mis à jour')
      setJustSynced(true)
      await load()
      await onApplied()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Erreur')
    } finally {
      setApplying(false)
    }
  }

  const missingPages =
    data?.navPageOrder.filter((p) => data.missingMenuPageIds.includes(p.id)) ?? []

  const scrollToSync = () => {
    document.getElementById('cms-menu-sync-actions')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  if (!active) return null

  return (
    <div
      className={`rounded-xl border border-slate-200 bg-gradient-to-b from-slate-50/90 to-white p-5 shadow-sm transition-shadow duration-500 ${
        justSynced ? 'ring-2 ring-emerald-400/70 ring-offset-2' : ''
      }`}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex gap-2">
          <GitBranch className="mt-0.5 h-5 w-5 text-indigo-600" />
          <div>
            <h3 className="text-base font-semibold text-slate-900">Menu ↔ structure du site</h3>
            <p className="mt-1 max-w-3xl text-xs text-slate-600">
              La <strong>structure</strong> (pages) fait foi pour l’organisation ; le <strong>menu</strong> est la
              couche visible par les visiteurs. Ici vous voyez les écarts et vous appliquez une mise à jour{' '}
              <strong>volontaire</strong> — rien n’est écrasé sans confirmation.
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-3 py-2 text-xs font-medium text-slate-700 shadow-sm transition hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </button>
      </div>

      {error && (
        <p className="mt-3 text-xs text-red-600" role="alert">
          {error}
        </p>
      )}

      {loading && !data && <p className="mt-4 text-sm text-slate-500">Analyse…</p>}

      {data && (
        <>
          <div className="mt-4 flex flex-wrap gap-2 text-xs">
            <span
              className={`inline-flex items-center rounded-full px-3 py-1.5 font-medium transition ${
                data.orderMatchesNavTree
                  ? 'bg-emerald-100 text-emerald-900'
                  : 'bg-amber-100 text-amber-900'
              }`}
            >
              Ordre : {data.orderMatchesNavTree ? 'identique à l’arbre' : 'différent de l’arbre'}
            </span>
            <span className="rounded-full bg-white px-3 py-1.5 font-medium text-slate-700 ring-1 ring-slate-200">
              Pages prévues pour le menu : {data.navPageOrder.length}
            </span>
            <span className="rounded-full bg-white px-3 py-1.5 font-medium text-slate-700 ring-1 ring-slate-200">
              Manquantes : {data.missingMenuPageIds.length}
            </span>
          </div>

          {missingPages.length > 0 && (
            <div className="mt-4 rounded-lg border border-indigo-100 bg-indigo-50/40 p-3">
              <p className="text-xs font-semibold text-indigo-950">Pages sur le site mais pas encore dans le menu</p>
              <ul className="mt-2 flex flex-wrap gap-2">
                {missingPages.map((p) => (
                  <li key={p.id}>
                    <Link
                      href={`/admin/pages/${p.slug}`}
                      className="inline-flex rounded-md bg-white px-2 py-1 text-[11px] font-medium text-indigo-700 shadow-sm ring-1 ring-indigo-100 transition hover:bg-indigo-50"
                    >
                      {p.title?.trim() || p.slug}
                    </Link>
                  </li>
                ))}
              </ul>
              <div className="mt-2 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setAddMissing(true)
                    scrollToSync()
                  }}
                  className="inline-flex items-center gap-1 rounded-lg bg-indigo-600 px-3 py-1.5 text-[11px] font-medium text-white shadow-sm hover:bg-indigo-700"
                >
                  <Sparkles className="h-3.5 w-3.5" />
                  Préparer l’ajout au menu
                </button>
              </div>
            </div>
          )}

          {!data.orderMatchesNavTree && data.applyHints.canReorder && (
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  setReorderNavLinks(true)
                  scrollToSync()
                }}
                className="inline-flex items-center gap-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-[11px] font-medium text-amber-950 hover:bg-amber-100"
              >
                <ArrowDown className="h-3.5 w-3.5" />
                Activer le réordonnancement selon l’arbre
              </button>
            </div>
          )}

          {data.warnings.length > 0 && (
            <ul className="mt-4 space-y-2">
              {data.warnings.map((w, idx) => (
                <li
                  key={`${w.code}-${idx}`}
                  className={`flex gap-3 rounded-lg border px-3 py-2.5 text-xs transition ${
                    w.severity === 'warning'
                      ? 'border-amber-200 bg-amber-50/90 text-amber-950'
                      : 'border-sky-200 bg-sky-50/90 text-sky-950'
                  }`}
                >
                  {w.severity === 'warning' ? (
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  ) : (
                    <Info className="mt-0.5 h-4 w-4 shrink-0" />
                  )}
                  <div>
                    <p className="font-semibold text-slate-900">{friendlyWarningTitle(w.code)}</p>
                    <p className="mt-0.5 text-slate-700">{w.message}</p>
                    {w.code === 'VAULT_URL_PATH_MISMATCH' && (
                      <p className="mt-1 text-[11px] text-slate-600">
                        Corrigez l’URL en base depuis l’édition de la page concernée (champ technique ou script
                        métier).
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div
            id="cms-menu-sync-actions"
            className="mt-5 rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
          >
            <p className="text-xs font-semibold text-slate-800">Synchroniser le menu</p>
            <p className="mt-1 text-[11px] text-slate-500">
              Cochez ce que vous voulez appliquer, puis confirmez. Les boutons et liens externes restent en place.
            </p>
            <div className="mt-3 space-y-2 text-sm">
              <label className="flex cursor-pointer items-start gap-2 rounded-lg border border-transparent p-1 hover:border-slate-100">
                <input
                  type="checkbox"
                  checked={addMissing}
                  onChange={(e) => setAddMissing(e.target.checked)}
                  className="mt-1"
                />
                <span>
                  <strong>Ajouter</strong> les entrées lien manquantes (pages marquées visibles dans le menu, hors
                  page d’accueil)
                </span>
              </label>
              {!data.applyHints.canAddMissing && (
                <p className="pl-7 text-[11px] text-slate-500">Rien à ajouter pour l’instant.</p>
              )}
              <label
                className={`flex cursor-pointer items-start gap-2 rounded-lg border border-transparent p-1 hover:border-slate-100 ${!data.applyHints.canReorder ? 'opacity-60' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={reorderNavLinks}
                  onChange={(e) => setReorderNavLinks(e.target.checked)}
                  disabled={!data.applyHints.canReorder}
                  className="mt-1"
                />
                <span>
                  <strong>Réordonner</strong> : racine, puis liens « menu » comme dans l’arbre, puis le reste (CTA,
                  etc.)
                </span>
              </label>
              {!data.applyHints.canReorder && (
                <p className="pl-7 text-[11px] text-amber-800">
                  Une seule entrée « racine » est requise pour réordonner automatiquement.
                </p>
              )}
            </div>
            <button
              type="button"
              disabled={applying || (!addMissing && !reorderNavLinks)}
              onClick={() => setConfirmOpen(true)}
              className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-xs font-medium text-white shadow-sm transition hover:bg-indigo-700 disabled:opacity-50"
            >
              {applying ? 'Application…' : 'Appliquer…'}
            </button>
          </div>
        </>
      )}

      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        onConfirm={() => void handleApply()}
        title="Confirmer la mise à jour du menu"
        description={
          `${addMissing ? 'Ajout des liens manquants.' : 'Pas d’ajout.'} ${reorderNavLinks ? 'Réordonnancement selon l’arbre.' : 'Pas de changement d’ordre.'} Les CTA et URLs externes ne sont pas supprimés.`
        }
        confirmLabel="Appliquer"
        cancelLabel="Annuler"
        destructive={false}
      />
    </div>
  )
}
