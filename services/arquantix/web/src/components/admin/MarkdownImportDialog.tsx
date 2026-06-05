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

type ImportPreview = {
  metadata: {
    title: string
    standfirst: string
    slug?: string
    status: string
    categorySlugs: string[]
    authorName?: string
    metaTitle?: string | null
    metaDescription?: string | null
    seoJson?: Record<string, unknown>
  }
  blocks: Array<{ index: number; type: string; preview: string }>
  blockCount: number
  replaceBlockCount: number
  warnings: Array<{ code: string; messageFr: string }>
}

export type MarkdownImportDialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  articleId: string
  locale: Locale
  onApplied: () => void | Promise<void>
}

export function MarkdownImportDialog({
  open,
  onOpenChange,
  articleId,
  locale,
  onApplied,
}: MarkdownImportDialogProps) {
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

  const runImport = async (markdown: string, mode: 'preview' | 'apply') => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/admin/articles/${articleId}/import-markdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ markdown, locale, mode }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(data.error || data.message || 'Import impossible')
      }
      return data
    } finally {
      setLoading(false)
    }
  }

  const handleFile = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.md')) {
      setError('Seuls les fichiers .md sont acceptés.')
      return
    }
    const text = await file.text()
    setPendingMarkdown(text)
    try {
      const data = await runImport(text, 'preview')
      setPreview(data as ImportPreview)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Erreur')
      setPreview(null)
    }
  }

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) void handleFile(file)
  }

  const applyImport = async () => {
    if (!pendingMarkdown) return
    await runImport(pendingMarkdown, 'apply')
    await onApplied()
    handleClose()
  }

  return (
    <>
      <Dialog open={open} onOpenChange={(v) => (v ? onOpenChange(true) : handleClose())}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Importer un Markdown</DialogTitle>
            <DialogDescription>
              Blueprint CMS : metadata, SEO et blocs. Remplacement total des Content Blocks.
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
              <div className="rounded border border-gray-200 bg-gray-50 p-3">
                <p className="font-medium text-gray-900">{preview.metadata.title}</p>
                {preview.metadata.standfirst ? (
                  <p className="mt-1 text-xs italic text-gray-600">{preview.metadata.standfirst}</p>
                ) : null}
                <ul className="mt-2 space-y-0.5 text-xs text-gray-600">
                  {preview.metadata.slug ? <li>slug: {preview.metadata.slug}</li> : null}
                  <li>status: {preview.metadata.status}</li>
                  <li>locale: {locale}</li>
                  {preview.metadata.authorName ? <li>auteur: {preview.metadata.authorName}</li> : null}
                  {preview.metadata.categorySlugs.length ? (
                    <li>catégories: {preview.metadata.categorySlugs.join(', ')}</li>
                  ) : null}
                </ul>
              </div>

              <p className="text-xs font-medium text-gray-700">
                {preview.replaceBlockCount > 0
                  ? `Remplacement : ${preview.replaceBlockCount} → ${preview.blockCount} bloc(s)`
                  : `${preview.blockCount} bloc(s)`}
              </p>

              <ol className="list-decimal space-y-1 pl-5 text-xs text-gray-700">
                {preview.blocks.map((b) => (
                  <li key={b.index}>
                    <span className="font-mono text-[10px] text-indigo-700">{b.type}</span> {b.preview || '—'}
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
                  disabled={loading}
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
        description={`Remplacer tous les blocs (${preview?.replaceBlockCount ?? 0} actuel(s)) et mettre à jour metadata + SEO pour ${locale.toUpperCase()} ?`}
        confirmLabel="Confirmer"
        cancelLabel="Annuler"
        destructive={false}
        onConfirm={applyImport}
      />
    </>
  )
}
