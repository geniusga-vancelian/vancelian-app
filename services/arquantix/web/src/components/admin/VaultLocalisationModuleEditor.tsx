'use client'

import { useState } from 'react'

import {
  isGoogleMapsIframeEmbedUrl,
  normalizeGoogleMapsEmbedInput,
} from '@/lib/maps/resolveMapsShareLink'

type Props = {
  content: Record<string, unknown>
  onPatch: (patch: Record<string, unknown>) => void
}

function readString(v: unknown): string {
  return typeof v === 'string' ? v : ''
}

function looksLikeGoogleMapsShortShareLink(raw: string): boolean {
  const t = raw.trim()
  if (!t.startsWith('http')) return false
  try {
    const u = new URL(t)
    const h = u.hostname.toLowerCase()
    return h === 'maps.app.goo.gl' || h === 'goo.gl' || h === 'g.co'
  } catch {
    return false
  }
}

/**
 * Module Localisation — titre, description, carte Google (URL d’iframe).
 * Le marketing peut coller le bloc `<iframe …>` fourni par Google (Partager → Intégrer une carte).
 */
export function VaultLocalisationModuleEditor({ content, onPatch }: Props) {
  const moduleTitle = readString(content.moduleTitle)
  const description = readString(content.description)
  const embedUrl = readString(content.embedUrl)
  const embedNorm = normalizeGoogleMapsEmbedInput(embedUrl)
  const previewOk = isGoogleMapsIframeEmbedUrl(embedNorm)
  const [resolving, setResolving] = useState(false)
  const [resolveError, setResolveError] = useState<string | null>(null)

  async function onResolveShortLink() {
    const raw = embedUrl.trim()
    if (!raw) return
    setResolveError(null)
    setResolving(true)
    try {
      const res = await fetch('/api/admin/maps/resolve-share-link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: raw }),
      })
      const data: { ok?: boolean; embedUrl?: string; error?: string } = await res.json()
      if (!res.ok || !data.ok || !data.embedUrl) {
        setResolveError(data.error ?? 'Conversion impossible')
        return
      }
      onPatch({ embedUrl: data.embedUrl })
    } catch {
      setResolveError('Réseau ou serveur indisponible')
    } finally {
      setResolving(false)
    }
  }

  return (
    <div className="mt-2 space-y-2 border-t border-gray-100 pt-3">
      <div className="grid gap-2 sm:grid-cols-2">
        <input
          type="text"
          value={moduleTitle}
          onChange={(e) => onPatch({ moduleTitle: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Titre du module (Localisation)"
        />
        <input
          type="text"
          value={description}
          onChange={(e) => onPatch({ description: e.target.value })}
          className="w-full rounded-md border px-2 py-1.5 text-sm"
          placeholder="Description (affichée au-dessus de la carte)"
        />
      </div>
      <div className="flex gap-1.5">
        <textarea
          value={embedUrl}
          onChange={(e) => onPatch({ embedUrl: e.target.value })}
          onBlur={() => {
            const n = normalizeGoogleMapsEmbedInput(embedUrl)
            if (n !== embedUrl) onPatch({ embedUrl: n })
          }}
          onPaste={(e) => {
            const text = e.clipboardData.getData('text')
            if (/<iframe\b/i.test(text)) {
              e.preventDefault()
              onPatch({ embedUrl: normalizeGoogleMapsEmbedInput(text) })
            }
          }}
          rows={2}
          className="min-h-[4rem] min-w-0 flex-1 resize-y rounded-md border px-2 py-1.5 text-xs font-mono leading-snug"
          placeholder="Collez le code &lt;iframe …&gt; ou l’URL https://www.google.com/maps/embed?…"
        />
        <button
          type="button"
          disabled={resolving || !looksLikeGoogleMapsShortShareLink(embedNorm)}
          onClick={() => void onResolveShortLink()}
          className="shrink-0 rounded-md border border-gray-300 bg-white px-2 py-1.5 text-xs font-medium text-gray-800 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {resolving ? '…' : 'Convertir lien courts'}
        </button>
      </div>
      {resolveError ? <p className="text-xs text-red-600">{resolveError}</p> : null}
      {embedUrl.trim().length > 0 && !previewOk && (
        <p className="text-[11px] text-amber-700">
          Collez le code d&apos;intégration Google (iframe) ou une URL avec{' '}
          <code>/maps/embed</code> / <code>output=embed</code>. Les liens courts{' '}
          <code>maps.app.goo.gl</code> : bouton convertir.
        </p>
      )}
      {previewOk ? (
        <details className="rounded border border-gray-200 bg-gray-50/60">
          <summary className="cursor-pointer list-none px-2 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-100">
            Aperçu carte (le rendu réel s&apos;affiche dans la preview à droite)
          </summary>
          <div className="aspect-video max-h-[240px] overflow-hidden border-t border-gray-200 bg-black">
            <iframe
              title="Aperçu carte"
              src={embedNorm}
              className="h-full min-h-[200px] w-full"
              loading="lazy"
              referrerPolicy="no-referrer-when-downgrade"
              allowFullScreen
            />
          </div>
        </details>
      ) : null}
    </div>
  )
}
