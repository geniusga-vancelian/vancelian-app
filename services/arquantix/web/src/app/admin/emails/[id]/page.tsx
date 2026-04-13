'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { CheckCircle, XCircle, Languages, FileText } from 'lucide-react'
import { EmailOutput } from '@/components/ai-email/EmailOutput'
import { EmailSpec } from '@/components/ai-email/types'
import { buildMjml } from '@/lib/ai-email/buildMjml'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'
import type { Locale } from '@/config/locales'
import { supportedLocales } from '@/config/locales'
import { TranslationStatus } from '@prisma/client'

interface Email {
  id: string
  name: string
  templateId: string
  theme: string
  locale: string
  status: 'DRAFT' | 'VALIDATED'
  spec: EmailSpec
  translations: Array<{
    id: string
    locale: string
    spec: EmailSpec
    translationStatus: TranslationStatus
    createdAt: string
    updatedAt: string
  }>
  updatedAt: string
  createdAt: string
}

type Tab = 'preview' | 'translations' | 'meta'

export default function EmailDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter()
  const [email, setEmail] = useState<Email | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('preview')
  const [selectedLocale, setSelectedLocale] = useState<string>('')
  const [mjml, setMjml] = useState('')
  const [html, setHtml] = useState('')
  const [showTranslateModal, setShowTranslateModal] = useState(false)
  const [isValidating, setIsValidating] = useState(false)

  useEffect(() => {
    loadEmail()
  }, [params.id])

  useEffect(() => {
    if (email) {
      updatePreview()
    }
  }, [email, selectedLocale])

  const loadEmail = async () => {
    try {
      const response = await fetch(`/api/admin/emails/${params.id}`)
      if (!response.ok) {
        throw new Error('Failed to fetch email')
      }
      const data = await response.json()
      setEmail(data)
      setSelectedLocale(data.locale)
    } catch (error) {
      console.error('Error loading email:', error)
      toastError('Failed to load email')
    } finally {
      setIsLoading(false)
    }
  }

  const updatePreview = async () => {
    if (!email) return

    // Get spec for selected locale
    let specToRender: EmailSpec
    if (selectedLocale === email.locale) {
      specToRender = email.spec as EmailSpec
    } else {
      const translation = email.translations.find((t) => t.locale === selectedLocale)
      if (translation) {
        specToRender = translation.spec as EmailSpec
      } else {
        specToRender = email.spec as EmailSpec
      }
    }

    try {
      const newMjml = buildMjml(specToRender)
      // Compile MJML via API route (server-side)
      const response = await fetch('/api/ai/email/compile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ mjml: newMjml }),
      })

      if (!response.ok) {
        throw new Error('Failed to compile MJML')
      }

      const { html: newHtml } = await response.json()
      setMjml(newMjml)
      setHtml(newHtml)
    } catch (error) {
      console.error('Failed to build preview:', error)
    }
  }

  const handleValidate = async () => {
    if (!email) return

    setIsValidating(true)
    try {
      const response = await fetch(`/api/admin/emails/${params.id}/validate`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to validate')
      }

      toastSuccess('Email validated. Structure is now locked.')
      loadEmail() // Reload to get updated status
    } catch (error) {
      console.error('Error validating email:', error)
      toastError(error instanceof Error ? error.message : 'Failed to validate email')
    } finally {
      setIsValidating(false)
    }
  }

  const handleTranslate = async (params: {
    sourceLocale: Locale
    targetLocales: Locale[]
    mode: 'missing' | 'force'
  }) => {
    if (!email) return

    const response = await fetch('/api/admin/translate/email', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        emailId: email.id,
        sourceLocale: params.sourceLocale,
        targetLocales: params.targetLocales,
        mode: params.mode,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Translation failed')
    }

    return await response.json()
  }

  const handleApproveTranslation = async (locale: string) => {
    if (!email) return

    try {
      const response = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          entityType: 'EMAIL',
          entityId: email.id,
          locale,
        }),
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Approval failed')
      }

      toastSuccess('Translation approved')
      loadEmail() // Reload to get updated status
    } catch (error) {
      console.error('Error approving translation:', error)
      toastError(error instanceof Error ? error.message : 'Approval failed')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading email...</div>
      </div>
    )
  }

  if (!email) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Email not found</p>
      </div>
    )
  }

  // Get spec for selected locale
  let specToRender: EmailSpec = email.spec as EmailSpec
  let translationStatus: TranslationStatus | null = null
  if (selectedLocale !== email.locale) {
    const translation = email.translations.find((t) => t.locale === selectedLocale)
    if (translation) {
      specToRender = translation.spec as EmailSpec
      translationStatus = translation.translationStatus
    }
  }

  // Available locales for preview
  const availableLocales: Array<{
    locale: string
    label: string
    isTranslation: boolean
    status?: TranslationStatus
  }> = [
    { locale: email.locale, label: email.locale.toUpperCase(), isTranslation: false },
    ...email.translations.map((t) => ({
      locale: t.locale,
      label: t.locale.toUpperCase(),
      isTranslation: true,
      status: t.translationStatus,
    })),
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">{email.name}</h1>
          <div className="flex items-center gap-4 mt-2">
            <span
              className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                email.status === 'VALIDATED'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {email.status}
            </span>
            <span className="text-sm text-gray-500">Template: {email.templateId}</span>
            <span className="text-sm text-gray-500">Theme: {email.theme}</span>
          </div>
        </div>
        {email.status === 'DRAFT' && (
          <button
            onClick={handleValidate}
            disabled={isValidating}
            className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isValidating ? 'Validating...' : 'Validate Email'}
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          <button
            onClick={() => setActiveTab('preview')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'preview'
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Preview
          </button>
          <button
            onClick={() => setActiveTab('translations')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'translations'
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Translations
          </button>
          <button
            onClick={() => setActiveTab('meta')}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === 'meta'
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Meta
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'preview' && (
        <div className="space-y-4">
          {/* Locale Selector */}
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Preview Locale:</label>
            <select
              value={selectedLocale}
              onChange={(e) => setSelectedLocale(e.target.value)}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
            >
              {availableLocales.map((loc) => (
                <option key={loc.locale} value={loc.locale}>
                  {loc.label}
                  {loc.isTranslation && loc.status != null ? ` (${loc.status})` : ''}
                </option>
              ))}
            </select>
            {translationStatus && (
              <div className="flex items-center gap-2">
                {translationStatus === 'APPROVED' ? (
                  <CheckCircle className="w-5 h-5 text-green-600" />
                ) : (
                  <XCircle className="w-5 h-5 text-yellow-600" />
                )}
                <span className="text-sm text-gray-600">
                  {translationStatus === 'APPROVED' ? 'Approved' : 'Machine Translation'}
                </span>
                {translationStatus === 'MACHINE' && (
                  <button
                    onClick={() => handleApproveTranslation(selectedLocale)}
                    className="px-3 py-1 text-sm bg-gray-900 text-white rounded hover:bg-gray-800"
                  >
                    Approve
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Email Preview */}
          <div className="h-[calc(100vh-20rem)]">
            <EmailOutput spec={specToRender} mjml={mjml} html={html} />
          </div>
        </div>
      )}

      {activeTab === 'translations' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold">Translations</h2>
            {email.status === 'VALIDATED' && (
              <button
                onClick={() => setShowTranslateModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
              >
                <Languages className="w-4 h-4" />
                Auto-translate
              </button>
            )}
          </div>

          {email.status !== 'VALIDATED' && (
            <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-sm text-yellow-800">
                Email must be validated before translation. Please validate the email first.
              </p>
            </div>
          )}

          <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Locale</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Updated</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {email.translations.map((translation) => (
                  <tr key={translation.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 uppercase">{translation.locale}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                          translation.translationStatus === 'APPROVED'
                            ? 'bg-green-100 text-green-800'
                            : 'bg-yellow-100 text-yellow-800'
                        }`}
                      >
                        {translation.translationStatus}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-500">
                        {new Date(translation.updatedAt).toLocaleDateString()}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {translation.translationStatus === 'MACHINE' && (
                        <button
                          onClick={() => handleApproveTranslation(translation.locale)}
                          className="text-sm text-gray-900 hover:text-gray-700"
                        >
                          Approve
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
                {email.translations.length === 0 && (
                  <tr>
                    <td colSpan={4} className="px-6 py-8 text-center text-gray-500">
                      No translations yet. Use "Auto-translate" to create translations.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeTab === 'meta' && (
        <div className="space-y-4">
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h3 className="text-lg font-semibold mb-4">Email Metadata</h3>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">ID</dt>
                <dd className="mt-1 text-sm text-gray-900">{email.id}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Name</dt>
                <dd className="mt-1 text-sm text-gray-900">{email.name}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Template</dt>
                <dd className="mt-1 text-sm text-gray-900">{email.templateId}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Theme</dt>
                <dd className="mt-1 text-sm text-gray-900">{email.theme}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Source Locale</dt>
                <dd className="mt-1 text-sm text-gray-900 uppercase">{email.locale}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1">
                  <span
                    className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      email.status === 'VALIDATED'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}
                  >
                    {email.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Created</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(email.createdAt).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Updated</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {new Date(email.updatedAt).toLocaleString()}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Blocks Count</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {(email.spec as EmailSpec).blocks.length} block(s)
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Translations</dt>
                <dd className="mt-1 text-sm text-gray-900">{email.translations.length} locale(s)</dd>
              </div>
            </dl>
          </div>
        </div>
      )}

      {/* Translate Modal */}
      {showTranslateModal && email.status === 'VALIDATED' && (
        <TranslateModal
          open={showTranslateModal}
          onOpenChange={setShowTranslateModal}
          sourceLocale={email.locale as Locale}
          onTranslate={handleTranslate}
          hasGlossary={true}
        />
      )}
    </div>
  )
}

