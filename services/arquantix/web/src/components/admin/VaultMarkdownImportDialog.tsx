'use client'

import { useCallback, useRef, useState } from 'react'
import { Upload, Loader2, AlertTriangle, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ConfirmDialog } from '@/components/admin/ConfirmDialog'
import type { Locale } from '@/config/locales'
import {
  parseVaultModulesMarkdown,
  summarizeVaultModuleImportPreview,
  vaultModulesToLandingModules,
} from '@/lib/admin/markdownVaultModulesBlueprint'

type ImportPreview = {
  modules: ReturnType<typeof summarizeVaultModuleImportPreview>
  moduleCount: number
  replaceModuleCount: number
  warnings: Array<{ code: string; messageFr: string }>
}

export type VaultMarkdownImportDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  locale: Locale
  currentModuleCount: number
  onApplied: (
    modules: Array<{ id: string; type: string; enabled: boolean; content: Record<string, unknown> }>,
  ) => void | Promise<void>
}

export function VaultMarkdownImportDialog({
  open,
  onOpenChange,
  locale,
  currentModuleCount,
  onApplied,
}: VaultMarkdownImportDialogProps) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [preview, setPreview] = useState<ImportPreview | null>(null)
  const [pendingMarkdown, setPendingMarkdown] = useState<string | null>(null)
  const [confirmApply, setConfirmApply] = useState(false)

  const reset = useCallback(() => {
    setPreview(null)
    setPendingMarkdown(null)
    setError(null)
  }, [])

  const handleClose = () => {
    reset()
    onOpenChange(false)
  }

  const buildPreview = (markdown: string): ImportPreview => {
    const result = parseVaultModulesMarkdown(markdown, locale)
    if (result.warnings.some((w) => w.code === 'YAML_INVALID')) {
      throw new Error('Frontmatter YAML invalide.')
    }
    if (result.modules.length === 0 && !result.warnings.some((w) => w.code === 'BODY_EMPTY')) {
      throw new Error('Aucun module valide trouvé dans le fichier.')
    }
    return {
      modules: summarizeVaultModuleImportPreview(result.modules),
      moduleCount: result.modules.length,
      replaceModuleCount: currentModuleCount,
      warnings: result.warnings.map((w) => ({ code: w.code, messageFr: w.messageFr })),
    }
  }

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.md')) {
      setError('Seuls les fichiers .md sont acceptés.')
      return
    }
    const text = await file.text()
    setPendingMarkdown(text)
    setLoading(true)
    setError(null)
    try {
      setPreview(buildPreview(text))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur')
      setPreview(null)
    } finally {
      setLoading(false)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) void handleFile(file)
  }

  const applyImport = async () => {
    if (!pendingMarkdown) return
    const result = parseVaultModulesMarkdown(pendingMarkdown, locale)
    const modules = vaultModulesToLandingModules(result.modules)
    await onApplied(modules)
    handleClose()
  }

  return (
    <>
      <Dialog open={open} onOpenChange={(v) => (v ? onOpenChange(true) : handleClose())}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Importer un Markdown</DialogTitle>
            <DialogDescription>
              Blueprint Vault Builder : modules de la section « Modules du vault » uniquement.
              Remplacement total des modules existants.
            </DialogDescription>
          </DialogHeader>

          <button
            type="button"
            className="absolute right-4 top-4 rounded p-1 text-gray-400 hover:bg-gray-100"
            onClick={handleClose}
            aria-label="Fermer"
          >
            <X className="h-4 w-4" />
          </button>

          {!preview ? (
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={onDrop}
              className="flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-gray-300 bg-gray-50 px-4 py-10"
            >
              {loading ? (
                <Loader2 className="h-8 w-8 animate-spin text-indigo-600" />
              ) : (
                <Upload className="h-8 w-8 text-gray-400" />
              )}
              <p className="text-center text-sm text-gray-600">
                Glisser-déposer un fichier <strong>.md</strong> ou{' '}
                <button
                  type="button"
                  className="text-indigo-600 underline"
                  onClick={() => inputRef.current?.click()}
                  disabled={loading}
                >
                  parcourir
                </button>
              </p>
              <input
                ref={inputRef}
                type="file"
                accept=".md,text/markdown"
                className="hidden"
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  if (f) void handleFile(f)
                  e.target.value = ''
                }}
              />
            </div>
          ) : (
            <div className="max-h-[55vh] space-y-3 overflow-y-auto text-sm">
              <p className="text-xs font-medium text-gray-700">
                {preview.replaceModuleCount > 0
                  ? `Remplacement : ${preview.replaceModuleCount} → ${preview.moduleCount} module(s)`
                  : `${preview.moduleCount} module(s)`}
              </p>

              <ol className="list-decimal space-y-1 pl-5 text-xs text-gray-700">
                {preview.modules.map((m) => (
                  <li key={m.index}>
                    <span className="font-mono text-[10px] text-indigo-700">{m.type}</span>{' '}
                    {!m.enabled ? (
                      <span className="text-gray-400">(inactif)</span>
                    ) : null}{' '}
                    {m.preview || m.label || '—'}
                  </li>
                ))}
              </ol>

              {preview.warnings.length > 0 ? (
                <div className="rounded border border-amber-200 bg-amber-50 p-2">
                  <div className="mb-1 flex items-center gap-1 text-amber-900">
                    <AlertTriangle className="h-3.5 w-3.5" />
                    <span className="text-xs font-medium">Avertissements</span>
                  </div>
                  <ul className="space-y-0.5 text-xs text-amber-950">
                    {preview.warnings.map((w, i) => (
                      <li key={`${w.code}-${i}`}>{w.messageFr}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              <div className="flex justify-end gap-2">
                <Button variant="outline" size="sm" onClick={reset} disabled={loading}>
                  Autre fichier
                </Button>
                <Button
                  size="sm"
                  className="bg-indigo-600 hover:bg-indigo-700"
                  disabled={loading || preview.moduleCount === 0}
                  onClick={() => setConfirmApply(true)}
                >
                  Appliquer
                </Button>
              </div>
            </div>
          )}

          {error ? <p className="text-sm text-red-600">{error}</p> : null}
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmApply}
        onOpenChange={setConfirmApply}
        title="Confirmer l’import"
        description={`Remplacer tous les modules du vault (${preview?.replaceModuleCount ?? 0} actuel(s)) par ${preview?.moduleCount ?? 0} module(s) importé(s) ?`}
        confirmLabel="Confirmer"
        cancelLabel="Annuler"
        destructive={false}
        onConfirm={applyImport}
      />
    </>
  )
}
