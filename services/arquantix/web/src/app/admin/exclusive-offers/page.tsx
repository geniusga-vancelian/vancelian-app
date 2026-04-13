'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

interface PoolItem {
  product_id: string
  pool_id: string
  project_id: string | null
  title: string
  asset: string
  borrower_client_id: string
  raised: number
  target: number
  progress_pct: number
  investors_count: number
  utilization: number
  supply_apr: number
  status: string
  created_at: string | null
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  fundraising: 'bg-blue-100 text-blue-700',
  funded: 'bg-indigo-100 text-indigo-700',
  active: 'bg-green-100 text-green-700',
  repaid: 'bg-amber-100 text-amber-700',
  closed: 'bg-gray-200 text-gray-500',
}

export default function ExclusiveOffersPage() {
  const [pools, setPools] = useState<PoolItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchPools()
  }, [])

  const fetchPools = async () => {
    try {
      const res = await fetch('/api/admin/lending/pools')
      if (!res.ok) throw new Error('Failed to fetch pools')
      const data = await res.json()
      setPools(data.pools ?? [])
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading exclusive offers...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-700">{error}</p>
        <p className="text-xs text-red-500 mt-2">Ensure the backend API is running.</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Lending — Exclusive Offer pools (custody)</h1>
        <p className="text-sm text-gray-500 mt-1">
          Opérations prêteurs / emprunteurs sur les pools lending. Le contenu éditorial et le registre
          produit sont gérés dans <strong>Vault Builder</strong> et <strong>Packaged Products</strong>, pas ici.
        </p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-xs text-gray-500 font-medium">Total Offers</p>
          <p className="text-2xl font-bold text-gray-900">{pools.length}</p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-xs text-gray-500 font-medium">Active</p>
          <p className="text-2xl font-bold text-green-700">{pools.filter(p => p.status === 'active').length}</p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-xs text-gray-500 font-medium">Fundraising</p>
          <p className="text-2xl font-bold text-blue-700">{pools.filter(p => p.status === 'fundraising').length}</p>
        </div>
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
          <p className="text-xs text-gray-500 font-medium">Total Investors</p>
          <p className="text-2xl font-bold text-purple-700">{pools.reduce((sum, p) => sum + p.investors_count, 0)}</p>
        </div>
      </div>

      {/* Pools table */}
      {pools.length === 0 ? (
        <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
          <p className="text-gray-500">No exclusive offer pools yet.</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Title</th>
                <th className="text-left px-4 py-3 font-medium text-gray-700">Asset</th>
                <th className="text-right px-4 py-3 font-medium text-gray-700">Raised</th>
                <th className="text-right px-4 py-3 font-medium text-gray-700">Target</th>
                <th className="text-right px-4 py-3 font-medium text-gray-700">Progress</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">Investors</th>
                <th className="text-right px-4 py-3 font-medium text-gray-700">APR</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">Status</th>
                <th className="text-center px-4 py-3 font-medium text-gray-700">Detail</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {pools.map((pool) => (
                <tr key={pool.product_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <div>
                      <p className="font-medium text-gray-900">{pool.title}</p>
                      {pool.project_id && (
                        <p className="text-xs text-gray-400">Project: {pool.project_id}</p>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{pool.asset}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-900">{pool.raised.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right font-mono text-gray-600">{pool.target.toLocaleString()}</td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-emerald-500 rounded-full"
                          style={{ width: `${Math.min(pool.progress_pct, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-600">{pool.progress_pct.toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center text-gray-900">{pool.investors_count}</td>
                  <td className="px-4 py-3 text-right text-gray-900">{pool.supply_apr}%</td>
                  <td className="px-4 py-3 text-center">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${STATUS_COLORS[pool.status] ?? 'bg-gray-100 text-gray-700'}`}>
                      {pool.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Link
                      href={`/admin/exclusive-offers/${pool.pool_id}`}
                      className="text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                    >
                      View →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
