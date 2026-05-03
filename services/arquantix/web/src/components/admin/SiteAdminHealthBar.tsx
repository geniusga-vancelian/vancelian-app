'use client'

import { useCallback, useEffect, useState } from 'react'
import { analyzeSiteTreeStructure } from '@/lib/admin/siteStructureTreeMeta'
import type { I18nSiteSummary } from '@/lib/admin/pageLocaleCompleteness'
import { LayoutDashboard, RefreshCw, CheckCircle2, AlertCircle, Languages } from 'lucide-react'

type AlignmentPayload = {
  orderMatchesNavTree: boolean
  missingMenuPageIds: string[]
  warnings: { code: string; severity: string }[]
}

/**
 * Résumé « État du site » : cohérence menu / arbre, pages nav manquantes, vaults racine, alertes.
 */
export function SiteAdminHealthBar({
  active,
  onOpenMenusTab,
}: {
  active: boolean
  onOpenMenusTab?: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [align, setAlign] = useState<AlignmentPayload | null>(null)
  const [vaultAtRoot, setVaultAtRoot] = useState(0)
  const [hasProjectsHub, setHasProjectsHub] = useState(false)
  const [i18nSummary, setI18nSummary] = useState<I18nSiteSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [aRes, tRes] = await Promise.all([
        fetch('/api/admin/menus/primary/structure-alignment'),
        fetch('/api/admin/site-tree'),
      ])
      const aJson = await aRes.json()
      const tJson = await tRes.json()
      if (!aRes.ok) throw new Error(aJson.error || 'Analyse menu')
      if (!tRes.ok) throw new Error(tJson.error || 'Arbre')
      setI18nSummary(tJson.i18nSummary ?? null)
      setAlign({
        orderMatchesNavTree: aJson.orderMatchesNavTree,
        missingMenuPageIds: aJson.missingMenuPageIds ?? [],
        warnings: aJson.warnings ?? [],
      })
      const tree = tJson.tree
      if (Array.isArray(tree) && tree.length) {
        const meta = analyzeSiteTreeStructure(tree)
        setVaultAtRoot(meta.vaultPagesAtRoot)
        setHasProjectsHub(meta.hasProjectsHub)
      } else {
        setVaultAtRoot(0)
        setHasProjectsHub(false)
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur')
      setAlign(null)
      setI18nSummary(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!active) return
    void load()
  }, [active, load])

  if (!active) return null

  const warnCount =
    align?.warnings.filter((w) => w.severity === 'warning').length ?? 0
  const menuCoherent =
    align &&
    align.orderMatchesNavTree &&
    align.missingMenuPageIds.length === 0 &&
    warnCount === 0

  return (
    <div className="mb-4 rounded-xl border border-slate-200/80 bg-gradient-to-br from-slate-50 to-white p-4 shadow-sm transition-shadow hover:shadow-md">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <LayoutDashboard className="h-5 w-5 text-indigo-600" />
          <div>
            <h3 className="text-sm font-semibold text-slate-900">État du site</h3>
            <p className="text-[11px] text-slate-500">
              Vue rapide : menu, pages visibles, offres vault.
              {onOpenMenusTab && (
                <>
                  {' '}
                  <button
                    type="button"
                    onClick={onOpenMenusTab}
                    className="font-medium text-indigo-600 hover:underline"
                  >
                    Ouvrir l’édition Menus
                  </button>{' '}
                  pour harmoniser.
                </>
              )}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-1 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </button>
      </div>

      {error && (
        <p className="mt-2 text-xs text-red-600">{error}</p>
      )}

      {i18nSummary && !error && (
        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3">
          <Languages className="h-4 w-4 shrink-0 text-indigo-600" />
          <span className="text-[11px] font-semibold text-slate-700">Traduction (aperçu)</span>
          <span className="rounded-full bg-white px-3 py-1 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200">
            Pages avec sections : {i18nSummary.pagesWithSections}
          </span>
          <span className="rounded-full bg-amber-50 px-3 py-1 text-[11px] font-medium text-amber-950 ring-1 ring-amber-100">
            Sans EN : {i18nSummary.missingEn}
          </span>
          <span className="rounded-full bg-amber-50 px-3 py-1 text-[11px] font-medium text-amber-950 ring-1 ring-amber-100">
            Sans IT : {i18nSummary.missingIt}
          </span>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-[11px] font-medium text-slate-800">
            Partiel EN / IT : {i18nSummary.partialEn} / {i18nSummary.partialIt}
          </span>
          <span className="rounded-full bg-violet-50 px-3 py-1 text-[11px] font-medium text-violet-950 ring-1 ring-violet-100">
            Vault sans EN : {i18nSummary.vaultMissingEn}
          </span>
          <span className="rounded-full bg-violet-50 px-3 py-1 text-[11px] font-medium text-violet-950 ring-1 ring-violet-100">
            Vault sans IT : {i18nSummary.vaultMissingIt}
          </span>
          <span className="rounded-full bg-slate-50 px-3 py-1 text-[11px] text-slate-600 ring-1 ring-slate-200">
            Sans sections : {i18nSummary.pagesNoSections}
          </span>
        </div>
      )}

      {align && !error && (
        <div className="mt-3 flex flex-wrap gap-2">
          <span
            className={`inline-flex items-center gap-1 rounded-full px-3 py-1 text-[11px] font-medium ${
              menuCoherent
                ? 'bg-emerald-100 text-emerald-900'
                : 'bg-amber-100 text-amber-900'
            }`}
          >
            {menuCoherent ? (
              <CheckCircle2 className="h-3.5 w-3.5" />
            ) : (
              <AlertCircle className="h-3.5 w-3.5" />
            )}
            Menu vs structure : {menuCoherent ? 'cohérent' : 'à vérifier'}
          </span>
          <span className="rounded-full bg-white px-3 py-1 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200">
            Pages nav absentes du menu : {align.missingMenuPageIds.length}
          </span>
          <span
            className={`rounded-full px-3 py-1 text-[11px] font-medium ${
              vaultAtRoot > 0
                ? 'bg-amber-100 text-amber-900'
                : 'bg-slate-100 text-slate-700'
            }`}
          >
            Vaults à la racine : {vaultAtRoot}
            {!hasProjectsHub && vaultAtRoot > 0 ? ' (pas de hub projects)' : ''}
          </span>
          <span className="rounded-full bg-white px-3 py-1 text-[11px] font-medium text-slate-700 ring-1 ring-slate-200">
            Alertes : {align.warnings.length}
          </span>
        </div>
      )}
    </div>
  )
}
