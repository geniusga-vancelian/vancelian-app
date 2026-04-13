'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { supportedLocales, type Locale } from '@/config/locales'
import { SectionEditor } from '@/components/admin/SectionEditor'
import { toastSuccess, toastError } from '@/lib/admin/toast'
import { TranslateModal } from '@/components/admin/TranslateModal'
import { getSectionType } from '@/lib/sections/library'

interface Section {
  id: string
  key: string
  order: number
  schemaVersion: string
  page: {
    slug: string
  }
}

interface Content {
  id: string
  locale: string
  status: string
  data: any
  translationStatus?: 'ORIGINAL' | 'MACHINE' | 'APPROVED'
}

export default function AdminSectionEditorPage() {
  const router = useRouter()
  const params = useParams()
  const sectionId = (params?.id as string | undefined) ?? ''

  const [section, setSection] = useState<Section | null>(null)
  const [content, setContent] = useState<Content | null>(null)
  const [selectedLocale, setSelectedLocale] = useState<Locale>('fr')
  const [selectedStatus, setSelectedStatus] = useState<'draft' | 'published'>('draft')
  const [data, setData] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [showTranslateModal, setShowTranslateModal] = useState(false)
  const [hasGlossary, setHasGlossary] = useState(false)
  const [approving, setApproving] = useState(false)

  useEffect(() => {
    if (!sectionId) return
    loadSection()
  }, [sectionId, selectedLocale, selectedStatus])

  const loadSection = async () => {
    try {
      const res = await fetch(
        `/api/admin/sections/${sectionId}?locale=${selectedLocale}&status=${selectedStatus}`
      )
      const result = await res.json()

      if (result.section) {
        setSection(result.section)
        if (result.content) {
          setContent(result.content)
          setData(result.content.data)
        } else {
          setContent(null)
          // Initialize with default data for this section type
          const sectionType = getSectionType(result.section.key)
          const defaultData = sectionType?.defaultData || {}
          setData(defaultData)
        }
      } else if (result.error === 'Unauthorized') {
        router.push('/admin/login')
      } else if (result.error === 'Section not found') {
        router.push('/admin/pages')
      }
    } catch (error) {
      console.error('Error loading section:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSaveDraft = async () => {
    setSaving(true)
    try {
      const res = await fetch(`/api/admin/sections/${sectionId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locale: selectedLocale,
          data,
        }),
      })

      if (res.ok) {
        toastSuccess('Saved')
        loadSection()
      } else {
        const error = await res.json()
        toastError(error.error || 'Failed to save draft')
      }
    } catch (error) {
      console.error('Error saving draft:', error)
      toastError('Error saving draft')
    } finally {
      setSaving(false)
    }
  }

  const handlePublish = async () => {
    if (!confirm('Publish this draft? This will overwrite the published version.')) {
      return
    }

    setSaving(true)
    try {
      const res = await fetch(`/api/admin/sections/${sectionId}/publish`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locale: selectedLocale,
        }),
      })

      if (res.ok) {
        const data = await res.json()
        if (data.warning) {
          // Show warning but still consider it a success
          toastError(data.warning)
        } else {
          toastSuccess('Published')
        }
        setSelectedStatus('published')
        loadSection()
      } else {
        const error = await res.json()
        toastError(error.error || 'Failed to publish')
      }
    } catch (error) {
      console.error('Error publishing:', error)
      toastError('Error publishing')
    } finally {
      setSaving(false)
    }
  }

  const handleResetDraft = async () => {
    if (!confirm('Reset draft from published? This will overwrite your current draft.')) {
      return
    }

    setSaving(true)
    try {
      const res = await fetch(`/api/admin/sections/${sectionId}/reset-draft`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          locale: selectedLocale,
        }),
      })

      if (res.ok) {
        toastSuccess('Draft reset')
        setSelectedStatus('draft')
        loadSection()
      } else {
        const error = await res.json()
        toastError(error.error || 'Failed to reset draft')
      }
    } catch (error) {
      console.error('Error resetting draft:', error)
      toastError('Error resetting draft')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">Loading...</div>
      </div>
    )
  }

  if (!section) {
    return null
  }

  const previewUrl = `/preview/${section.page.slug}?locale=${selectedLocale}`

  const handleApproveTranslation = async () => {
    if (!content || !section) return
    setApproving(true)
    try {
      const res = await fetch('/api/admin/translate/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          entityType: 'SECTION',
          entityId: section.id,
          locale: selectedLocale,
        }),
      })
      if (!res.ok) {
        const error = await res.json()
        throw new Error(error.error || 'Failed to approve translation')
      }
      toastSuccess('Translation approved')
      await loadSection() // Reload to update status
    } catch (error: any) {
      toastError(error.message || 'Failed to approve translation')
    } finally {
      setApproving(false)
    }
  }

  // Check if we have a structured editor for this section type
  const hasStructuredEditor = section.key === 'hero' || section.key === 'projects' || section.key === 'project_grid' || section.key === 'faq'

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Section: {section.key}
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Page: {section.page.slug} • Schema: {section.schemaVersion}
          </p>
        </div>
        <Link
          href={`/admin/pages/${section.page.slug}`}
          className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900"
        >
          ← Back to Page
        </Link>
      </div>

      <div className="bg-white rounded-lg shadow p-6 mb-6">
        <div className="flex gap-4 items-center mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Locale
            </label>
            <select
              value={selectedLocale}
              onChange={(e) => {
                setSelectedLocale(e.target.value as Locale)
                setSelectedStatus('draft')
              }}
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            >
              {supportedLocales.map((locale) => (
                <option key={locale} value={locale}>
                  {locale.toUpperCase()}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              View
            </label>
            <select
              value={selectedStatus}
              onChange={(e) =>
                setSelectedStatus(e.target.value as 'draft' | 'published')
              }
              className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500"
            >
              <option value="draft">Draft</option>
              <option value="published">Published</option>
            </select>
          </div>

          {content && content.translationStatus && (
            <div className="flex items-end">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-gray-700">Status:</span>
                <span
                  className={`px-2 py-1 text-xs font-semibold rounded ${
                    content.translationStatus === 'ORIGINAL'
                      ? 'bg-gray-100 text-gray-700'
                      : content.translationStatus === 'MACHINE'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-green-100 text-green-800'
                  }`}
                >
                  {content.translationStatus === 'ORIGINAL'
                    ? 'ORIGINAL'
                    : content.translationStatus === 'MACHINE'
                    ? 'MACHINE'
                    : 'APPROVED'}
                </span>
                {content.translationStatus === 'MACHINE' && (
                  <button
                    onClick={handleApproveTranslation}
                    disabled={approving}
                    className="px-3 py-1 text-xs bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                  >
                    {approving ? 'Approving...' : 'Approve'}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSaveDraft}
            disabled={saving}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50"
          >
            {saving ? 'Saving...' : 'Save Draft'}
          </button>
          <button
            onClick={handlePublish}
            disabled={saving || selectedStatus === 'published'}
            className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            Publish
          </button>
          <button
            onClick={handleResetDraft}
            disabled={saving || !content || selectedStatus === 'draft'}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
          >
            Reset Draft
          </button>
          <a
            href={previewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
          >
            Preview
          </a>
          {content && (
            <button
              onClick={() => setShowTranslateModal(true)}
              disabled={saving}
              className="px-4 py-2 bg-purple-600 text-white rounded-md hover:bg-purple-700 disabled:opacity-50"
            >
              Auto-translate
            </button>
          )}
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Content Data</h2>

        {hasStructuredEditor ? (
          <div className="space-y-4">
            <SectionEditor
              sectionKey={section.key}
              data={data}
              onChange={setData}
            />
            <details className="mt-4">
              <summary className="cursor-pointer text-sm text-gray-600 hover:text-gray-900">
                View/Edit Raw JSON
              </summary>
              <textarea
                value={JSON.stringify(data, null, 2)}
                onChange={(e) => {
                  try {
                    setData(JSON.parse(e.target.value))
                  } catch {
                    // Invalid JSON, keep raw value
                  }
                }}
                className="w-full h-64 font-mono text-xs border border-gray-300 rounded-md p-4 mt-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
            </details>
          </div>
        ) : (
          <>
            <textarea
              value={JSON.stringify(data, null, 2)}
              onChange={(e) => {
                try {
                  setData(JSON.parse(e.target.value))
                } catch {
                  // Invalid JSON, keep raw value
                }
              }}
              className="w-full h-96 font-mono text-sm border border-gray-300 rounded-md p-4 focus:ring-indigo-500 focus:border-indigo-500"
              placeholder='{"title": "Example", "description": "..."}'
            />
            <p className="text-sm text-gray-500 mt-2">
              Edit the JSON data for this section. The structure depends on the section
              type (hero, features, etc.).
            </p>
          </>
        )}
      </div>

      {/* Translate Modal */}
      {content && (
        <TranslateModal
          open={showTranslateModal}
          onOpenChange={setShowTranslateModal}
          sourceLocale={selectedLocale}
          hasGlossary={hasGlossary}
          onTranslate={async ({ sourceLocale, targetLocales, mode }) => {
            const response = await fetch('/api/admin/translate/section', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                sectionContentId: content.id,
                sourceLocale,
                targetLocales,
                mode,
              }),
            })

            if (!response.ok) {
              const error = await response.json()
              throw new Error(error.error || 'Translation failed')
            }

            const data = await response.json()
            // Reload section to show new translations
            await loadSection()
            return data
          }}
        />
      )}
    </div>
  )
}

