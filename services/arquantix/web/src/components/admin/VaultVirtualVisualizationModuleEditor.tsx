'use client'

import {
  isVirtualVisualizationEmbedUrl,
  normalizeVirtualVisualizationInput,
} from '@/lib/vault/normalizeVirtualVisualizationUrl'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

/**
 * Module visite virtuelle — titre, description, URL du viewer (iframe pleine largeur côté public).
 */
export function VaultVirtualVisualizationModuleEditor({ content, onPatch }: Props) {
  const moduleTitle = readString(content.moduleTitle)
  const description = readString(content.description)
  const visualizationUrl = readString(content.visualizationUrl)
  const urlNorm = normalizeVirtualVisualizationInput(visualizationUrl)
  const previewOk = isVirtualVisualizationEmbedUrl(urlNorm)

  return (
    <div className="mt-2 space-y-2 border-t border-gray-100 pt-3">
      <div className="grid gap-2 sm:grid-cols-2">
        <input
          type="text"
          value={moduleTitle}
          onChange={(e) => onPatch({ moduleTitle: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Titre du module"
        />
        <input
          type="text"
          value={description}
          onChange={(e) => onPatch({ description: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Description (texte au-dessus de la visite)"
        />
      </div>
      <div>
        <label className="mb-0.5 block text-[11px] font-medium text-gray-600">
          Lien de la visite virtuelle (URL du viewer)
        </label>
        <textarea
          value={visualizationUrl}
          onChange={(e) => onPatch({ visualizationUrl: e.target.value })}
          onBlur={() => {
            const n = normalizeVirtualVisualizationInput(visualizationUrl)
            if (n !== visualizationUrl) onPatch({ visualizationUrl: n })
          }}
          onPaste={(e) => {
            const text = e.clipboardData.getData('text')
            if (/<iframe\b/i.test(text)) {
              e.preventDefault()
              onPatch({ visualizationUrl: normalizeVirtualVisualizationInput(text) })
            }
          }}
          rows={2}
          className="min-h-[4rem] w-full resize-y rounded-md border px-2 py-1.5 text-xs font-mono leading-snug"
          placeholder="https://virtual.komavisualization.com/vrViewer/…/"
        />
      </div>
      {visualizationUrl.trim().length > 0 && !previewOk && (
        <p className="text-[11px] text-amber-700">
          URL non reconnue : attendu une adresse http(s) vers le viewer, ou un bloc{' '}
          <code>&lt;iframe …&gt;</code> avec <code>src=</code>.
        </p>
      )}
      {previewOk ? (
        <details className="rounded border border-gray-200 bg-gray-50/60">
          <summary className="cursor-pointer list-none px-2 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100">
            Aperçu intégration (le rendu pleine largeur est sur la fiche / preview)
          </summary>
          <div className="max-h-[280px] overflow-hidden border-t border-gray-200 bg-black">
            <iframe
              title="Aperçu visite virtuelle"
              src={urlNorm}
              className="h-[240px] w-full"
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              allowFullScreen
              allow="accelerometer; gyroscope; fullscreen; xr-spatial-tracking"
            />
          </div>
        </details>
      ) : null}
    </div>
  )
}
