'use client'

import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, LayoutGrid, Save, RefreshCcw } from 'lucide-react'

type JsonObject = Record<string, unknown>

interface DsComponent {
  id: string
  slug: string
  name: string
  schemaJson: JsonObject
}

interface DsChapter {
  id: string
  slug: string
  components: DsComponent[]
}

const LAYOUT_DOC_TO_DB_SLUG: Record<string, string> = {
  DashboardScrollTemplate: 'dashboard_layout',
  OffersScreen: 'offers_layout',
  EuroAccountTemplate: 'euro_account_layout',
  AllTransactionsTemplate: 'all_transactions_layout',
  TransactionDetailTemplate: 'transaction_detail_layout',
  ExclusiveOfferDetailScreen: 'exclusive_offer_detail_layout',
}

export default function AdminFlutterLayoutDetailPage() {
  const params = useParams()
  const doc = (params?.slug as string | undefined) ?? ''
  const dbSlug = LAYOUT_DOC_TO_DB_SLUG[doc]

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [component, setComponent] = useState<DsComponent | null>(null)
  const [jsonStr, setJsonStr] = useState('')
  const [initialJsonStr, setInitialJsonStr] = useState('')

  const isDirty = useMemo(() => jsonStr !== initialJsonStr, [jsonStr, initialJsonStr])

  useEffect(() => {
    let cancelled = false
    async function loadLayout() {
      setLoading(true)
      setError(null)
      setSuccess(null)
      try {
        const auth = await fetch('/api/admin/me', { credentials: 'include' })
        const authJson = await auth.json()
        if (!authJson?.user) {
          if (!cancelled) {
            setError('Session expirée. Reconnectez-vous.')
            setLoading(false)
          }
          return
        }

        if (!dbSlug) {
          if (!cancelled) {
            setError(`Ce layout (${doc}) n'est pas relié à un slug DB éditable.`)
            setLoading(false)
          }
          return
        }

        const res = await fetch('/api/admin/ds-components', { credentials: 'include' })
        if (!res.ok) {
          throw new Error('Impossible de charger les composants DS.')
        }
        const data = (await res.json()) as { chapters?: DsChapter[] }
        const chapters = Array.isArray(data.chapters) ? data.chapters : []
        const chapter = chapters.find((ch) => ch.slug === 'component_ds_flutter')
        const found = chapter?.components?.find((c) => c.slug === dbSlug) ?? null

        if (!found) {
          throw new Error(`Layout DB introuvable pour le slug "${dbSlug}".`)
        }

        const pretty = JSON.stringify(found.schemaJson ?? {}, null, 2)
        if (!cancelled) {
          setComponent(found)
          setJsonStr(pretty)
          setInitialJsonStr(pretty)
          setLoading(false)
        }
      } catch (e) {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : 'Erreur de chargement.')
          setLoading(false)
        }
      }
    }
    loadLayout()
    return () => {
      cancelled = true
    }
  }, [doc, dbSlug])

  const onFormat = () => {
    setSuccess(null)
    setError(null)
    try {
      const parsed = JSON.parse(jsonStr) as JsonObject
      setJsonStr(JSON.stringify(parsed, null, 2))
    } catch {
      setError('JSON invalide. Impossible de formatter.')
    }
  }

  const onSave = async () => {
    if (!component) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const parsed = JSON.parse(jsonStr) as unknown
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
        throw new Error('Le JSON racine doit être un objet.')
      }

      const res = await fetch(`/api/admin/ds-components/${component.id}`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          schemaJson: parsed,
        }),
      })

      const payload = await res.json()
      if (!res.ok) {
        throw new Error(payload?.error || 'Échec de sauvegarde.')
      }

      const pretty = JSON.stringify(payload.schemaJson ?? parsed, null, 2)
      setJsonStr(pretty)
      setInitialJsonStr(pretty)
      setSuccess('JSON enregistré en base avec succès.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec de sauvegarde.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/admin/flutter"
          className="inline-flex items-center gap-2 text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour à Flutter
        </Link>
      </div>

      <h1 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-2">
        <LayoutGrid className="w-7 h-7 text-indigo-600" />
        Layout · {doc}
      </h1>
      <p className="text-gray-600 mb-6">
        Éditez le JSON du layout puis enregistrez directement en base.
      </p>

      {loading ? (
        <div className="bg-white rounded-lg shadow border border-gray-100 p-6 text-gray-500">
          Chargement du layout…
        </div>
      ) : null}

      {error ? (
        <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
          {error}
        </div>
      ) : null}

      {success ? (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
          {success}
        </div>
      ) : null}

      {!loading && component ? (
        <div className="bg-white rounded-lg shadow border border-gray-100 overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 px-4 py-3 bg-gray-50">
            <div className="text-sm text-gray-700">
              <span className="font-medium">{component.name}</span>{' '}
              <span className="text-gray-500">({component.slug})</span>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onFormat}
                className="inline-flex items-center gap-1 rounded border border-gray-200 bg-white px-3 py-1.5 text-sm text-gray-700 hover:bg-gray-50"
              >
                <RefreshCcw className="w-4 h-4" />
                Formatter
              </button>
              <button
                type="button"
                onClick={onSave}
                disabled={saving || !isDirty}
                className="inline-flex items-center gap-1 rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Enregistrement…' : 'Enregistrer'}
              </button>
            </div>
          </div>
          <textarea
            value={jsonStr}
            onChange={(e) => {
              setJsonStr(e.target.value)
              setError(null)
              setSuccess(null)
            }}
            spellCheck={false}
            className="w-full min-h-[65vh] p-4 text-sm font-mono text-gray-800 bg-white outline-none"
          />
        </div>
      ) : null}
    </div>
  )
}
