'use client'

import { useCallback, useMemo, useState } from 'react'
import { ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { VAULT_MODULE_CATALOG } from '@/lib/admin/vaultModuleCatalog'
import { buildVaultModulePreviewMock } from '@/lib/admin/vaultModuleAdminPreviewMock'
import { VaultModuleWeb } from '@/components/exclusive-offer/VaultModuleWeb'

function normalizeCatalogSearch(s: string): string {
  return s
    .trim()
    .toLowerCase()
    .normalize('NFD')
    .replace(/\p{M}/gu, '')
}

export type VaultModuleSelection = {
  type: string
  label: string
  category: string
  description: string
  hint?: string
}

export interface AddVaultModuleModalProps {
  /** Titre principal du header. */
  headerTitle: string
  /** Sous-titre du header. */
  headerSubtitle?: string
  /** Libellé bouton retour (fermeture sans ajouter). */
  backLabel?: string
  /** URL publique optionnelle (fiche projet) — lien « ouvrir dans un nouvel onglet ». */
  publicPreviewHref?: string | null
  onClose: () => void
  onValidate: (selection: VaultModuleSelection) => Promise<void>
}

/**
 * Modale plein écran « Ajouter un module vault » — même ergonomie que
 * {@link AddBlockModal} (catalogue filtrable à gauche, détail + aperçu à droite).
 * L’aperçu utilise {@link VaultModuleWeb} avec des données de démonstration (sans enregistrement).
 */
export function AddVaultModuleModal({
  headerTitle,
  headerSubtitle = 'Sélectionnez un type de module à gauche, lisez la description, puis validez.',
  backLabel = '← Retour à l’éditeur',
  publicPreviewHref,
  onClose,
  onValidate,
}: AddVaultModuleModalProps) {
  const [selected, setSelected] = useState<VaultModuleSelection | null>(null)
  const [catalogQuery, setCatalogQuery] = useState('')
  const [saving, setSaving] = useState(false)

  const filteredCatalog = useMemo(() => {
    const q = normalizeCatalogSearch(catalogQuery)
    if (!q) return VAULT_MODULE_CATALOG
    return VAULT_MODULE_CATALOG.map((cat) => ({
      category: cat.category,
      items: cat.items.filter((it) => {
        const hay = normalizeCatalogSearch(
          [it.label, it.type, it.hint ?? '', it.description ?? '', cat.category].join(' '),
        )
        return hay.includes(q)
      }),
    })).filter((cat) => cat.items.length > 0)
  }, [catalogQuery])

  const select = useCallback(
    (
      it: { type: string; label: string; hint?: string; description?: string },
      category: string,
    ) => {
      setSelected({
        type: it.type,
        label: it.label,
        category,
        description: it.description ?? 'Aucune description disponible.',
        ...(it.hint ? { hint: it.hint } : {}),
      })
    },
    [],
  )

  const previewMod = useMemo(
    () => (selected ? buildVaultModulePreviewMock(selected.type) : null),
    [selected],
  )

  const handleValidate = async () => {
    if (!selected) return
    setSaving(true)
    try {
      await onValidate(selected)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[80] flex flex-col bg-slate-100">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white px-4 py-3 shadow-sm">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            {backLabel}
          </button>
          <div className="min-w-0">
            <h1 className="truncate text-lg font-semibold text-slate-900">{headerTitle}</h1>
            <p className="truncate text-xs text-slate-500">{headerSubtitle}</p>
          </div>
        </div>
      </header>

      <div className="grid min-h-0 min-w-0 flex-1 grid-cols-1 gap-0 md:grid-cols-[minmax(0,3fr)_minmax(0,7fr)]">
        <aside className="flex min-h-0 min-w-0 flex-col overflow-hidden border-r border-slate-200 bg-white">
          <div className="shrink-0 border-b border-slate-100 bg-white px-3 py-2">
            <label htmlFor="add-vault-module-search" className="sr-only">
              Filtrer les modules
            </label>
            <input
              id="add-vault-module-search"
              type="search"
              value={catalogQuery}
              onChange={(e) => setCatalogQuery(e.target.value)}
              placeholder="Rechercher (titre, markdown, FAQ, carrousel…)"
              autoComplete="off"
              className="w-full rounded-md border border-slate-300 bg-white px-2.5 py-1.5 text-xs text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
            {filteredCatalog.length === 0 ? (
              <p className="px-2.5 py-4 text-center text-[11px] text-slate-500">
                Aucun module ne correspond à votre recherche.
              </p>
            ) : (
              <div className="divide-y divide-slate-100">
                {filteredCatalog.map((cat) => (
                  <div key={cat.category}>
                    <div className="sticky top-0 z-[1] bg-slate-100/95 px-2.5 py-1 backdrop-blur-sm">
                      <div className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide text-slate-700">
                        {cat.category}
                      </div>
                    </div>
                    {cat.items.map((it) => {
                      const active = selected?.type === it.type
                      return (
                        <button
                          key={it.type}
                          type="button"
                          title={it.hint ?? it.label}
                          onClick={() => select(it, cat.category)}
                          className={cn(
                            'flex w-full items-start gap-2 border-l-[3px] border-transparent px-2.5 py-2 text-left text-xs transition hover:bg-slate-50',
                            active && 'border-l-indigo-600 bg-indigo-50/70',
                          )}
                        >
                          <div className="min-w-0 flex-1">
                            <div className="truncate font-medium text-slate-900">{it.label}</div>
                            {it.hint ? (
                              <div className="truncate text-[10px] text-slate-500">{it.hint}</div>
                            ) : null}
                          </div>
                          <span className="shrink-0 truncate font-mono text-[10px] text-slate-400">
                            {it.type}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>
        </aside>

        <section className="flex min-h-0 min-w-0 flex-col bg-slate-200/80">
          {!selected ? (
            <div className="flex flex-1 items-center justify-center p-8 text-center text-sm text-slate-500">
              Choisissez un module dans la liste à gauche pour afficher sa description.
              <br />
              <span className="mt-2 block text-xs text-slate-400">
                L’aperçu live du rendu complet est disponible dans le panneau à droite de l’éditeur vault
                (après enregistrement, le site public reflète le brouillon ou le publié selon la résolution de
                contenu).
              </span>
            </div>
          ) : (
            <>
              <div className="shrink-0 border-b border-slate-200 bg-white px-6 py-4 shadow-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600">
                    {selected.category}
                  </span>
                  <h2 className="text-base font-semibold text-slate-900">{selected.label}</h2>
                </div>
                <p className="mt-0.5 font-mono text-xs text-slate-500">{selected.type}</p>
                <p className="mt-3 text-sm leading-relaxed text-slate-700">{selected.description}</p>
              </div>
              <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-slate-200/80">
                <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain">
                  <div className="mx-auto max-w-3xl bg-white px-6 py-6 shadow-sm">
                    <p className="mb-4 rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                      Aperçu avec <span className="font-medium">données de démonstration</span> (images
                      externes, PDF d’exemple, etc.) — le module ajouté repart du contenu par défaut du
                      catalogue.
                    </p>
                    {previewMod ? <VaultModuleWeb mod={previewMod} /> : null}
                  </div>
                </div>
                {publicPreviewHref ? (
                  <div className="shrink-0 border-t border-slate-200 bg-white px-6 py-3">
                    <a
                      href={publicPreviewHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-sm font-medium text-indigo-800 hover:underline"
                    >
                      <ExternalLink className="h-4 w-4 shrink-0" aria-hidden />
                      Ouvrir la fiche projet (vue complète dans l’éditeur / public)
                    </a>
                  </div>
                ) : null}
              </div>
            </>
          )}
        </section>
      </div>

      <footer className="flex shrink-0 flex-wrap items-center justify-end gap-3 border-t border-slate-200 bg-white px-6 py-4 shadow-[0_-4px_12px_rgba(0,0,0,0.06)]">
        <button
          type="button"
          onClick={onClose}
          className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Annuler
        </button>
        <Button
          type="button"
          disabled={!selected || saving}
          onClick={() => void handleValidate()}
          className="min-w-[200px]"
        >
          {saving ? 'Ajout…' : 'Ajouter ce module'}
        </Button>
      </footer>
    </div>
  )
}
