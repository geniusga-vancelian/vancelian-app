'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, ExternalLink, Code2, FileJson } from 'lucide-react'

interface TemplateMeta {
  id: string
  mjmlPath: string
  description: string
  subjectExamples: { fr: string; en: string }
  jsonSchema: unknown
  fixture: Record<string, unknown> | null
}

const LOCALES = ['fr', 'en'] as const

export default function EmailTemplatesGalleryPage() {
  const [items, setItems] = useState<TemplateMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [openSchemaFor, setOpenSchemaFor] = useState<string | null>(null)
  const [openFixtureFor, setOpenFixtureFor] = useState<string | null>(null)
  const [activeLocale, setActiveLocale] = useState<Record<string, 'fr' | 'en'>>({})

  useEffect(() => {
    void (async () => {
      try {
        const res = await fetch('/api/admin/email/templates', { cache: 'no-store' })
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const json = (await res.json()) as { items: TemplateMeta[] }
        setItems(json.items)
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err))
      } finally {
        setLoading(false)
      }
    })()
  }, [])

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
        <h1 className="text-2xl font-bold text-gray-900">Templates MJML</h1>
      </div>
      <p className="text-sm text-gray-600 max-w-3xl">
        Galerie des templates production-ready. Chaque template définit un{' '}
        <strong>schéma Zod strict</strong> (validation des variables, y compris celles
        produites par l’IA) et une <strong>fixture canonique</strong> (données mockées
        pour la preview et les tests).
      </p>

      {loading && <div className="text-gray-500 text-sm">Chargement…</div>}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 text-sm">
          Erreur : {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {items.map((tpl) => {
          const loc = activeLocale[tpl.id] ?? 'fr'
          return (
            <div
              key={tpl.id}
              className="bg-white border border-gray-200 rounded-xl overflow-hidden flex flex-col"
            >
              <div className="px-5 pt-4 pb-3 border-b border-gray-100">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-mono text-sm font-semibold text-gray-900">
                    {tpl.id}
                  </div>
                  <div className="flex gap-1">
                    {LOCALES.map((l) => (
                      <button
                        key={l}
                        onClick={() =>
                          setActiveLocale((prev) => ({ ...prev, [tpl.id]: l }))
                        }
                        className={`px-2 py-0.5 text-xs rounded-full font-medium transition-colors ${
                          loc === l
                            ? 'bg-gray-900 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                      >
                        {l.toUpperCase()}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="text-sm text-gray-500 mt-1">{tpl.description}</div>
                {tpl.subjectExamples[loc] && (
                  <div className="text-xs text-gray-700 mt-2">
                    <span className="text-gray-400">Subject:</span>{' '}
                    <span className="font-medium">{tpl.subjectExamples[loc]}</span>
                  </div>
                )}
              </div>

              <div className="bg-gray-50 p-3">
                <iframe
                  title={`preview-${tpl.id}`}
                  src={`/api/admin/email/preview?templateId=${tpl.id}&locale=${loc}&inline=1`}
                  className="w-full bg-white border border-gray-200 rounded-md"
                  style={{ height: 420 }}
                />
              </div>

              <div className="px-5 py-3 border-t border-gray-100 flex flex-wrap gap-2 items-center justify-between">
                <div className="flex flex-wrap gap-2">
                  <Link
                    href={`/preview/email/${tpl.id}?locale=${loc}`}
                    target="_blank"
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-gray-300 rounded-full hover:bg-gray-50 text-gray-700"
                  >
                    Preview plein écran
                    <ExternalLink className="w-3 h-3" />
                  </Link>
                  <button
                    onClick={() =>
                      setOpenSchemaFor(openSchemaFor === tpl.id ? null : tpl.id)
                    }
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-gray-300 rounded-full hover:bg-gray-50 text-gray-700"
                  >
                    <Code2 className="w-3 h-3" />
                    {openSchemaFor === tpl.id ? 'Masquer schéma' : 'Voir schéma JSON'}
                  </button>
                  <button
                    onClick={() =>
                      setOpenFixtureFor(openFixtureFor === tpl.id ? null : tpl.id)
                    }
                    className="inline-flex items-center gap-1 px-3 py-1.5 text-xs border border-gray-300 rounded-full hover:bg-gray-50 text-gray-700"
                  >
                    <FileJson className="w-3 h-3" />
                    {openFixtureFor === tpl.id ? 'Masquer fixture' : 'Voir fixture'}
                  </button>
                </div>
                <Link
                  href={`/admin/email/ai-builder?template=${tpl.id}`}
                  className="px-3 py-1.5 text-xs bg-gray-900 text-white rounded-full hover:bg-gray-800"
                >
                  Construire avec l’IA →
                </Link>
              </div>

              {openSchemaFor === tpl.id && (
                <pre className="mx-5 mb-4 max-h-72 overflow-auto bg-gray-900 text-gray-100 text-[11px] leading-relaxed p-3 rounded-md font-mono">
                  {JSON.stringify(tpl.jsonSchema, null, 2)}
                </pre>
              )}
              {openFixtureFor === tpl.id && tpl.fixture && (
                <FixtureBlock id={tpl.id} fixture={tpl.fixture} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function FixtureBlock({ id, fixture }: { id: string; fixture: Record<string, unknown> }) {
  const text = useMemo(() => JSON.stringify(fixture, null, 2), [fixture])
  const [copied, setCopied] = useState(false)
  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      /* clipboard refusé */
    }
  }
  return (
    <div className="mx-5 mb-4 relative">
      <button
        onClick={onCopy}
        className="absolute top-2 right-2 px-2 py-0.5 text-[11px] bg-gray-700 text-white rounded hover:bg-gray-600 z-10"
      >
        {copied ? 'Copié ✓' : 'Copier'}
      </button>
      <pre
        title={`fixture-${id}`}
        className="max-h-72 overflow-auto bg-gray-900 text-gray-100 text-[11px] leading-relaxed p-3 rounded-md font-mono"
      >
        {text}
      </pre>
    </div>
  )
}
