'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { supportedLocales, type Locale } from '@/config/locales'

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
}

export default function AdminSectionEditorPage() {
  const router = useRouter()
  const params = useParams()
  const sectionId = params.id as string

  const [section, setSection] = useState<Section | null>(null)
  const [content, setContent] = useState<Content | null>(null)
  const [selectedLocale, setSelectedLocale] = useState<Locale>('fr')
  const [selectedStatus, setSelectedStatus] = useState<'draft' | 'published'>('draft')
  const [data, setData] = useState<any>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

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
          setData({})
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
        alert('Draft saved successfully!')
        loadSection()
      } else {
        const error = await res.json()
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      console.error('Error saving draft:', error)
      alert('Error saving draft')
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
        alert('Published successfully!')
        setSelectedStatus('published')
        loadSection()
      } else {
        const error = await res.json()
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      console.error('Error publishing:', error)
      alert('Error publishing')
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
        alert('Draft reset successfully!')
        setSelectedStatus('draft')
        loadSection()
      } else {
        const error = await res.json()
        alert(`Error: ${error.error}`)
      }
    } catch (error) {
      console.error('Error resetting draft:', error)
      alert('Error resetting draft')
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
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Content Data (JSON)</h2>
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
      </div>
    </div>
  )
}

