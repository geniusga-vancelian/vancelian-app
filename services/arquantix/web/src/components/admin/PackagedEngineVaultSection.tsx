'use client'

import Link from 'next/link'
import { useCallback, useEffect, useState } from 'react'
import { Cog, ExternalLink, Loader2, Unlink } from 'lucide-react'

import { toastError, toastSuccess } from '@/lib/admin/toast'
import { formatVaultNominalAmount } from '@/lib/portal/morphoVaultFormat'

type EnginePayload = {
  packagedProductId: string
  productType: string
  engineType: string | null
  engineReferenceId: string | null
  vaultEngineSnapshot: Record<string, unknown> | null
}

type AvailableVaultRow = {
  portalConfigId: string
  provider: 'morpho' | 'ledgity'
  integrationMode: string
  vaultAddress: string
  chainId: number
  label: string
  assetSymbol: string
  userApyBps: number | null
  tvlUsd: number | null
  isPublished: boolean
}

export interface PackagedEngineVaultSectionProps {
  packagedProductId: string | null
  productType: string
  hasPackagedRow: boolean
  onRefresh: () => Promise<void>
}

function num(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v
  if (typeof v === 'string') {
    const n = parseFloat(v)
    return Number.isFinite(n) ? n : null
  }
  return null
}

function formatApy(bps: number | null): string {
  if (bps == null) return '—'
  return `${(bps / 100).toFixed(2)} %`
}

export function PackagedEngineVaultSection({
  packagedProductId,
  productType,
  hasPackagedRow,
  onRefresh,
}: PackagedEngineVaultSectionProps) {
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<EnginePayload | null>(null)

  const [linkOpen, setLinkOpen] = useState(false)
  const [linkSearch, setLinkSearch] = useState('')
  const [linkLoading, setLinkLoading] = useState(false)
  const [linkItems, setLinkItems] = useState<AvailableVaultRow[]>([])
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

  const linked = data?.engineType === 'VAULT_ENGINE' && Boolean(data.engineReferenceId)
  const snapshot = data?.vaultEngineSnapshot
  const incompatible =
    productType !== 'VAULT_SIMPLE' && productType !== 'EXCLUSIVE_OFFER'

  const searchAvailable = async () => {
    setLinkLoading(true)
    try {
      const qs = new URLSearchParams({ limit: '40' })
      if (linkSearch.trim()) qs.set('q', linkSearch.trim())
      const res = await fetch(`/api/admin/platform-vaults/available?${qs}`, { credentials: 'include' })
      const json = await res.json()
      if (!res.ok) throw new Error(json.error || 'Recherche impossible')
      setLinkItems(json.items ?? [])
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Recherche impossible')
    } finally {
      setLinkLoading(false)
    }
  }

  const handleLink = async (portalConfigId: string) => {
    if (!packagedProductId) return
    setLinkSubmitting(true)
    try {
      const res = await fetch(`/api/admin/packaged-products/${packagedProductId}/engine/vault/link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ portal_config_id: portalConfigId }),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(typeof json.error === 'string' ? json.error : `Erreur ${res.status}`)
      }
      toastSuccess('Vault plateforme connecté.')
      setLinkOpen(false)
      await onRefresh()
      await loadEngine()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Connexion impossible')
    } finally {
      setLinkSubmitting(false)
    }
  }

  const handleUnlink = async () => {
    if (!packagedProductId) return
    if (!window.confirm('Déconnecter le vault plateforme de cette offre exclusive ?')) {
      return
    }
    setUnlinking(true)
    try {
      const res = await fetch(`/api/admin/packaged-products/${packagedProductId}/engine/vault`, {
        method: 'DELETE',
        credentials: 'include',
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) {
        throw new Error(typeof json.error === 'string' ? json.error : `Erreur ${res.status}`)
      }
      toastSuccess('Vault déconnecté.')
      await onRefresh()
      await loadEngine()
    } catch (e: unknown) {
      toastError(e instanceof Error ? e.message : 'Déconnexion impossible')
    } finally {
      setUnlinking(false)
    }
  }

  if (!hasPackagedRow) {
    return (
      <div className="border border-slate-200 rounded-lg p-4 bg-slate-50 text-sm text-slate-700">
        <div className="font-medium text-slate-900 flex items-center gap-2">
          <Cog className="w-4 h-4" />
          Moteur vault (plateforme)
        </div>
        <p className="mt-2 text-xs">
          Enregistrez d’abord le produit packagé (Product Settings) pour connecter un vault Morpho ou Ledgity.
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
            Moteur vault (plateforme)
          </h3>
          <p className="text-xs text-gray-600 mt-1">
            Le Vault Builder reste la couche marketing. Les dépôts, retraits, intérêts et liquidité proviennent du
            vault décentralisé sélectionné (Morpho, Ledgity, Vancelian/Arquantix, etc.).
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
          <span className="font-medium">Attention :</span> la connexion vault est prévue pour{' '}
          <code className="font-mono">VAULT_SIMPLE</code> ou{' '}
          <code className="font-mono">EXCLUSIVE_OFFER</code>. Type actuel :{' '}
          <code className="font-mono">{productType}</code>.
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Loader2 className="w-4 h-4 animate-spin" />
          Chargement…
        </div>
      )}

      {!loading && linked && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50/60 p-3 space-y-2">
          <div className="text-sm font-medium text-emerald-900">Vault plateforme connecté</div>
          <div className="text-xs font-mono text-gray-800 space-y-1">
            <div>
              <span className="text-gray-500">portal_config_id</span> {data?.engineReferenceId}
            </div>
            {snapshot && (
              <>
                <div>
                  <span className="text-gray-500">vault</span> {String(snapshot.name ?? '')}
                </div>
                <div>
                  <span className="text-gray-500">provider</span> {String(snapshot.provider ?? '')}
                </div>
                <div className="break-all">
                  <span className="text-gray-500">address</span> {String(snapshot.vault_address ?? '')}
                </div>
              </>
            )}
          </div>

          {snapshot && (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs border-t border-emerald-100 pt-2 mt-2">
              <div>
                <dt className="text-gray-500">Actif sous-jacent</dt>
                <dd>{String(snapshot.asset_symbol ?? snapshot.asset ?? '—')}</dd>
              </div>
              <div>
                <dt className="text-gray-500">APY</dt>
                <dd>{formatApy(num(snapshot.user_apy_bps))}</dd>
              </div>
              <div>
                <dt className="text-gray-500">TVL</dt>
                <dd>
                  {formatVaultNominalAmount(
                    num(snapshot.tvl_usd),
                    typeof snapshot.asset_symbol === 'string' ? snapshot.asset_symbol : null,
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Liquidité dispo.</dt>
                <dd>
                  {formatVaultNominalAmount(
                    num(snapshot.available_liquidity_usd),
                    typeof snapshot.asset_symbol === 'string' ? snapshot.asset_symbol : null,
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Investable</dt>
                <dd>{snapshot.investable === true ? 'oui (publié)' : 'non'}</dd>
              </div>
              {snapshot.vault_profile === 'exclusive_offer_locked' ? (
                <>
                  <div>
                    <dt className="text-gray-500">Profil</dt>
                    <dd>Offre exclusive — lock-up (club deal)</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Lock actif</dt>
                    <dd>{snapshot.lock_active === true ? 'oui' : 'non'}</dd>
                  </div>
                  <div className="sm:col-span-2">
                    <dt className="text-gray-500">Maturité / retrait</dt>
                    <dd>
                      {typeof snapshot.lock_status_label === 'string'
                        ? snapshot.lock_status_label
                        : '—'}
                    </dd>
                  </div>
                </>
              ) : null}
            </dl>
          )}

          <div className="flex flex-wrap gap-2 pt-2">
            <Link
              href="/admin/morpho-vaults"
              className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-gray-300 bg-white hover:bg-gray-50"
            >
              <ExternalLink className="w-3 h-3" />
              Admin vaults
            </Link>
            <button
              type="button"
              onClick={() => void handleUnlink()}
              disabled={unlinking}
              className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-40"
            >
              <Unlink className="w-3 h-3" />
              {unlinking ? '…' : 'Déconnecter'}
            </button>
          </div>
        </div>
      )}

      {!loading && !linked && (
        <div className="space-y-3">
          <p className="text-sm text-gray-700">
            <span className="font-medium text-gray-900">Aucun vault connecté</span> — choisissez un vault parmi ceux
            configurés sur la plateforme.
          </p>
          <button
            type="button"
            onClick={() => {
              setLinkOpen((o) => !o)
              if (!linkOpen) void searchAvailable()
            }}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-md bg-indigo-600 text-white text-sm hover:bg-indigo-700"
          >
            Connecter un vault plateforme
          </button>
        </div>
      )}

      {linkOpen && !linked && (
        <div className="rounded-md border border-gray-200 p-3 space-y-2 text-sm">
          <div className="font-medium text-gray-900">Vaults disponibles</div>
          <div className="flex gap-2">
            <input
              value={linkSearch}
              onChange={(e) => setLinkSearch(e.target.value)}
              placeholder="Recherche nom, adresse, asset…"
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
          <ul className="max-h-56 overflow-auto divide-y divide-gray-100 text-xs">
            {linkItems.map((row) => (
              <li key={row.portalConfigId} className="py-2 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-medium text-gray-900">{row.label}</div>
                  <div className="text-gray-600">
                    {row.provider} · {row.assetSymbol} · chain {row.chainId}
                  </div>
                  <div className="font-mono text-gray-500 break-all">{row.vaultAddress}</div>
                  <div className="text-gray-500">
                    APY {formatApy(row.userApyBps)} · TVL{' '}
                    {formatVaultNominalAmount(row.tvlUsd, row.assetSymbol)}
                    {!row.isPublished ? ' · non publié' : ''}
                  </div>
                </div>
                <button
                  type="button"
                  disabled={linkSubmitting}
                  onClick={() => void handleLink(row.portalConfigId)}
                  className="px-2 py-1 rounded bg-gray-900 text-white text-xs disabled:opacity-50"
                >
                  Connecter
                </button>
              </li>
            ))}
            {linkItems.length === 0 && !linkLoading && (
              <li className="py-2 text-gray-500">
                Aucun vault configuré. Ajoutez-en via{' '}
                <Link href="/admin/morpho-vaults" className="underline">
                  Admin vaults
                </Link>
                .
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  )
}
