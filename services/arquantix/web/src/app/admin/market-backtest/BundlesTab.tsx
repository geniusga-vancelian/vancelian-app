'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { toast } from 'sonner'
import { Plus, Edit, Trash2 } from 'lucide-react'

interface BundleListItem {
  id: number
  name: string
  asset_class: string
  type: string
  is_active: boolean
  updated_at: string
  allocations_count: number
}

export default function BundlesTab() {
  const [bundles, setBundles] = useState<BundleListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filterAssetClass, setFilterAssetClass] = useState<string>('')

  useEffect(() => {
    loadBundles()
  }, [filterAssetClass])

  const loadBundles = async () => {
    try {
      setIsLoading(true)
      const params = new URLSearchParams()
      if (filterAssetClass) params.append('asset_class', filterAssetClass)
      params.append('active', 'true')

      const response = await fetch(`/api/bundles?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to load bundles')
      }

      const data = await response.json()
      setBundles(data)
    } catch (error: any) {
      console.error('Load bundles error:', error)
      toast.error(error.message || 'Failed to load bundles')
    } finally {
      setIsLoading(false)
    }
  }

  const handleDelete = async (bundleId: number, bundleName: string) => {
    if (!confirm(`Are you sure you want to deactivate bundle "${bundleName}"?`)) {
      return
    }

    try {
      const response = await fetch(`/api/bundles/${bundleId}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: 'Delete failed' }))
        throw new Error(errorData.error || 'Failed to delete bundle')
      }

      toast.success('Bundle deactivated')
      loadBundles()
    } catch (error: any) {
      console.error('Delete bundle error:', error)
      toast.error(error.message || 'Failed to delete bundle')
    }
  }

  const assetClassLabels: Record<string, string> = {
    crypto: 'Crypto',
    etf: 'ETF',
    equity: 'Equity',
    commodities: 'Commodities',
    index: 'Index',
    forex: 'Forex',
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <p className="text-gray-600">
          Gérer les bundles d'allocations (fixed, composite, dynamic)
        </p>
        <Link
          href="/admin/bundles/new"
          className="flex items-center space-x-2 px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
        >
          <Plus className="w-4 h-4" />
          <span>Create Bundle</span>
        </Link>
      </div>

      {/* Filter */}
      <div className="bg-white rounded-lg shadow p-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Filter by Asset Class
        </label>
        <select
          value={filterAssetClass}
          onChange={(e) => setFilterAssetClass(e.target.value)}
          className="w-full md:w-64 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
        >
          <option value="">All Asset Classes</option>
          <option value="crypto">Crypto</option>
          <option value="etf">ETF</option>
          <option value="equity">Equity</option>
          <option value="commodities">Commodities</option>
          <option value="index">Index</option>
          <option value="forex">Forex</option>
        </select>
      </div>

      {/* Bundles List */}
      <div className="bg-white rounded-lg shadow">
        {isLoading ? (
          <div className="p-6 text-center text-gray-500">Loading bundles...</div>
        ) : bundles.length === 0 ? (
          <div className="p-6 text-center text-gray-500">
            No bundles found. <Link href="/admin/bundles/new" className="text-indigo-600 hover:underline">Create one</Link>
          </div>
        ) : (
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Asset Class</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Instruments</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Updated</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {bundles.map((bundle) => (
                <tr key={bundle.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{bundle.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-800">
                      {assetClassLabels[bundle.asset_class] || bundle.asset_class}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{bundle.type}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{bundle.allocations_count}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(bundle.updated_at).toLocaleDateString('fr-FR')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <Link
                        href={`/admin/bundles/${bundle.id}`}
                        className="text-indigo-600 hover:text-indigo-900"
                      >
                        <Edit className="w-4 h-4" />
                      </Link>
                      <button
                        onClick={() => handleDelete(bundle.id, bundle.name)}
                        className="text-red-600 hover:text-red-900"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

