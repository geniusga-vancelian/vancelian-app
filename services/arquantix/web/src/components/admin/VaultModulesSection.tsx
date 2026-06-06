'use client'

import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ChevronDown, Download, FileUp, Plus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { getVaultModuleLabel, getVaultModuleSummary } from '@/lib/admin/vaultModuleCatalog'

export interface VaultModuleRow {
  id: string
  type: string
  enabled: boolean
  content: Record<string, unknown>
}

export interface VaultModulesSectionProps {
  modules: VaultModuleRow[]
  onReorderModules: (orderedModuleIds: string[]) => void
  onDeleteModule: (moduleId: string) => void
  onToggleEnabled?: (moduleId: string, enabled: boolean) => void
  onClickAddModule: () => void | Promise<void>
  /** Export Markdown des modules (section content blocks). */
  onClickExportMarkdown?: () => void
  /** Import Markdown blueprint modules. */
  onClickImportMarkdown?: () => void
  saving?: boolean
  entityId: string
  title?: string
  /** Désactive supprimer / réordonner pour certains modules (ex. requis produit). */
  isModuleLocked?: (module: VaultModuleRow) => boolean
  renderModuleEditor: (module: VaultModuleRow) => ReactNode
}

/**
 * Liste de modules vault repliable — mêmes conventions que {@link ContentBlocksSection}
 * (carte blanche, compteur, tout déplier/replier, bouton indigo « Ajouter »).
 * Spécifique vault : case à cocher « actif » et résumés adaptés au JSON module.
 */
export function VaultModulesSection({
  modules,
  onReorderModules,
  onDeleteModule,
  onToggleEnabled,
  onClickAddModule,
  onClickExportMarkdown,
  onClickImportMarkdown,
  saving = false,
  entityId,
  title = 'Modules du vault',
  isModuleLocked,
  renderModuleEditor,
}: VaultModulesSectionProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set())
  const collapseInitRef = useRef<string | null>(null)

  useEffect(() => {
    if (!entityId || collapseInitRef.current === entityId) return
    if (modules.length === 0) return
    collapseInitRef.current = entityId
    if (modules.length > 5) {
      setCollapsed(new Set(modules.map((m) => m.id)))
    }
  }, [entityId, modules])

  const toggleCollapsed = (id: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const allCollapsed = modules.length > 0 && modules.every((m) => collapsed.has(m.id))

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          {modules.length > 0 ? (
            <span className="text-xs text-gray-500">{modules.length} module(s)</span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {modules.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCollapsed(allCollapsed ? new Set() : new Set(modules.map((m) => m.id)))}
            >
              {allCollapsed ? 'Tout déplier' : 'Tout replier'}
            </Button>
          ) : null}
          {onClickExportMarkdown ? (
            <Button
              variant="outline"
              size="sm"
              disabled={saving || modules.length === 0}
              onClick={onClickExportMarkdown}
              title="Télécharger les modules au format Markdown"
            >
              <Download className="mr-1 h-4 w-4" /> Export Markdown
            </Button>
          ) : null}
          {onClickImportMarkdown ? (
            <Button
              variant="outline"
              size="sm"
              disabled={saving}
              onClick={onClickImportMarkdown}
              title="Importer un fichier .md (modules vault uniquement)"
            >
              <FileUp className="mr-1 h-4 w-4" /> Importer un Markdown
            </Button>
          ) : null}
          <Button
            size="sm"
            className="bg-indigo-600 hover:bg-indigo-700"
            disabled={saving}
            onClick={() => void onClickAddModule()}
            title="Ouvrir le catalogue de modules"
          >
            <Plus className="mr-1 h-4 w-4" /> Ajouter un module
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {modules.length === 0 ? (
          <p className="text-gray-500 text-center py-8">
            Aucun module pour l’instant. Ajoutez votre premier module depuis le catalogue.
          </p>
        ) : (
          modules.map((module, index) => {
            const isCollapsed = collapsed.has(module.id)
            const summary = getVaultModuleSummary(module)
            const typeLabel = getVaultModuleLabel(module.type)
            const locked = isModuleLocked?.(module) ?? false
            return (
              <div key={module.id} className="rounded-lg border border-gray-200 bg-white">
                <div className="flex items-center gap-2 p-2">
                  <button
                    type="button"
                    onClick={() => toggleCollapsed(module.id)}
                    className="rounded p-1 text-gray-500 hover:bg-gray-100"
                    title={isCollapsed ? 'Déplier' : 'Replier'}
                    aria-expanded={!isCollapsed}
                  >
                    <ChevronDown
                      className={`h-4 w-4 transition-transform ${isCollapsed ? '-rotate-90' : ''}`}
                    />
                  </button>
                  <span className="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-600">
                    {typeLabel}
                  </span>
                  {locked ? (
                    <span className="shrink-0 text-[10px] font-semibold uppercase tracking-wide text-indigo-600 bg-indigo-100 px-1.5 py-0.5 rounded">
                      requis
                    </span>
                  ) : null}
                  <button
                    type="button"
                    onClick={() => toggleCollapsed(module.id)}
                    className="min-w-0 flex-1 truncate text-left text-sm text-gray-900 hover:text-indigo-700"
                    title={summary}
                  >
                    {summary}
                  </button>
                  {onToggleEnabled ? (
                    <label className="shrink-0 text-xs inline-flex items-center gap-1 text-gray-600">
                      <input
                        type="checkbox"
                        checked={module.enabled}
                        disabled={locked}
                        onChange={(e) => onToggleEnabled(module.id, e.target.checked)}
                      />
                      actif
                    </label>
                  ) : null}
                  <div className="flex shrink-0 items-center gap-0.5">
                    {index > 0 && (
                      <button
                        type="button"
                        onClick={() => {
                          const next = [...modules]
                          ;[next[index], next[index - 1]] = [next[index - 1], next[index]]
                          onReorderModules(next.map((m) => m.id))
                        }}
                        className="rounded p-1 text-gray-500 hover:bg-gray-100"
                        title="Monter"
                      >
                        ↑
                      </button>
                    )}
                    {index < modules.length - 1 && (
                      <button
                        type="button"
                        onClick={() => {
                          const next = [...modules]
                          ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
                          onReorderModules(next.map((m) => m.id))
                        }}
                        className="rounded p-1 text-gray-500 hover:bg-gray-100"
                        title="Descendre"
                      >
                        ↓
                      </button>
                    )}
                    {!locked && (
                      <button
                        type="button"
                        onClick={() => {
                          if (!window.confirm('Supprimer ce module ?')) return
                          onDeleteModule(module.id)
                        }}
                        className="rounded px-2 py-0.5 text-xs text-red-600 hover:bg-red-50"
                        title="Supprimer ce module"
                      >
                        Supprimer
                      </button>
                    )}
                  </div>
                </div>
                {!isCollapsed ? (
                  <div className="space-y-2 border-t border-gray-100 p-3">{renderModuleEditor(module)}</div>
                ) : null}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
