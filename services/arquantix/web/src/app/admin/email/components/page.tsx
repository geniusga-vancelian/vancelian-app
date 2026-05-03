'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Code2, Copy } from 'lucide-react'

interface ComponentMeta {
  id: string
  kind: 'section' | 'inline'
  description: string
  vars: Record<string, unknown>
}

const KIND_LABEL: Record<ComponentMeta['kind'], { label: string; color: string }> = {
  section: { label: 'Section', color: 'bg-purple-100 text-purple-800' },
  inline: { label: 'Inline', color: 'bg-blue-100 text-blue-800' },
}

export default function EmailComponentsGalleryPage() {
  const [items, setItems] = useState<ComponentMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<'all' | 'section' | 'inline'>('all')
  const [openVarsFor, setOpenVarsFor] = useState<string | null>(null)

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch('/api/admin/email/components', { cache: 'no-store' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = (await res.json()) as { items: ComponentMeta[] }
        setItems(json.items)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  const filtered = useMemo(
    () => (filter === 'all' ? items : items.filter((c) => c.kind === filter)),
    [items, filter],
  )

  return (
    <div className="space-y-6 max-w-6xl">
      <div className="flex items-center gap-3">
        <Link
          href="/admin/email"
          className="text-gray-500 hover:text-gray-900 inline-flex items-center gap-1 text-sm"
        >
          <ArrowLeft className="w-4 h-4" /> Hub
        </Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-2xl font-bold text-gray-900">Components MJML</h1>
      </div>
      <p className="text-sm text-gray-600 max-w-3xl">
        Composants Mustache réutilisables (chargés automatiquement depuis{' '}
        <code className="font-mono text-xs">emails/mjml/components/</code>). Utilisation
        dans un template :{' '}
        <code className="font-mono text-xs bg-gray-100 px-1.5 py-0.5 rounded">
          {'{{#section}}{{> ComponentName}}{{/section}}'}
        </code>
      </p>

      <div className="flex gap-2">
        {(['all', 'section', 'inline'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 text-sm rounded-full border transition-colors ${
              filter === f
                ? 'bg-gray-900 text-white border-gray-900'
                : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {f === 'all' ? `Tous (${items.length})` : f}
          </button>
        ))}
      </div>

      {loading && <div className="text-gray-500 text-sm">Chargement…</div>}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 text-sm">
          Erreur : {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {filtered.map((c) => (
          <ComponentCard
            key={c.id}
            component={c}
            open={openVarsFor === c.id}
            onToggle={() => setOpenVarsFor(openVarsFor === c.id ? null : c.id)}
          />
        ))}
      </div>
    </div>
  )
}

function ComponentCard({
  component,
  open,
  onToggle,
}: {
  component: ComponentMeta
  open: boolean
  onToggle: () => void
}) {
  const [copied, setCopied] = useState(false)
  const usageSnippet = `{{#${camelToSnake(component.id)}}}{{> ${component.id}}}{{/${camelToSnake(component.id)}}}`
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(usageSnippet)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* refusé */
    }
  }
  const kind = KIND_LABEL[component.kind]

  // Hauteur d'iframe adaptée selon le composant
  const iframeHeight = component.kind === 'inline'
    ? 130
    : component.id === 'HeaderL1' || component.id === 'Footer' || component.id === 'TwoColumns'
      ? 380
      : 240

  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-4 pt-3 pb-2 border-b border-gray-100 flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm font-semibold text-gray-900 truncate">
              {component.id}
            </span>
            <span
              className={`inline-flex px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide rounded ${kind.color}`}
            >
              {kind.label}
            </span>
          </div>
          <div className="text-xs text-gray-500 mt-0.5 line-clamp-2">
            {component.description}
          </div>
        </div>
      </div>

      <div className="bg-gray-50 p-2">
        <iframe
          title={`component-${component.id}`}
          src={`/api/admin/email/components/${component.id}/preview`}
          className="w-full bg-white border border-gray-200 rounded-md"
          style={{ height: iframeHeight }}
        />
      </div>

      <div className="px-4 py-3 border-t border-gray-100 flex items-center justify-between gap-3 flex-wrap">
        <code className="font-mono text-[11px] text-gray-700 bg-gray-100 px-2 py-1 rounded truncate flex-1 min-w-0">
          {usageSnippet}
        </code>
        <div className="flex gap-1">
          <button
            onClick={onCopy}
            className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-gray-300 rounded-md hover:bg-gray-50 text-gray-700"
            title="Copier le snippet d'usage"
          >
            <Copy className="w-3 h-3" />
            {copied ? 'Copié ✓' : 'Copier'}
          </button>
          <button
            onClick={onToggle}
            className="inline-flex items-center gap-1 px-2 py-1 text-xs border border-gray-300 rounded-md hover:bg-gray-50 text-gray-700"
          >
            <Code2 className="w-3 h-3" />
            {open ? 'Masquer vars' : 'Voir vars'}
          </button>
        </div>
      </div>

      {open && (
        <pre className="mx-4 mb-4 max-h-60 overflow-auto bg-gray-900 text-gray-100 text-[11px] leading-relaxed p-3 rounded-md font-mono">
          {JSON.stringify(component.vars, null, 2)}
        </pre>
      )}
    </div>
  )
}

function camelToSnake(s: string): string {
  return s.charAt(0).toLowerCase() + s.slice(1)
}
