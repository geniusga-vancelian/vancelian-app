'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Eye } from 'lucide-react'
import { toastError } from '@/lib/admin/toast'

interface EmailModule {
  id: string
  slug: string
  name: string
  description: string | null
  moduleType: 'HEADER' | 'FOOTER' | 'LEGAL' | 'SIGNATURE' | 'SOCIAL' | 'DISCLAIMER' | 'CUSTOM'
  theme: string
  status: 'DRAFT' | 'VALIDATED'
  updatedAt: string
  createdAt: string
  _count: {
    translations: number
  }
}

export default function EmailModulesPage() {
  const router = useRouter()
  const [modules, setModules] = useState<EmailModule[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filterType, setFilterType] = useState<string>('')
  const [filterStatus, setFilterStatus] = useState<string>('')

  useEffect(() => {
    loadModules()
  }, [filterType, filterStatus])

  const loadModules = async () => {
    try {
      const params = new URLSearchParams()
      if (filterType) params.append('moduleType', filterType)
      if (filterStatus) params.append('status', filterStatus)
      
      const response = await fetch(`/api/admin/email-modules?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to fetch modules')
      }
      const data = await response.json()
      setModules(data)
    } catch (error) {
      console.error('Error loading modules:', error)
      toastError('Failed to load modules')
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewModule = () => {
    router.push('/admin/email-modules/new')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading modules...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Email Modules</h1>
        <button
          onClick={handleNewModule}
          className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Module
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Types</option>
          <option value="HEADER">HEADER</option>
          <option value="FOOTER">FOOTER</option>
          <option value="LEGAL">LEGAL</option>
          <option value="SIGNATURE">SIGNATURE</option>
          <option value="SOCIAL">SOCIAL</option>
          <option value="DISCLAIMER">DISCLAIMER</option>
          <option value="CUSTOM">CUSTOM</option>
        </select>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
        >
          <option value="">All Status</option>
          <option value="DRAFT">DRAFT</option>
          <option value="VALIDATED">VALIDATED</option>
        </select>
      </div>

      {modules.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500 mb-2">No modules yet</p>
          <p className="text-sm text-gray-400 mb-4">
            Run seed to create default modules: <code className="bg-gray-100 px-2 py-1 rounded text-xs">npm run seed:email</code>
          </p>
          <button
            onClick={handleNewModule}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
          >
            Create your first module
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Name
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Translations
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Updated
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {modules.map((module) => (
                <tr key={module.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{module.name}</div>
                    <div className="text-sm text-gray-500">{module.slug}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded">
                      {module.moduleType}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        module.status === 'VALIDATED'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {module.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {module._count.translations}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(module.updatedAt).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Link
                      href={`/admin/email-modules/${module.id}`}
                      className="text-gray-900 hover:text-gray-700 flex items-center gap-1"
                    >
                      <Eye className="w-4 h-4" />
                      Open
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

