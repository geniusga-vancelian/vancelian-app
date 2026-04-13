'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Eye } from 'lucide-react'
import { toastError } from '@/lib/admin/toast'

interface EmailTemplate {
  id: string
  slug: string
  name: string
  description: string | null
  theme: string
  status: 'DRAFT' | 'VALIDATED'
  heroPolicy: 'REQUIRED' | 'OPTIONAL'
  headerModule: {
    id: string
    slug: string
    name: string
    moduleType: string
  }
  footerModule: {
    id: string
    slug: string
    name: string
    moduleType: string
  }
  updatedAt: string
  createdAt: string
}

export default function EmailTemplatesPage() {
  const router = useRouter()
  const [templates, setTemplates] = useState<EmailTemplate[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filterStatus, setFilterStatus] = useState<string>('')

  useEffect(() => {
    loadTemplates()
  }, [filterStatus])

  const loadTemplates = async () => {
    try {
      const params = new URLSearchParams()
      if (filterStatus) params.append('status', filterStatus)
      
      const response = await fetch(`/api/admin/email-templates?${params.toString()}`)
      if (!response.ok) {
        throw new Error('Failed to fetch templates')
      }
      const data = await response.json()
      setTemplates(data)
    } catch (error) {
      console.error('Error loading templates:', error)
      toastError('Failed to load templates')
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewTemplate = () => {
    router.push('/admin/email-templates/new')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading templates...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Email Templates</h1>
        <button
          onClick={handleNewTemplate}
          className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Template
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-4">
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

      {templates.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500 mb-2">No templates yet</p>
          <p className="text-sm text-gray-400 mb-4">
            Run seed to create default template: <code className="bg-gray-100 px-2 py-1 rounded text-xs">npm run seed:email</code>
          </p>
          <button
            onClick={handleNewTemplate}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
          >
            Create your first template
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
                  Header Module
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Footer Module
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
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
              {templates.map((template) => (
                <tr key={template.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{template.name}</div>
                    <div className="text-sm text-gray-500">{template.slug}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {template.headerModule.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {template.footerModule.name}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded ${
                        template.status === 'VALIDATED'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {template.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {new Date(template.updatedAt).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Link
                      href={`/admin/email-templates/${template.id}`}
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

