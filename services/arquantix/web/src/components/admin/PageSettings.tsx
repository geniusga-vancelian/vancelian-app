'use client'

import { useState, useEffect } from 'react'
import { Save } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { slugify, isValidSlug, calculateUrlPath } from '@/lib/utils/slugify'

interface Page {
  id: string
  slug: string
  urlPath: string
  title: string | null
  template: string
  themeColor?: string
  description: string | null
}

interface PageSettingsProps {
  page: Page
  onUpdate: () => void
}

export function PageSettings({ page, onUpdate }: PageSettingsProps) {
  const [title, setTitle] = useState(page.title || '')
  const [slug, setSlug] = useState(page.slug)
  const [description, setDescription] = useState(page.description || '')
  const [template, setTemplate] = useState(page.template || 'homepage')
  const [themeColor, setThemeColor] = useState(page.themeColor || 'dark')
  const [autoSlug, setAutoSlug] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const urlPath = calculateUrlPath(slug)
  const isHomePage = page.slug === 'home'

  useEffect(() => {
    setTitle(page.title || '')
    setSlug(page.slug)
    setDescription(page.description || '')
    setTemplate(page.template || 'homepage')
    setThemeColor(page.themeColor || 'dark')
  }, [page])

  const handleTitleChange = (value: string) => {
    setTitle(value)
    if (autoSlug && !isHomePage) {
      setSlug(slugify(value))
    }
  }

  const handleSlugChange = (value: string) => {
    setSlug(value.toLowerCase())
    setAutoSlug(false)
  }

  const handleSave = async () => {
    setError(null)
    setSuccess(false)
    setSaving(true)

    if (!slug.trim()) {
      setError('Slug is required')
      setSaving(false)
      return
    }

    if (!isValidSlug(slug)) {
      setError('Slug must be lowercase, alphanumeric with hyphens only (max 60 chars)')
      setSaving(false)
      return
    }

    try {
      const response = await fetch(`/api/admin/pages/${page.slug}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim() || null,
          slug: slug.trim(),
          description: description.trim() || null,
          template: template,
          themeColor: themeColor,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to update page')
      }

      const data = await response.json()
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)

      // If slug changed, redirect to new URL
      if (data.page.slug !== page.slug) {
        window.location.href = `/admin/pages/${data.page.slug}`
      } else {
        onUpdate()
      }
    } catch (e: any) {
      setError(e.message || 'Failed to update page')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow p-6 mb-6">
      <h2 className="text-xl font-semibold mb-4">Page Settings</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-100 text-red-800 rounded-md text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-100 text-green-800 rounded-md text-sm">
          Page settings saved successfully!
        </div>
      )}

      <div className="space-y-4">
        <div>
          <label htmlFor="page-title" className="block text-sm font-medium text-gray-700 mb-1">
            Title
          </label>
          <input
            id="page-title"
            type="text"
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Page title"
          />
        </div>

        <div>
          <label htmlFor="page-slug" className="block text-sm font-medium text-gray-700 mb-1">
            Slug
          </label>
          <input
            id="page-slug"
            type="text"
            value={slug}
            onChange={(e) => handleSlugChange(e.target.value)}
            disabled={isHomePage}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm disabled:bg-gray-100 disabled:cursor-not-allowed"
            placeholder="page-slug"
          />
          {isHomePage && (
            <p className="text-xs text-gray-500 mt-1">
              Slug "home" is reserved and cannot be changed
            </p>
          )}
          {!isHomePage && !isValidSlug(slug) && slug && (
            <p className="text-xs text-red-600 mt-1">Invalid slug format</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            URL Path (read-only)
          </label>
          <input
            type="text"
            value={urlPath}
            disabled
            className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 font-mono text-sm cursor-not-allowed"
          />
          <p className="text-xs text-gray-500 mt-1">
            This URL is automatically calculated from the slug
          </p>
        </div>

        <div>
          <label htmlFor="page-description" className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            id="page-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Brief description of this page..."
          />
        </div>

        <div>
          <label htmlFor="page-template" className="block text-sm font-medium text-gray-700 mb-1">
            Template
          </label>
          <select
            id="page-template"
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="homepage">Homepage</option>
            <option value="blog">Blog</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            The template determines how the page is rendered on the frontend
          </p>
        </div>

        <div>
          <label htmlFor="page-theme-color" className="block text-sm font-medium text-gray-700 mb-1">
            Theme Color
          </label>
          <select
            id="page-theme-color"
            value={themeColor}
            onChange={(e) => setThemeColor(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="dark">Dark</option>
            <option value="light">Light</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Determines the navigation bar colors (dark = white text/logo, light = black text/logo)
          </p>
        </div>

        <div className="flex justify-end pt-4 border-t">
          <Button onClick={handleSave} disabled={saving || !isValidSlug(slug)}>
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Page Settings'}
          </Button>
        </div>
      </div>
    </div>
  )
}

