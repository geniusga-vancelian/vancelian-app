'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Loader2, Plus, RefreshCw, Save, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { toastError, toastSuccess } from '@/lib/admin/toast'
import type { PortalMorphoCatalogVault } from '@/lib/portal/morphoVaultTypes'
import type { PortalMorphoIntegrationMode } from '@/lib/portal/morphoConstants'
import { formatApyFromDecimal, formatEarnUsd } from '@/lib/portal/morphoVaultFormat'

type AdminMorphoVaultRow = {
  id: string
  vaultAddress: string
  chainId: number
  integrationMode: PortalMorphoIntegrationMode
  privyVaultId?: string | null
  label?: string | null
  description?: string | null
  curator?: string | null
  sortOrder: number
  isPublished: boolean
  name: string
  userApyBps: number | null
  tvlUsd: number | null
}

type DraftRow = {
  label: string
  description: string
  integrationMode: PortalMorphoIntegrationMode
  privyVaultId: string
  sortOrder: string
  isPublished: boolean
}

function emptyDraft(): DraftRow {
  return {
    label: '',
    description: '',
    integrationMode: 'direct_morpho',
    privyVaultId: '',
    sortOrder: '999',
    isPublished: false,
  }
}

export default function AdminMorphoVaultsPage() {
  const [catalog, setCatalog] = useState<PortalMorphoCatalogVault[]>([])
  const [vaults, setVaults] = useState<AdminMorphoVaultRow[]>([])
  const [loading, setLoading] = useState(true)
  const [catalogQuery, setCatalogQuery] = useState('')
  const [drafts, setDrafts] = useState<Record<string, DraftRow>>({})
  const [savingId, setSavingId] = useState<string | null>(null)

  const loadAll = useCallback(async () => {
    setLoading(true)
    try {
      const [catalogRes, vaultsRes] = await Promise.all([
        fetch('/api/admin/morpho-vaults/catalog', { cache: 'no-store' }),
        fetch('/api/admin/morpho-vaults', { cache: 'no-store' }),
      ])
      if (!catalogRes.ok || !vaultsRes.ok) throw new Error('Chargement impossible.')
      const catalogData = (await catalogRes.json()) as { vaults: PortalMorphoCatalogVault[] }
      const vaultsData = (await vaultsRes.json()) as { vaults: AdminMorphoVaultRow[] }
      setCatalog(catalogData.vaults ?? [])
      setVaults(vaultsData.vaults ?? [])
      setDrafts(
        Object.fromEntries(
          (vaultsData.vaults ?? []).map((row) => [
            row.id,
            {
              label: row.label ?? row.name ?? '',
              description: row.description ?? '',
              integrationMode: row.integrationMode,
              privyVaultId: row.privyVaultId ?? '',
              sortOrder: String(row.sortOrder ?? 999),
              isPublished: row.isPublished,
            },
          ]),
        ),
      )
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Erreur de chargement.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadAll()
  }, [loadAll])

  const publishedAddresses = useMemo(
    () => new Set(vaults.map((row) => row.vaultAddress.toLowerCase())),
    [vaults],
  )

  const filteredCatalog = useMemo(() => {
    const q = catalogQuery.trim().toLowerCase()
    return catalog.filter((row) => {
      if (publishedAddresses.has(row.address.toLowerCase())) return false
      if (!q) return true
      return (
        row.name.toLowerCase().includes(q) ||
        row.symbol.toLowerCase().includes(q) ||
        row.asset.symbol.toLowerCase().includes(q) ||
        (row.curator ?? '').toLowerCase().includes(q)
      )
    })
  }, [catalog, catalogQuery, publishedAddresses])

  const addFromCatalog = async (item: PortalMorphoCatalogVault) => {
    try {
      const res = await fetch('/api/admin/morpho-vaults', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vaultAddress: item.address,
          integrationMode: 'direct_morpho',
          label: item.name,
          description: item.description,
          curator: item.curator,
          sortOrder: vaults.length,
          isPublished: false,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'Ajout impossible.')
      }
      toastSuccess(`${item.name} ajouté à la sélection.`)
      await loadAll()
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Ajout impossible.')
    }
  }

  const saveRow = async (row: AdminMorphoVaultRow) => {
    const draft = drafts[row.id]
    if (!draft) return
    setSavingId(row.id)
    try {
      const res = await fetch(`/api/admin/morpho-vaults/${row.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: draft.label,
          description: draft.description,
          integrationMode: draft.integrationMode,
          privyVaultId: draft.privyVaultId || null,
          sortOrder: Number.parseInt(draft.sortOrder, 10) || 999,
          isPublished: draft.isPublished,
        }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'Sauvegarde impossible.')
      }
      toastSuccess('Vault mis à jour.')
      await loadAll()
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Sauvegarde impossible.')
    } finally {
      setSavingId(null)
    }
  }

  const deleteRow = async (row: AdminMorphoVaultRow) => {
    if (!window.confirm(`Retirer ${row.name} de la sélection ?`)) return
    try {
      const res = await fetch(`/api/admin/morpho-vaults/${row.id}`, { method: 'DELETE' })
      if (!res.ok) throw new Error('Suppression impossible.')
      toastSuccess('Vault retiré.')
      await loadAll()
    } catch (error) {
      toastError(error instanceof Error ? error.message : 'Suppression impossible.')
    }
  }

  return (
    <div className="mx-auto max-w-6xl space-y-8 p-8">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Morpho Vaults (Base)</h1>
          <p className="mt-1 max-w-2xl text-sm text-gray-600">
            Sélectionnez les vaults Morpho affichés dans le portail Invest. Chaque vault peut être
            exécuté en mode direct (wallet Privy + contrats ERC-4626) ou via Privy Earn.
          </p>
        </div>
        <Button type="button" variant="outline" onClick={() => void loadAll()} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Actualiser
        </Button>
      </header>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">Catalogue Morpho (Base)</h2>
        <p className="mt-1 text-sm text-gray-600">Vaults listés sur Base via l’API GraphQL Morpho.</p>
        <input
          type="search"
          value={catalogQuery}
          onChange={(e) => setCatalogQuery(e.target.value)}
          placeholder="Rechercher un vault, actif ou curator…"
          className="mt-4 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
        />
        {loading ? (
          <p className="mt-4 flex items-center gap-2 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Chargement…
          </p>
        ) : (
          <div className="mt-4 max-h-80 overflow-y-auto divide-y divide-gray-100">
            {filteredCatalog.slice(0, 50).map((item) => (
              <div key={item.address} className="flex items-center justify-between gap-4 py-3">
                <div className="min-w-0">
                  <p className="truncate font-medium text-gray-900">{item.name}</p>
                  <p className="truncate text-xs text-gray-500">
                    {item.asset.symbol} · {item.version.toUpperCase()} · APY {formatApyFromDecimal(item.netApy)} · TVL{' '}
                    {formatEarnUsd(item.tvlUsd)} · {item.address}
                  </p>
                </div>
                <Button type="button" size="sm" onClick={() => void addFromCatalog(item)}>
                  <Plus className="mr-1 h-4 w-4" />
                  Ajouter
                </Button>
              </div>
            ))}
            {!filteredCatalog.length ? (
              <p className="py-6 text-sm text-gray-500">Aucun vault disponible dans le catalogue.</p>
            ) : null}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900">Vaults configurés</h2>
        <p className="mt-1 text-sm text-gray-600">
          Overrides CMS, mode d’intégration, ordre d’affichage et publication portail.
        </p>

        {loading ? (
          <p className="mt-4 text-sm text-gray-500">Chargement…</p>
        ) : !vaults.length ? (
          <p className="mt-4 text-sm text-gray-500">Aucun vault sélectionné.</p>
        ) : (
          <div className="mt-4 space-y-4">
            {vaults.map((row) => {
              const draft = drafts[row.id] ?? emptyDraft()
              return (
                <article key={row.id} className="rounded-md border border-gray-200 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="font-semibold text-gray-900">{row.name}</h3>
                      <p className="text-xs text-gray-500">{row.vaultAddress}</p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        type="button"
                        size="sm"
                        onClick={() => void saveRow(row)}
                        disabled={savingId === row.id}
                      >
                        <Save className="mr-1 h-4 w-4" />
                        Enregistrer
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => void deleteRow(row)}>
                        <Trash2 className="mr-1 h-4 w-4" />
                        Retirer
                      </Button>
                    </div>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <label className="text-sm text-gray-700">
                      Label portail
                      <input
                        className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                        value={draft.label}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [row.id]: { ...draft, label: e.target.value },
                          }))
                        }
                      />
                    </label>
                    <label className="text-sm text-gray-700">
                      Mode
                      <select
                        className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                        value={draft.integrationMode}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [row.id]: {
                              ...draft,
                              integrationMode: e.target.value as PortalMorphoIntegrationMode,
                            },
                          }))
                        }
                      >
                        <option value="direct_morpho">direct_morpho</option>
                        <option value="privy_earn">privy_earn</option>
                      </select>
                    </label>
                    <label className="text-sm text-gray-700 md:col-span-2">
                      Description
                      <textarea
                        className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                        rows={2}
                        value={draft.description}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [row.id]: { ...draft, description: e.target.value },
                          }))
                        }
                      />
                    </label>
                    {draft.integrationMode === 'privy_earn' ? (
                      <label className="text-sm text-gray-700 md:col-span-2">
                        Privy vault ID
                        <input
                          className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 font-mono text-xs"
                          value={draft.privyVaultId}
                          onChange={(e) =>
                            setDrafts((prev) => ({
                              ...prev,
                              [row.id]: { ...draft, privyVaultId: e.target.value },
                            }))
                          }
                        />
                      </label>
                    ) : null}
                    <label className="text-sm text-gray-700">
                      Ordre
                      <input
                        type="number"
                        min={0}
                        className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2"
                        value={draft.sortOrder}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [row.id]: { ...draft, sortOrder: e.target.value },
                          }))
                        }
                      />
                    </label>
                    <label className="flex items-center gap-2 self-end text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={draft.isPublished}
                        onChange={(e) =>
                          setDrafts((prev) => ({
                            ...prev,
                            [row.id]: { ...draft, isPublished: e.target.checked },
                          }))
                        }
                      />
                      Publié sur le portail
                    </label>
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
