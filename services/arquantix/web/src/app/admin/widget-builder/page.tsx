'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

type Kind = 'widget' | 'feed'

interface BuilderComponent {
  id: string
  slug: string
  name: string
  schemaJson: Record<string, unknown>
  createdAt: string
}

interface FeedPreviewResponse {
  count: number
  items: Array<Record<string, unknown>>
  params?: Record<string, unknown>
}

const DEFAULT_FEED_JSON = {
  type: 'feed',
  feedType: 'blog_articles',
  source: {
    locale: 'fr',
    categorySlug: '',
    limit: 10,
  },
}

const DEFAULT_WIDGET_JSON = {
  type: 'widget',
  modules: [
    {
      type: 'MarketingCardsSmallSlidingCarrousel_Paysage',
      title: 'Mon module',
      items: [],
    },
  ],
  feedSlugs: [],
}

export default function AdminWidgetBuilderPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [widgets, setWidgets] = useState<BuilderComponent[]>([])
  const [feeds, setFeeds] = useState<BuilderComponent[]>([])

  const [newFeedSlug, setNewFeedSlug] = useState('')
  const [newFeedName, setNewFeedName] = useState('')
  const [newFeedJson, setNewFeedJson] = useState(JSON.stringify(DEFAULT_FEED_JSON, null, 2))

  const [newWidgetSlug, setNewWidgetSlug] = useState('')
  const [newWidgetName, setNewWidgetName] = useState('')
  const [newWidgetJson, setNewWidgetJson] = useState(JSON.stringify(DEFAULT_WIDGET_JSON, null, 2))

  const [savingId, setSavingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [previewByFeedId, setPreviewByFeedId] = useState<Record<string, FeedPreviewResponse | null>>({})

  const widgetCount = widgets.length
  const feedCount = feeds.length

  const allItems = useMemo(
    () => [
      ...feeds.map((f) => ({ ...f, kind: 'feed' as Kind })),
      ...widgets.map((w) => ({ ...w, kind: 'widget' as Kind })),
    ],
    [feeds, widgets]
  )

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const authRes = await fetch('/api/admin/me', { credentials: 'include' })
      const auth = await authRes.json()
      if (!auth?.user) {
        router.push('/admin/login')
        return
      }

      const res = await fetch('/api/admin/widget-builder', { credentials: 'include' })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.error || 'Impossible de charger le Widget Builder')

      const nextFeeds = (data.feeds ?? []) as BuilderComponent[]
      const nextWidgets = (data.widgets ?? []) as BuilderComponent[]
      setFeeds(nextFeeds)
      setWidgets(nextWidgets)

      const nextDrafts: Record<string, string> = {}
      for (const item of [...nextFeeds, ...nextWidgets]) {
        nextDrafts[item.id] = JSON.stringify(item.schemaJson ?? {}, null, 2)
      }
      setDrafts(nextDrafts)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur réseau')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const createItem = async (kind: Kind) => {
    const slug = kind === 'feed' ? newFeedSlug.trim() : newWidgetSlug.trim()
    const name = kind === 'feed' ? newFeedName.trim() : newWidgetName.trim()
    const rawJson = kind === 'feed' ? newFeedJson : newWidgetJson

    if (!slug || !name) {
      setError(`Veuillez renseigner slug + nom pour le ${kind}.`)
      return
    }

    let parsed: Record<string, unknown>
    try {
      parsed = JSON.parse(rawJson) as Record<string, unknown>
    } catch {
      setError(`JSON invalide pour le ${kind}.`)
      return
    }

    setError(null)
    const res = await fetch('/api/admin/widget-builder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ kind, slug, name, schemaJson: parsed }),
    })
    const data = await res.json()
    if (!res.ok) {
      setError(data?.error || `Création ${kind} impossible`)
      return
    }

    if (kind === 'feed') {
      setNewFeedSlug('')
      setNewFeedName('')
      setNewFeedJson(JSON.stringify(DEFAULT_FEED_JSON, null, 2))
    } else {
      setNewWidgetSlug('')
      setNewWidgetName('')
      setNewWidgetJson(JSON.stringify(DEFAULT_WIDGET_JSON, null, 2))
    }
    await loadData()
  }

  const saveItem = async (item: BuilderComponent) => {
    setSavingId(item.id)
    setError(null)
    try {
      const raw = drafts[item.id] ?? '{}'
      const parsed = JSON.parse(raw) as Record<string, unknown>
      const res = await fetch(`/api/admin/widget-builder/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          slug: item.slug,
          name: item.name,
          schemaJson: parsed,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.error || 'Sauvegarde impossible')
      await loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur de sauvegarde')
    } finally {
      setSavingId(null)
    }
  }

  const deleteItem = async (item: BuilderComponent) => {
    const ok = window.confirm(`Supprimer "${item.name}" ?`)
    if (!ok) return

    setDeletingId(item.id)
    setError(null)
    try {
      const res = await fetch(`/api/admin/widget-builder/${item.id}`, {
        method: 'DELETE',
        credentials: 'include',
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.error || 'Suppression impossible')
      await loadData()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur de suppression')
    } finally {
      setDeletingId(null)
    }
  }

  const previewFeed = async (feed: BuilderComponent) => {
    setError(null)
    try {
      const res = await fetch(`/api/admin/widget-builder/feed-preview?id=${encodeURIComponent(feed.id)}`, {
        credentials: 'include',
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data?.error || 'Preview feed impossible')
      setPreviewByFeedId((prev) => ({ ...prev, [feed.id]: data as FeedPreviewResponse }))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Erreur de preview')
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Widget Builder</h1>
          <p className="text-gray-600 mt-1">
            Créez des widgets composés de modules + des feeds SQL/DB réutilisables.
          </p>
        </div>
        <Link
          href="/admin/flutter"
          className="px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-700 hover:bg-gray-50"
        >
          Retour Flutter
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border rounded-lg p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Widgets</p>
          <p className="text-2xl font-semibold text-gray-900">{widgetCount}</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Feeds</p>
          <p className="text-2xl font-semibold text-gray-900">{feedCount}</p>
        </div>
        <div className="bg-white border rounded-lg p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Total</p>
          <p className="text-2xl font-semibold text-gray-900">{widgetCount + feedCount}</p>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-lg font-semibold">Créer un Feed</h2>
          <p className="text-xs text-gray-500">
            `feedType` supportés: `blog_articles`, `blog_crypto_asset`, `research_crypto_asset`, `vaults_by_investment_type`, `top10_news`, `top10_research`, `crypto_bundles`, `top_crypto_mock`, `all_crypto_mock`.
          </p>
          <input
            value={newFeedSlug}
            onChange={(e) => setNewFeedSlug(e.target.value)}
            placeholder="Slug unique (ex: blog-news-fr)"
            className="w-full px-3 py-2 border rounded-md"
          />
          <input
            value={newFeedName}
            onChange={(e) => setNewFeedName(e.target.value)}
            placeholder="Nom (ex: Feed blog actualités FR)"
            className="w-full px-3 py-2 border rounded-md"
          />
          <textarea
            value={newFeedJson}
            onChange={(e) => setNewFeedJson(e.target.value)}
            className="w-full min-h-[200px] p-2 border rounded-md font-mono text-xs"
          />
          <button
            type="button"
            onClick={() => createItem('feed')}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            Créer feed
          </button>
        </section>

        <section className="bg-white border rounded-lg p-4 space-y-3">
          <h2 className="text-lg font-semibold">Créer un Widget</h2>
          <p className="text-xs text-gray-500">
            Un widget référence des modules (ordre d'affichage) et des feedSlugs.
          </p>
          <p className="text-xs text-gray-500">
            Pour `MarketingCardsSmallSlidingCarrousel_Portrait` / `..._Paysage`, vous pouvez aussi définir dans le module : `visibleCardsCount` et `cardAspectRatio` (format `largeur:hauteur`, ex `3:4`).
          </p>
          <p className="text-xs text-gray-500">
            Pour `assets_bundles_module` (Crypto Bundles) : optionnellement `showImageOverlay` (bool). Si `true`, filtre gris sur l&apos;image ; si `false` ou absent, pas d&apos;overlay.
          </p>
          <input
            value={newWidgetSlug}
            onChange={(e) => setNewWidgetSlug(e.target.value)}
            placeholder="Slug unique (ex: widget-saving-vaults-feed)"
            className="w-full px-3 py-2 border rounded-md"
          />
          <input
            value={newWidgetName}
            onChange={(e) => setNewWidgetName(e.target.value)}
            placeholder="Nom (ex: Widget Saving Vaults)"
            className="w-full px-3 py-2 border rounded-md"
          />
          <textarea
            value={newWidgetJson}
            onChange={(e) => setNewWidgetJson(e.target.value)}
            className="w-full min-h-[200px] p-2 border rounded-md font-mono text-xs"
          />
          <button
            type="button"
            onClick={() => createItem('widget')}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
          >
            Créer widget
          </button>
        </section>
      </div>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">Composants créés</h2>
        {loading ? (
          <div className="bg-white border rounded-lg p-4 text-sm text-gray-500">Chargement…</div>
        ) : allItems.length === 0 ? (
          <div className="bg-white border rounded-lg p-4 text-sm text-gray-500">Aucun feed/widget pour le moment.</div>
        ) : (
          <div className="space-y-4">
            {allItems.map((item) => (
              <div key={item.id} className="bg-white border rounded-lg p-4 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="text-sm">
                    <span className="font-semibold text-gray-900">{item.name}</span>
                    <span className="text-gray-500"> ({item.slug})</span>
                    <span className="ml-2 inline-flex items-center rounded border px-2 py-0.5 text-xs">
                      {item.kind}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    {item.kind === 'feed' && (
                      <button
                        type="button"
                        onClick={() => previewFeed(item)}
                        className="px-2 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
                      >
                        Preview feed
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => saveItem(item)}
                      disabled={savingId === item.id}
                      className="px-2 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {savingId === item.id ? 'Sauvegarde…' : 'Sauver'}
                    </button>
                    <button
                      type="button"
                      onClick={() => deleteItem(item)}
                      disabled={deletingId === item.id}
                      className="px-2 py-1 text-sm border border-red-300 text-red-700 rounded hover:bg-red-50 disabled:opacity-50"
                    >
                      Supprimer
                    </button>
                  </div>
                </div>
                <textarea
                  value={drafts[item.id] ?? '{}'}
                  onChange={(e) =>
                    setDrafts((prev) => ({
                      ...prev,
                      [item.id]: e.target.value,
                    }))
                  }
                  className="w-full min-h-[180px] p-2 border rounded-md font-mono text-xs"
                />
                {item.kind === 'feed' && previewByFeedId[item.id] && (
                  <pre className="bg-gray-50 border rounded p-3 text-xs overflow-x-auto">
                    {JSON.stringify(previewByFeedId[item.id], null, 2)}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
