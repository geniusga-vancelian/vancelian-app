'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Cog, ExternalLink, Loader2, Unlink } from 'lucide-react'

import { toastError, toastSuccess } from '@/lib/admin/toast'

type EnginePayload = {
  packagedProductId: string
  productType: string
  engineType: string | null
  engineReferenceId: string | null
  lendingPoolProduct: {
    id: string
    lendingPoolId: string
    title: string
    status: string
    asset: string
    borrowerClientId: string
    targetSize: unknown
    currentRaised: unknown
    supplyAprBps: unknown
    projectId: string | null
    packagedProductId: string | null
  } | null
  lendingSnapshot: Record<string, unknown> | null
}

type AvailableRow = {
  id: string
  title: string
  asset: string
  status: string
  targetSize: unknown
  currentRaised: unknown
  borrowerClientId: string
  projectId: string | null
}

export interface PackagedEngineLendingSectionProps {
  packagedProductId: string | null
  /** Type courant (brouillon ou serveur) — EXCLUSIVE_OFFER requis pour le lending. */
  productType: string
  hasPackagedRow: boolean
  onRefresh: () => Promise<void>
}

function num(v: unknown): number {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string') {
    const n = parseFloat(v)
    return Number.isFinite(n) ? n : 0
  }
  return 0
}

export function PackagedEngineLendingSection({
  packagedProductId,
  productType,
  hasPackagedRow,
  onRefresh,
}: PackagedEngineLendingSectionProps) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<EnginePayload | null>(null)
  const [engineChoice, setEngineChoice] = useState<'none' | 'lending'>('none')

  const [createOpen, setCreateOpen] = useState(false)
  const [createSubmitting, setCreateSubmitting] = useState(false)
  const [borrowerId, setBorrowerId] = useState('')
  const [asset, setAsset] = useState('USDC')
  const [targetSize, setTargetSize] = useState('100000')
  const [title, setTitle] = useState('')
  const [supplyAprBps, setSupplyAprBps] = useState('300')
  const [borrowAprBps, setBorrowAprBps] = useState('500')

  const [linkOpen, setLinkOpen] = useState(false)
  const [linkSearch, setLinkSearch] = useState('')
  const [linkLoading, setLinkLoading] = useState(false)
  const [linkItems, setLinkItems] = useState<AvailableRow[]>([])
  const [linkSubmitting, setLinkSubmitting] = useState(false)
  const [unlinking, setUnlinking] = useState(false)

  const loadEngine = useCallback(async () => {
    if (!packagedProductId) {
      setData(null)
      return
    }
    setLoading(true)
    try {
      const res = await fetch(`/api/admin/packaged-products/${packagedProductId}/engine`, {
        credentials: 'include',
      })
      const json = (await res.json()) as EnginePayload & { error?: string }
      if (!res.ok) {
        throw new Error(json.error || `Erreur ${res.status}`)
      }
      setData(json)
      setEngineChoice(json.engineType === 'LENDING' ? 'lending' : 'none')
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Chargement moteur impossible')
      setData(null)
    } finally {
      setLoading(false)
    }
  }, [packagedProductId])

  useEffect(() => {
    void loadEngine()
  }, [loadEngine])

  const linked = Boolean(data?.lendingPoolProduct && data.engineType === 'LENDING')
  const snapshot = data?.lendingSnapshot
  const incompatible = productType !== 'EXCLUSIVE_OFFER'

  const handleCreate = async () => {
    if (!packagedProductId) return
    if (incompatible) {
      toastError('Passez le type de produit à « Offre exclusive » (EXCLUSIVE_OFFER) dans Product Settings.')
      return
    }
    setCreateSubmitting(true)
    try {
      const res = await fetch(`/api/admin/packaged-products/${packagedProductId}/engine/lending/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          borrower_client_id: borrowerId.trim(),
          asset: asset.trim(),
          target_size: parseFloat(targetSize),
          title: title.trim() || null,
          supply_apr_bps: parseFloat(supplyAprBps) || 300,
          borrow_apr_bps: parseFloat(borrowAprBps) || 500,
        }),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) {
        const msg =
          typeof json.detail === 'string'
            ? json.detail
            : typeof json.error === 'string'
              ? json.error
              : `Erreur ${res.status}`
        throw new Error(msg)
      }
      toastSuccess('Produit lending créé et lié au registre.')
      setCreateOpen(false)
      await onRefresh()
      await loadEngine()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Création impossible')
    } finally {
      setCreateSubmitting(false)
    }
  }

  const searchAvailable = async () => {
    setLinkLoading(true)
    try {
      const qs = new URLSearchParams({ limit: '30' })
      if (linkSearch.trim()) qs.set('q', linkSearch.trim())
      const res = await fetch(`/api/admin/lending-pool-products/available?${qs}`, { credentials: 'include' })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Recherche impossible')
      setLinkItems(json.items ?? [])
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Recherche impossible')
    } finally {
      setLinkLoading(false)
    }
  }

  const handleLink = async (lendingProductId: string) => {
    if (!packagedProductId) return
    setLinkSubmitting(true)
    try {
      const res = await fetch(`/api/admin/packaged-products/${packagedProductId}/engine/lending/link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ lending_product_id: lendingProductId }),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(typeof json.error === 'string' ? json.error : `Erreur ${res.status}`)
      }
      toastSuccess('Produit lending lié.')
      setLinkOpen(false)
      await onRefresh()
      await loadEngine()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Liaison impossible')
    } finally {
      setLinkSubmitting(false)
    }
  }

  const handleUnlink = async () => {
    if (!packagedProductId) return
    if (!window.confirm('Délier ce produit lending du registre ? (réservé au statut « draft » côté lending)')) {
      return
    }
    setUnlinking(true)
    try {
      const res = await fetch(`/api/admin/packaged-products/${packagedProductId}/engine/lending`, {
        method: 'DELETE',
        credentials: 'include',
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(typeof json.error === 'string' ? json.error : `Erreur ${res.status}`)
      }
      toastSuccess('Liaison supprimée.')
      await onRefresh()
      await loadEngine()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Déliaison impossible')
    } finally {
      setUnlinking(false)
    }
  }

  if (!hasPackagedRow) {
    return (
      <div className="border border-slate-200 rounded-lg p-4 bg-slate-50 text-sm text-slate-700">
        <div className="font-medium text-slate-900 flex items-center gap-2">
          <Cog className="w-4 h-4" />
          Moteur (Engine)
        </div>
        <p className="mt-2 text-xs">
          Enregistrez d’abord le produit packagé (Product Settings) pour configurer le moteur lending.
        </p>
      </div>
    )
  }

  return (
    <div className="border border-slate-200 rounded-lg p-4 space-y-4 bg-white">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <Cog className="w-4 h-4 text-slate-600" />
            Moteur (Engine)
          </h3>
          <p className="text-xs text-gray-600 mt-1">
            Liaison avec le moteur lending exclusif — le registre reste la source catalogue, le lending la source
            investissement.
          </p>
        </div>
        {packagedProductId && (
          <button
            type="button"
            onClick={() => void loadEngine()}
            disabled={loading}
            className="text-xs px-2 py-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-50"
          >
            Actualiser
          </button>
        )}
      </div>

      {incompatible && (
        <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          <span className="font-medium">Attention :</span> le lending est prévu pour le type{' '}
          <code className="font-mono">EXCLUSIVE_OFFER</code>. Type actuel :{' '}
          <code className="font-mono">{productType}</code>.
        </div>
      )}

      <div>
        <label className="block text-xs font-medium text-gray-700 mb-1">Type de moteur</label>
        <select
          value={engineChoice}
          onChange={(e) => {
            const v = e.target.value as 'none' | 'lending'
            if (linked && v === 'none') {
              toastError('Déliez d’abord le produit lending (bouton Délier) avant de passer à « Aucun ».')
              return
            }
            setEngineChoice(v)
          }}
          className="w-full max-w-md px-3 py-2 border rounded-md text-sm"
        >
          <option value="none">Aucun</option>
          <option value="lending">Lending (offre exclusive)</option>
        </select>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Loader2 className="w-4 h-4 animate-spin" />
          Chargement…
        </div>
      )}

      {engineChoice === 'lending' && !loading && (
        <div className="space-y-4 border-t border-gray-100 pt-4">
          {!linked && (
            <p className="text-sm text-gray-700">
              <span className="font-medium text-gray-900">Aucun produit lending lié</span> — créez-en un ou liez un
              existant (sans packaged_product).
            </p>
          )}

          {linked && data?.lendingPoolProduct && (
            <div className="rounded-md border border-emerald-200 bg-emerald-50/60 p-3 space-y-2">
              <div className="text-sm font-medium text-emerald-900">Produit lending lié</div>
              <div className="text-xs font-mono text-gray-800 space-y-1">
                <div>
                  <span className="text-gray-500">lending_product_id</span> {data.lendingPoolProduct.id}
                </div>
                <div>
                  <span className="text-gray-500">pool_id</span> {data.lendingPoolProduct.lendingPoolId}
                </div>
                <div>
                  <span className="text-gray-500">statut</span> {data.lendingPoolProduct.status}
                </div>
                {data.lendingPoolProduct.projectId && (
                  <div className="text-amber-800">
                    <span className="text-gray-500">project_id (legacy)</span> {data.lendingPoolProduct.projectId}
                  </div>
                )}
              </div>

              {snapshot && (
                <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs border-t border-emerald-100 pt-2 mt-2">
                  <div>
                    <dt className="text-gray-500">APR supply (%)</dt>
                    <dd>{num(snapshot.supply_apr).toFixed(4)}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Montants</dt>
                    <dd>
                      levé {num(snapshot.current_raised).toLocaleString('fr-FR')} / cible{' '}
                      {num(snapshot.target_size).toLocaleString('fr-FR')} {String(snapshot.asset ?? '')}
                    </dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Investable</dt>
                    <dd>{String(snapshot.status ?? '') === 'fundraising' ? 'oui (fundraising)' : 'non'}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Emprunteur (client)</dt>
                    <dd className="break-all">{String(snapshot.borrower_client_id ?? '')}</dd>
                  </div>
                </dl>
              )}

              <div className="flex flex-wrap gap-2 pt-2">
                <Link
                  href="/admin/custody"
                  className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-gray-300 bg-white hover:bg-gray-50"
                >
                  <ExternalLink className="w-3 h-3" />
                  Admin custody
                </Link>
                <button
                  type="button"
                  onClick={() => void handleUnlink()}
                  disabled={unlinking || data.lendingPoolProduct.status !== 'draft'}
                  className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-40"
                  title={
                    data.lendingPoolProduct.status !== 'draft'
                      ? 'Déliaison réservée au statut draft côté lending'
                      : undefined
                  }
                >
                  <Unlink className="w-3 h-3" />
                  {unlinking ? '…' : 'Délier'}
                </button>
              </div>
            </div>
          )}

          {!linked && (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => setCreateOpen((o) => !o)}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-indigo-600 text-white text-sm hover:bg-indigo-700"
              >
                Créer un produit lending
              </button>
              <button
                type="button"
                onClick={() => {
                  setLinkOpen((o) => !o)
                  if (!linkOpen) void searchAvailable()
                }}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-md border border-gray-300 text-sm hover:bg-gray-50"
              >
                Lier un produit existant
              </button>
            </div>
          )}

          {createOpen && !linked && (
            <div className="rounded-md border border-gray-200 p-3 space-y-2 text-sm">
              <div className="font-medium text-gray-900">Nouveau lending (backend existant)</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                <label className="block">
                  <span className="text-xs text-gray-600">borrower_client_id (UUID)</span>
                  <input
                    value={borrowerId}
                    onChange={(e) => setBorrowerId(e.target.value)}
                    className="w-full mt-0.5 px-2 py-1 border rounded font-mono text-xs"
                    placeholder="UUID pe_clients"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-gray-600">Asset</span>
                  <input
                    value={asset}
                    onChange={(e) => setAsset(e.target.value)}
                    className="w-full mt-0.5 px-2 py-1 border rounded font-mono text-xs"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-gray-600">target_size</span>
                  <input
                    value={targetSize}
                    onChange={(e) => setTargetSize(e.target.value)}
                    className="w-full mt-0.5 px-2 py-1 border rounded font-mono text-xs"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-gray-600">Titre (optionnel)</span>
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    className="w-full mt-0.5 px-2 py-1 border rounded text-xs"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-gray-600">supply_apr_bps</span>
                  <input
                    value={supplyAprBps}
                    onChange={(e) => setSupplyAprBps(e.target.value)}
                    className="w-full mt-0.5 px-2 py-1 border rounded font-mono text-xs"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-gray-600">borrow_apr_bps</span>
                  <input
                    value={borrowAprBps}
                    onChange={(e) => setBorrowAprBps(e.target.value)}
                    className="w-full mt-0.5 px-2 py-1 border rounded font-mono text-xs"
                  />
                </label>
              </div>
              <button
                type="button"
                disabled={createSubmitting || !borrowerId.trim()}
                onClick={() => void handleCreate()}
                className="mt-2 px-3 py-2 rounded-md bg-indigo-600 text-white text-sm disabled:opacity-50"
              >
                {createSubmitting ? 'Création…' : 'Créer via API lending'}
              </button>
            </div>
          )}

          {linkOpen && !linked && (
            <div className="rounded-md border border-gray-200 p-3 space-y-2 text-sm">
              <div className="font-medium text-gray-900">Lier un lending existant</div>
              <div className="flex gap-2">
                <input
                  value={linkSearch}
                  onChange={(e) => setLinkSearch(e.target.value)}
                  placeholder="Recherche titre, asset ou UUID"
                  className="flex-1 px-2 py-1 border rounded text-xs"
                />
                <button
                  type="button"
                  onClick={() => void searchAvailable()}
                  disabled={linkLoading}
                  className="px-2 py-1 rounded border text-xs"
                >
                  {linkLoading ? '…' : 'Chercher'}
                </button>
              </div>
              <ul className="max-h-48 overflow-auto divide-y divide-gray-100 text-xs">
                {linkItems.map((row) => (
                  <li key={row.id} className="py-2 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="font-mono text-gray-800">{row.id}</div>
                      <div>{row.title}</div>
                      <div className="text-gray-500">
                        {row.asset} · {row.status}
                      </div>
                    </div>
                    <button
                      type="button"
                      disabled={linkSubmitting}
                      onClick={() => void handleLink(row.id)}
                      className="px-2 py-1 rounded bg-gray-900 text-white text-xs disabled:opacity-50"
                    >
                      Lier
                    </button>
                  </li>
                ))}
                {linkItems.length === 0 && !linkLoading && (
                  <li className="py-2 text-gray-500">Aucun résultat (produits sans packaged_product).</li>
                )}
              </ul>
            </div>
          )}
        </div>
      )}

      {engineChoice === 'none' && !loading && (
        <p className="text-xs text-gray-500">
          Sélectionnez « Lending » pour créer ou lier un produit. Le catalogue mobile utilise le registre ; les
          montants / statuts viennent du moteur.
        </p>
      )}
    </div>
  )
}
