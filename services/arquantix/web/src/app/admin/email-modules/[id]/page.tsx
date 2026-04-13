'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { ArrowLeft, CheckCircle, XCircle, Languages, FileText, Eye } from 'lucide-react'
import { EmailOutput } from '@/components/ai-email/EmailOutput'
import { EmailSpec } from '@/components/ai-email/types'
import { buildMjml } from '@/lib/ai-email/buildMjml'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'
import type { Locale } from '@/config/locales'
import { supportedLocales } from '@/config/locales'
import { TranslationStatus } from '@prisma/client'
import Link from 'next/link'

interface EmailModule {
  id: string
  slug: string
  name: string
  description: string | null
  moduleType: string
  theme: string
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

export default function EmailModuleDetailPage() {
  const router = useRouter()
  const params = useParams()
  const moduleId = (params?.id as string | undefined) ?? ''

  const [module, setModule] = useState<EmailModule | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<Tab>('preview')
  const [selectedLocale, setSelectedLocale] = useState<string>('')
  const [mjml, setMjml] = useState('')
  const [html, setHtml] = useState('')
  const [showTranslateModal, setShowTranslateModal] = useState(false)
  const [isValidating, setIsValidating] = useState(false)

  useEffect(() => {
    if (moduleId) {
      loadModule()
    }
  }, [moduleId])

  useEffect(() => {
    if (module) {
      updatePreview()
    }
  }, [module, selectedLocale])

  const loadModule = async () => {
    try {
      const response = await fetch(`/api/admin/email-modules/${moduleId}`)
      if (!response.ok) {
        throw new Error('Failed to fetch module')
      }
      const data = await response.json()
      setModule(data)
      // Use default locale (fr) if module doesn't have locale in spec
      setSelectedLocale(data.spec?.locale || 'fr')
    } catch (error) {
      console.error('Error loading module:', error)
      toastError('Failed to load module')
    } finally {
      setIsLoading(false)
    }
  }

  const updatePreview = async () => {
    if (!module) return

    // Get spec for selected locale
    let specToRender: EmailSpec
    const baseLocale = module.spec?.locale || 'fr'
    
    if (selectedLocale === baseLocale || !selectedLocale) {
      specToRender = module.spec as EmailSpec
    } else {
      const translation = module.translations.find((t) => t.locale === selectedLocale)
      if (translation) {
        specToRender = translation.spec as EmailSpec
      } else {
        specToRender = module.spec as EmailSpec
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
    if (!module) return

    setIsValidating(true)
    try {
      const response = await fetch(`/api/admin/email-modules/${moduleId}/validate`, {
        method: 'POST',
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.error || 'Failed to validate')
      }

      toastSuccess('Module validated. Editing is now locked.')
      loadModule() // Reload to get updated status
    } catch (error) {
      console.error('Error validating module:', error)
      toastError(error instanceof Error ? error.message : 'Failed to validate module')
    } finally {
      setIsValidating(false)
    }
  }

  const handleTranslate = async (params: {
    sourceLocale: Locale
    targetLocales: Locale[]
    mode: 'missing' | 'force'
  }) => {
    if (!module) throw new Error('Module not loaded')

    const response = await fetch('/api/admin/translate/email-module', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        moduleId: module.id,
        sourceLocale: params.sourceLocale,
        targetLocales: params.targetLocales,
        mode: params.mode,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.error || 'Failed to translate')
    }

    const data = (await response.json()) as { translated?: string[]; skipped?: string[] }
    loadModule()
    return {
      results: {
        created: data.translated ?? [],
        updated: [],
        skipped: data.skipped ?? [],
        errors: [] as Array<{ locale: string; error: string }>,
      },
    }
  }

  const handleApproveTranslation = async (translationId: string) => {
    try {
      const response = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          entityType: 'EMAIL_MODULE',
          entityId: module?.id,
          translationId,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to approve translation')
      }

      toastSuccess('Translation approved')
      loadModule()
    } catch (error) {
      console.error('Error approving translation:', error)
      toastError('Failed to approve translation')
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading module...</div>
      </div>
    )
  }

  if (!module) {
    return (
      <div className="flex flex-col items-center justify-center h-64">
        <div className="text-gray-500 mb-4">Module not found</div>
        <Link
          href="/admin/email-modules"
          className="text-gray-900 hover:text-gray-700 flex items-center gap-2"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to modules
        </Link>
      </div>
    )
  }

  const baseLocale = module.spec?.locale || 'fr'
  const availableLocales = [baseLocale, ...module.translations.map((t) => t.locale)]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/admin/email-modules"
            className="text-gray-600 hover:text-gray-900"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{module.name}</h1>
            <p className="text-sm text-gray-500">{module.slug}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`px-3 py-1 text-sm font-medium rounded ${
              module.status === 'VALIDATED'
                ? 'bg-green-100 text-green-800'
                : 'bg-yellow-100 text-yellow-800'
            }`}
          >
            {module.status}
          </span>
          {module.status === 'DRAFT' && (
            <button
              onClick={handleValidate}
              disabled={isValidating}
              className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 disabled:opacity-50"
            >
              {isValidating ? 'Validating...' : 'Validate Module'}
            </button>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {(['preview', 'translations', 'meta'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? 'border-gray-900 text-gray-900'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'preview' && (
        <div className="space-y-4">
          {/* Locale Selector */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Languages className="w-5 h-5 text-gray-500" />
              <select
                value={selectedLocale}
                onChange={(e) => setSelectedLocale(e.target.value)}
                className="px-3 py-2 border border-gray-300 rounded-lg text-sm"
              >
                {availableLocales.map((locale) => {
                  const translation = module.translations.find((t) => t.locale === locale)
                  const isBase = locale === baseLocale
                  return (
                    <option key={locale} value={locale}>
                      {locale.toUpperCase()}
                      {isBase ? ' (Original)' : translation ? ` (${translation.translationStatus})` : ''}
                    </option>
                  )
                })}
              </select>
            </div>
          </div>

          {/* Preview */}
          <div className="h-[calc(100vh-20rem)]">
            <EmailOutput
              spec={(() => {
                if (selectedLocale === baseLocale || !selectedLocale) {
                  return module.spec as EmailSpec
                }
                const translation = module.translations.find((t) => t.locale === selectedLocale)
                return (translation?.spec || module.spec) as EmailSpec
              })()}
              mjml={mjml}
              html={html}
            />
          </div>
        </div>
      )}

      {activeTab === 'translations' && (
        <div className="space-y-4">
          {module.status !== 'VALIDATED' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-sm text-yellow-800">
                Module must be VALIDATED before translations can be created.
              </p>
            </div>
          )}

          {module.status === 'VALIDATED' && (
            <>
              <div className="flex justify-between items-center">
                <h2 className="text-lg font-semibold text-gray-900">Translations</h2>
                <button
                  onClick={() => setShowTranslateModal(true)}
                  className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800"
                >
                  Auto-translate
                </button>
              </div>

              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Locale
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Status
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Updated
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">
                        Action
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {module.translations.map((translation) => (
                      <tr key={translation.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {translation.locale.toUpperCase()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span
                            className={`px-2 py-1 text-xs font-medium rounded flex items-center gap-1 w-fit ${
                              translation.translationStatus === 'APPROVED'
                                ? 'bg-green-100 text-green-800'
                                : translation.translationStatus === 'MACHINE'
                                ? 'bg-yellow-100 text-yellow-800'
                                : 'bg-gray-100 text-gray-800'
                            }`}
                          >
                            {translation.translationStatus === 'APPROVED' ? (
                              <CheckCircle className="w-3 h-3" />
                            ) : (
                              <XCircle className="w-3 h-3" />
                            )}
                            {translation.translationStatus}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {new Date(translation.updatedAt).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          {translation.translationStatus === 'MACHINE' && (
                            <button
                              onClick={() => handleApproveTranslation(translation.id)}
                              className="text-blue-600 hover:text-blue-800"
                            >
                              Approve
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                    {module.translations.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-4 text-center text-sm text-gray-500">
                          No translations yet. Click "Auto-translate" to create translations.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {showTranslateModal && (
            <TranslateModal
              open={showTranslateModal}
              onOpenChange={setShowTranslateModal}
              sourceLocale={baseLocale as Locale}
              hasGlossary={false}
              onTranslate={handleTranslate}
            />
          )}
        </div>
      )}

      {activeTab === 'meta' && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ID</label>
            <div className="text-sm text-gray-900 font-mono">{module.id}</div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Slug</label>
            <div className="text-sm text-gray-900">{module.slug}</div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Module Type</label>
            <div className="text-sm text-gray-900">
              <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                {module.moduleType}
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Theme</label>
            <div className="text-sm text-gray-900">{module.theme}</div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <div className="text-sm">
              <span
                className={`px-2 py-1 text-xs font-medium rounded ${
                  module.status === 'VALIDATED'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-yellow-100 text-yellow-800'
                }`}
              >
                {module.status}
              </span>
            </div>
          </div>
          {module.description && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <div className="text-sm text-gray-900">{module.description}</div>
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Created</label>
            <div className="text-sm text-gray-500">
              {new Date(module.createdAt).toLocaleString()}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Updated</label>
            <div className="text-sm text-gray-500">
              {new Date(module.updatedAt).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}









