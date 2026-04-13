'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Plus, Eye, Wand2, LayoutTemplate, Boxes, ArrowRight } from 'lucide-react'
import { toastError, toastSuccess } from '@/lib/admin/toast'

interface Email {
  id: string
  name: string
  templateId: string
  locale: string
  status: 'DRAFT' | 'VALIDATED'
  updatedAt: string
  createdAt: string
  _count: {
    translations: number
  }
}

export default function EmailsPage() {
  const router = useRouter()
  const [emails, setEmails] = useState<Email[]>([])
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadEmails()
  }, [])

  const loadEmails = async () => {
    try {
      const response = await fetch('/api/admin/emails')
      if (!response.ok) {
        throw new Error('Failed to fetch emails')
      }
      const data = await response.json()
      setEmails(data)
    } catch (error) {
      console.error('Error loading emails:', error)
      toastError('Failed to load emails')
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewEmail = () => {
    router.push('/admin/ai/email')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading emails...</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Feature Cards Section */}
      <div className="mt-2 mb-8">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {/* Email Builder Card */}
          <Link
            href="/admin/ai/email"
            className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-lg hover:border-gray-300 transition-all group relative"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-2 bg-blue-50 rounded-lg">
                <Wand2 className="w-6 h-6 text-blue-600" />
              </div>
              <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Email Builder</h3>
            <p className="text-sm text-gray-600">
              Compose emails with AI, locked templates and brand pack.
            </p>
          </Link>

          {/* Email Templates Card */}
          <Link
            href="/admin/email-templates"
            className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-lg hover:border-gray-300 transition-all group relative"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-2 bg-purple-50 rounded-lg">
                <LayoutTemplate className="w-6 h-6 text-purple-600" />
              </div>
              <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Email Templates</h3>
            <p className="text-sm text-gray-600">
              Manage templates built from modules (header/footer) and lock policies.
            </p>
          </Link>

          {/* Email Modules Card */}
          <Link
            href="/admin/email-modules"
            className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-lg hover:border-gray-300 transition-all group relative"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="p-2 bg-green-50 rounded-lg">
                <Boxes className="w-6 h-6 text-green-600" />
              </div>
              <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Email Modules</h3>
            <p className="text-sm text-gray-600">
              Create reusable header/footer modules and manage translations.
            </p>
          </Link>
        </div>
      </div>

      {/* Existing Emails Section - Keep as-is */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Emails</h1>
        <button
          onClick={handleNewEmail}
          className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
        >
          <Plus className="w-5 h-5" />
          New Email
        </button>
      </div>

      {emails.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500 mb-4">No emails yet</p>
          <button
            onClick={handleNewEmail}
            className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
          >
            Create your first email
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
                  Template
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Locale
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Translations
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Updated
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {emails.map((email) => (
                <tr key={email.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm font-medium text-gray-900">{email.name}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{email.templateId}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                        email.status === 'VALIDATED'
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}
                    >
                      {email.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500 uppercase">{email.locale}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">{email._count.translations} locale(s)</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="text-sm text-gray-500">
                      {new Date(email.updatedAt).toLocaleDateString()}
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <Link
                      href={`/admin/emails/${email.id}`}
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

