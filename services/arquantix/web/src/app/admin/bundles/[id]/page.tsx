'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { toast } from 'sonner'
import { ArrowLeft, Plus, Trash2 } from 'lucide-react'

interface Instrument {
  id: number
  symbol: string
  name: string | null
  asset_class: string
}

interface Allocation {
  instrument_code: string
  weight: number
}

interface BundleDetail {
  id: number
  name: string
  asset_class: string
  type: string
  description: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  created_by_email: string | null
  allocations: Array<{
    instrument_id: number
    instrument_code: string
    instrument_name: string | null
    weight: number
    position_order: number | null
  }>
}

export default function EditBundlePage() {
  const router = useRouter()
  const params = useParams()
  const bundleId = (params?.id as string | undefined) ?? ''

  const [bundle, setBundle] = useState<BundleDetail | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [isActive, setIsActive] = useState(true)
  const [instruments, setInstruments] = useState<Instrument[]>([])
  const [allocations, setAllocations] = useState<Allocation[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingBundle, setIsLoadingBundle] = useState(true)
  const [isLoadingInstruments, setIsLoadingInstruments] = useState(false)

  useEffect(() => {
    if (bundleId) {
      loadBundle()
    }
  }, [bundleId])

  useEffect(() => {
    if (bundle?.asset_class) {
      loadInstruments()
    }
  }, [bundle?.asset_class])

  const loadBundle = async () => {
    try {
      setIsLoadingBundle(true)
      const response = await fetch(`/api/bundles/${bundleId}`)
      if (!response.ok) {
        throw new Error('Failed to load bundle')
      }

      const data: BundleDetail = await response.json()
      setBundle(data)
      setName(data.name)
      setDescription(data.description || '')
      setIsActive(data.is_active)
      setAllocations(
        data.allocations.map(alloc => ({
          instrument_code: alloc.instrument_code,
          weight: parseFloat(alloc.weight.toString()),
        }))
      )
    } catch (error: any) {
      console.error('Load bundle error:', error)
      toast.error(error.message || 'Failed to load bundle')
      router.push('/admin/bundles')
    } finally {
      setIsLoadingBundle(false)
    }
  }

  const loadInstruments = async () => {
    if (!bundle?.asset_class) return

    try {
      setIsLoadingInstruments(true)
      const response = await fetch(`/api/bundles/asset-classes/${bundle.asset_class}/instruments`)
      if (!response.ok) {
        throw new Error('Failed to load instruments')
      }

      const data = await response.json()
      setInstruments(data)
    } catch (error: any) {
      console.error('Load instruments error:', error)
      toast.error(error.message || 'Failed to load instruments')
    } finally {
      setIsLoadingInstruments(false)
    }
  }

  const addAllocation = () => {
    setAllocations([...allocations, { instrument_code: '', weight: 0 }])
  }

  const removeAllocation = (index: number) => {
    setAllocations(allocations.filter((_, i) => i !== index))
  }

  const updateAllocation = (index: number, field: 'instrument_code' | 'weight', value: string | number) => {
    const updated = [...allocations]
    updated[index] = { ...updated[index], [field]: value }
    setAllocations(updated)
  }

  const calculateTotal = () => {
    return allocations.reduce((sum, alloc) => sum + (alloc.weight || 0), 0)
  }

  const normalizeWeights = () => {
    const total = calculateTotal()
    if (total === 0) {
      toast.error('Cannot normalize: total is 0')
      return
    }

    const normalized = allocations.map(alloc => ({
      ...alloc,
      weight: Math.round((alloc.weight / total) * 100 * 100) / 100
    }))

    const normalizedTotal = normalized.reduce((sum, alloc) => sum + alloc.weight, 0)
    if (normalized.length > 0) {
      normalized[normalized.length - 1].weight += (100 - normalizedTotal)
      normalized[normalized.length - 1].weight = Math.round(normalized[normalized.length - 1].weight * 100) / 100
    }

    setAllocations(normalized)
    toast.success('Weights normalized to 100%')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name) {
      toast.error('Please fill in name')
      return
    }

    if (allocations.length === 0) {
      toast.error('Please add at least one allocation')
      return
    }

    const incomplete = allocations.some(alloc => !alloc.instrument_code)
    if (incomplete) {
      toast.error('Please select an instrument for all allocations')
      return
    }

    const total = calculateTotal()
    if (Math.abs(total - 100) > 0.01) {
      toast.error(`Weights must sum to 100% (current: ${total.toFixed(2)}%)`)
      return
    }

    try {
      setIsLoading(true)
      const response = await fetch(`/api/bundles/${bundleId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name,
          description: description || null,
          is_active: isActive,
          allocations: allocations.map(alloc => ({
            instrument_code: alloc.instrument_code,
            weight: alloc.weight,
          })),
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        let errorMessage = 'Failed to update bundle'
        if (data.backend_body) {
          if (data.backend_body.detail) {
            if (Array.isArray(data.backend_body.detail)) {
              errorMessage = data.backend_body.detail.map((err: any) => {
                const field = err.loc?.join('.') || 'field'
                return `${field}: ${err.msg || err.message || 'Invalid'}`
              }).join(', ')
            } else if (typeof data.backend_body.detail === 'string') {
              errorMessage = data.backend_body.detail
            }
          }
        }
        throw new Error(errorMessage)
      }

      toast.success('Bundle updated successfully')
      router.push('/admin/bundles')
    } catch (error: any) {
      console.error('Update bundle error:', error)
      toast.error(error.message || 'Failed to update bundle')
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoadingBundle) {
    return (
      <div className="space-y-6">
        <div className="text-center text-gray-500">Loading bundle...</div>
      </div>
    )
  }

  if (!bundle) {
    return null
  }

  const total = calculateTotal()
  const isValid = Math.abs(total - 100) <= 0.01

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-4">
        <Link
          href="/admin/bundles"
          className="text-gray-600 hover:text-gray-900"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Edit Bundle</h1>
      </div>

      <form onSubmit={handleSubmit} className="bg-white rounded-lg shadow p-6 space-y-6">
        {/* Basic Info */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Bundle Name *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Asset Class
            </label>
            <input
              type="text"
              value={bundle.asset_class}
              disabled
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-100 text-gray-500"
            />
            <p className="text-xs text-gray-500 mt-1">Asset class cannot be changed</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description (optional)
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div>
          <label className="flex items-center space-x-2">
            <input
              type="checkbox"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span className="text-sm text-gray-700">Active</span>
          </label>
        </div>

        {/* Allocations */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <label className="block text-sm font-medium text-gray-700">
              Allocations *
            </label>
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-medium ${isValid ? 'text-green-600' : 'text-red-600'}`}>
                Total: {total.toFixed(2)}%
              </span>
              <button
                type="button"
                onClick={normalizeWeights}
                disabled={allocations.length === 0 || total === 0}
                className="px-3 py-1 text-sm bg-gray-100 rounded-md hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Normalize
              </button>
              <button
                type="button"
                onClick={addAllocation}
                className="flex items-center space-x-1 px-3 py-1 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
              >
                <Plus className="w-4 h-4" />
                <span>Add</span>
              </button>
            </div>
          </div>

          {isLoadingInstruments ? (
            <div className="text-sm text-gray-500">Loading instruments...</div>
          ) : allocations.length === 0 ? (
            <div className="text-sm text-gray-500">
              Click "Add" to add an allocation. Weights must sum to 100%.
            </div>
          ) : (
            <div className="space-y-2">
              {allocations.map((alloc, index) => (
                <div key={index} className="flex items-center space-x-2 p-3 border border-gray-200 rounded-md">
                  <select
                    value={alloc.instrument_code}
                    onChange={(e) => updateAllocation(index, 'instrument_code', e.target.value)}
                    required
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select instrument...</option>
                    {instruments
                      .filter(inst => !allocations.some((a, i) => i !== index && a.instrument_code === inst.symbol))
                      .map(inst => (
                        <option key={inst.id} value={inst.symbol}>
                          {inst.symbol} {inst.name ? `(${inst.name})` : ''}
                        </option>
                      ))}
                  </select>
                  <input
                    type="number"
                    value={alloc.weight || ''}
                    onChange={(e) => updateAllocation(index, 'weight', parseFloat(e.target.value) || 0)}
                    min="0"
                    max="100"
                    step="0.01"
                    required
                    className="w-24 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Weight %"
                  />
                  <span className="text-sm text-gray-500">%</span>
                  <button
                    type="button"
                    onClick={() => removeAllocation(index)}
                    className="text-red-600 hover:text-red-900"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {!isValid && allocations.length > 0 && (
            <div className="mt-2 text-sm text-red-600">
              Weights must sum to exactly 100% (current: {total.toFixed(2)}%)
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end space-x-4 pt-4 border-t">
          <Link
            href="/admin/bundles"
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isLoading || !isValid || !name || allocations.length === 0}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Updating...' : 'Update Bundle'}
          </button>
        </div>
      </form>
    </div>
  )
}

