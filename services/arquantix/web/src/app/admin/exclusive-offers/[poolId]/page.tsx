'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'

interface PoolDetail {
  overview: {
    pool_id: string
    asset: string
    total_committed: number
    total_borrowed: number
    available_liquidity: number
    utilization_rate: number
    supply_rate_bps: number
    borrow_rate_bps: number
  }
  product: {
    product_id: string
    project_id: string | null
    title: string
    borrower_client_id: string
    asset: string
    target_size: number
    current_raised: number
    progress_pct: number
    investors_count: number
    supply_apr: number
    borrow_apr: number
    status: string
    start_date: string | null
    maturity_date: string | null
  } | null
  lenders: Array<{
    client_id: string
    commitment_id: string
    committed: number
    allocated: number
    available: number
    accrued_interest: number
    status: string
    created_at: string | null
  }>
  borrowers: Array<{
    client_id: string
    borrow_position_id: string
    borrowed: number
    accrued_interest_due: number
    total_due: number
    status: string
    created_at: string | null
  }>
  allocations: Array<{
    allocation_id: string
    supply_commitment_id: string
    borrow_position_id: string
    amount: number
    created_at: string | null
  }>
  summary: {
    total_lenders: number
    total_borrowed_positions: number
    total_allocations: number
  }
}

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  fundraising: 'bg-blue-100 text-blue-700',
  funded: 'bg-indigo-100 text-indigo-700',
  active: 'bg-green-100 text-green-700',
  repaid: 'bg-amber-100 text-amber-700',
  closed: 'bg-gray-200 text-gray-500',
}

export default function ExclusiveOfferDetailPage() {
  const params = useParams()
  const poolId = (params?.poolId as string | undefined) ?? ''

  const [detail, setDetail] = useState<PoolDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!poolId) return
    fetchDetail()
  }, [poolId])

  const fetchDetail = async () => {
    try {
      const res = await fetch(`/api/admin/lending/pools/${poolId}`)
      if (!res.ok) throw new Error('Failed to fetch pool detail')
      const data = await res.json()
      setDetail(data)
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading pool detail...</div>
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="p-6 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-700">{error || 'Pool not found'}</p>
      </div>
    )
  }

  const { overview, product, lenders, borrowers, allocations, summary } = detail

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{product?.title || 'Pool Detail'}</h1>
          <p className="text-sm text-gray-500 mt-1">
            Pool: <span className="font-mono">{poolId}</span>
          </p>
        </div>
        <Link
          href="/admin/exclusive-offers"
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to lending pools
        </Link>
      </div>

      {/* Product info */}
      {product && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Product Overview</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <div>
              <p className="text-xs text-gray-500">Status</p>
              <span className={`inline-block mt-1 px-2 py-1 text-xs font-semibold rounded-full ${STATUS_COLORS[product.status] ?? ''}`}>
                {product.status}
              </span>
            </div>
            <div>
              <p className="text-xs text-gray-500">Asset</p>
              <p className="font-bold text-gray-900">{product.asset}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Supply APR</p>
              <p className="font-bold text-blue-700">{product.supply_apr}%</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Progress</p>
              <p className="font-bold text-green-700">{product.progress_pct.toFixed(1)}%</p>
              <p className="text-xs text-gray-500">{product.current_raised.toLocaleString()} / {product.target_size.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Borrower</p>
              <p className="font-mono text-xs text-gray-700 break-all">{product.borrower_client_id}</p>
            </div>
          </div>
        </div>
      )}

      {/* Pool overview */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Pool Liquidity</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
            <p className="text-xs text-blue-600 font-medium">Total Committed</p>
            <p className="text-xl font-bold text-blue-900">{overview.total_committed.toLocaleString()}</p>
          </div>
          <div className="bg-amber-50 rounded-lg p-4 border border-amber-200">
            <p className="text-xs text-amber-600 font-medium">Total Borrowed</p>
            <p className="text-xl font-bold text-amber-900">{overview.total_borrowed.toLocaleString()}</p>
          </div>
          <div className="bg-green-50 rounded-lg p-4 border border-green-200">
            <p className="text-xs text-green-600 font-medium">Available Liquidity</p>
            <p className="text-xl font-bold text-green-900">{overview.available_liquidity.toLocaleString()}</p>
          </div>
          <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
            <p className="text-xs text-purple-600 font-medium">Utilization</p>
            <p className="text-xl font-bold text-purple-900">{(overview.utilization_rate * 100).toFixed(1)}%</p>
          </div>
        </div>
      </div>

      {/* Lenders */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Lenders <span className="text-sm font-normal text-gray-500">({summary.total_lenders})</span>
        </h2>
        {lenders.length === 0 ? (
          <p className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-md p-4 bg-gray-50">
            No lenders yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-700">Client ID</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-700">Committed</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-700">Allocated</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-700">Available</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-700">Accrued Interest</th>
                  <th className="text-center px-4 py-2 font-medium text-gray-700">Status</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-700">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {lenders.map((l) => (
                  <tr key={l.commitment_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs text-gray-700">{l.client_id.substring(0, 8)}...</td>
                    <td className="px-4 py-2 text-right font-mono">{l.committed.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right font-mono">{l.allocated.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right font-mono">{l.available.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right font-mono text-green-700">+{l.accrued_interest.toFixed(4)}</td>
                    <td className="px-4 py-2 text-center">
                      <span className="px-2 py-0.5 text-xs bg-gray-100 rounded">{l.status}</span>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500">{l.created_at?.substring(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Borrower */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Borrower <span className="text-sm font-normal text-gray-500">({summary.total_borrowed_positions})</span>
        </h2>
        {borrowers.length === 0 ? (
          <p className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-md p-4 bg-gray-50">
            No active borrower position.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-700">Client ID</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-700">Borrowed</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-700">Interest Due</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-700">Total Due</th>
                  <th className="text-center px-4 py-2 font-medium text-gray-700">Status</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-700">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {borrowers.map((b) => (
                  <tr key={b.borrow_position_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs text-gray-700">{b.client_id.substring(0, 8)}...</td>
                    <td className="px-4 py-2 text-right font-mono">{b.borrowed.toLocaleString()}</td>
                    <td className="px-4 py-2 text-right font-mono text-red-600">{b.accrued_interest_due.toFixed(4)}</td>
                    <td className="px-4 py-2 text-right font-mono font-bold">{b.total_due.toLocaleString()}</td>
                    <td className="px-4 py-2 text-center">
                      <span className="px-2 py-0.5 text-xs bg-gray-100 rounded">{b.status}</span>
                    </td>
                    <td className="px-4 py-2 text-xs text-gray-500">{b.created_at?.substring(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Allocations audit */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Allocation Audit Trail <span className="text-sm font-normal text-gray-500">({summary.total_allocations})</span>
        </h2>
        {allocations.length === 0 ? (
          <p className="text-sm text-gray-500 border border-dashed border-gray-300 rounded-md p-4 bg-gray-50">
            No allocations yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-2 font-medium text-gray-700">Allocation ID</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-700">Supply → Borrow</th>
                  <th className="text-right px-4 py-2 font-medium text-gray-700">Amount</th>
                  <th className="text-left px-4 py-2 font-medium text-gray-700">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {allocations.map((a) => (
                  <tr key={a.allocation_id} className="hover:bg-gray-50">
                    <td className="px-4 py-2 font-mono text-xs text-gray-500">{a.allocation_id.substring(0, 8)}...</td>
                    <td className="px-4 py-2 text-xs text-gray-600">
                      <span className="font-mono">{a.supply_commitment_id.substring(0, 8)}</span>
                      <span className="mx-1">→</span>
                      <span className="font-mono">{a.borrow_position_id.substring(0, 8)}</span>
                    </td>
                    <td className="px-4 py-2 text-right font-mono">{a.amount.toLocaleString()}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">{a.created_at?.substring(0, 10)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
