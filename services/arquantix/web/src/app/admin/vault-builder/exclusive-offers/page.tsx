'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ArrowLeft, ExternalLink, Loader2, Plus, Search } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { toastError, toastSuccess } from '@/lib/admin/toast'

type EngineLinked = 'all' | 'linked' | 'unlinked'

interface ListItem {
  packagedProductId: string
  slug: string
  commercialStatus: string
  visibility: string
  featuredRank: number | null
  engineLinked: boolean
  lendingSnapshot: {
    poolProductId: string
    status: string
    supplyAprBps: string | null
    currentRaised: string | null
    targetSize: string | null
  } | null
  publicationState: string
  page: {
    id: string
    slug: string
    title: string | null
    urlPath: string
    template: string
    updatedAt: string
  } | null
  packagedUpdatedAt: string
  integrityIssue: boolean
  integrityMessage: string | null
}

const COMMERCIAL = ['DRAFT', 'PUBLISHED', 'ARCHIVED'] as const
const VIS = ['PUBLIC', 'PRIVATE', 'HIDDEN'] as const

export default function AdminVaultBuilderExclusiveOffersPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(true)
  const [items, setItems] = useState<ListItem[]>([])
  const [creating, setCreating] = useState(false)

  const [q, setQ] = useState('')
  const [debouncedQ, setDebouncedQ] = useState('')
  const [commercialStatus, setCommercialStatus] = useState<string>('')
  const [visibility, setVisibility] = useState<string>('')
  const [engineLinked, setEngineLinked] = useState<EngineLinked>('all')
  const [sort, setSort] = useState<'updated_desc' | 'featured_asc'>('updated_desc')

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(q.trim()), 300)
    return () => clearTimeout(t)
  }, [q])

  const queryString = useMemo(() => {
    const p = new URLSearchParams()
    if (debouncedQ) p.set('q', debouncedQ)
    if (commercialStatus) p.set('commercialStatus', commercialStatus)
    if (visibility) p.set('visibility', visibility)
    if (engineLinked !== 'all') p.set('engineLinked', engineLinked)
    if (sort !== 'updated_desc') p.set('sort', sort)
    return p.toString()
  }, [debouncedQ, commercialStatus, visibility, engineLinked, sort])

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(
        `/api/admin/packaged-products/exclusive-offers${queryString ? `?${queryString}` : ''}`,
        { credentials: 'include' }
      )
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body?.error || body?.detail || `Erreur ${res.status}`)
      }
      const data = await res.json()
      setItems(data.items ?? [])
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Chargement impossible')
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [queryString, router])

  useEffect(() => {
    void load()
  }, [load])

  const handleCreate = async () => {
    setCreating(true)
    try {
      const res = await fetch('/api/admin/packaged-products/exclusive-offers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          title: 'Nouvelle Exclusive Offer',
        }),
      })
      const body = await res.json().catch(() => ({}))
      if (res.status === 401) {
        router.push('/admin/login')
        return
      }
      if (!res.ok) {
        throw new Error(body?.error || body?.detail || 'Création impossible')
      }
      toastSuccess('Exclusive Offer créée.')
      const url = body.editUrl as string | undefined
      if (url) {
        router.push(url)
      } else if (body.slug) {
        router.push(`/admin/vault-builder?slug=${encodeURIComponent(body.slug)}&eo=1`)
      } else {
        await load()
      }
    } catch (e) {
      toastError(e instanceof Error ? e.message : 'Création impossible')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/admin/vault-builder"
            className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-800 mb-2"
          >
            <ArrowLeft className="w-4 h-4" />
            Vault Builder (tous les vaults)
          </Link>
          <h1 className="text-2xl font-bold text-gray-900">Exclusive Offers</h1>
          <p className="text-sm text-gray-600 mt-1">
            Liste issue du registre <code className="text-xs bg-gray-100 px-1 rounded">packaged_products</code>{' '}
            · type <strong>EXCLUSIVE_OFFER</strong> · pages Vault Builder.
          </p>
        </div>
        <Button type="button" onClick={handleCreate} disabled={creating} className="shrink-0">
          {creating ? (
            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
          ) : (
            <Plus className="w-4 h-4 mr-2" />
          )}
          Create Exclusive Offer
        </Button>
      </div>

      <div className="bg-white rounded-lg shadow border border-gray-100 p-4 mb-6 space-y-4">
        <div className="flex flex-wrap gap-3 items-end">
          <div className="flex-1 min-w-[200px]">
            <label className="block text-xs font-medium text-gray-500 mb-1">Recherche (titre / slug)</label>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="ex. niseko, eo-…"
                className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-md text-sm"
              />
            </div>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Commercial</label>
            <select
              value={commercialStatus}
              onChange={(e) => setCommercialStatus(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm min-w-[140px]"
            >
              <option value="">Tous</option>
              {COMMERCIAL.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Visibilité</label>
            <select
              value={visibility}
              onChange={(e) => setVisibility(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm min-w-[120px]"
            >
              <option value="">Toutes</option>
              {VIS.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Moteur lending</label>
            <select
              value={engineLinked}
              onChange={(e) => setEngineLinked(e.target.value as EngineLinked)}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm min-w-[140px]"
            >
              <option value="all">Tous</option>
              <option value="linked">Lié</option>
              <option value="unlinked">Non lié</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">Tri</label>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as 'updated_desc' | 'featured_asc')}
              className="px-3 py-2 border border-gray-300 rounded-md text-sm min-w-[180px]"
            >
              <option value="updated_desc">Mis à jour (récent)</option>
              <option value="featured_asc">Mis en avant (rang)</option>
            </select>
          </div>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16 text-gray-500">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-12 text-center text-gray-500">
          Aucune Exclusive Offer. Utilisez « Create Exclusive Offer » pour en créer une.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Titre</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Slug</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commercial</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Visibilité</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rang</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Moteur</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">MAJ</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {items.map((row) => {
                const title = row.page?.title || row.slug
                const editHref = `/admin/vault-builder?slug=${encodeURIComponent(row.slug)}&eo=1`
                return (
                  <tr key={row.packagedProductId} className={row.integrityIssue ? 'bg-amber-50' : undefined}>
                    <td className="px-4 py-3 text-sm">
                      <div className="font-medium text-gray-900">{title}</div>
                      {row.integrityIssue && (
                        <div className="text-xs text-amber-800 mt-0.5">
                          Problème d’intégrité : {row.integrityMessage ?? '—'}
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-gray-600">{row.slug}</td>
                    <td className="px-4 py-3 text-sm">{row.commercialStatus}</td>
                    <td className="px-4 py-3 text-sm">{row.visibility}</td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      {row.featuredRank ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      {row.engineLinked ? (
                        <span className="text-green-700">Lié</span>
                      ) : (
                        <span className="text-gray-500">Non lié</span>
                      )}
                      {row.lendingSnapshot?.supplyAprBps != null && (
                        <div className="text-xs text-gray-500 mt-0.5">
                          APR {row.lendingSnapshot.supplyAprBps} bps
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                      {new Date(row.packagedUpdatedAt).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        href={editHref}
                        className="inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-800"
                      >
                        Éditer
                        <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
