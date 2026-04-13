'use client'

import { useState } from 'react'
import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { slugify, isValidSlug } from '@/lib/utils/slugify'

interface CreatePageModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess: () => void
}

export function CreatePageModal({ isOpen, onClose, onSuccess }: CreatePageModalProps) {
  const [template, setTemplate] = useState('homepage')
  const [title, setTitle] = useState('')
  const [slug, setSlug] = useState('')
  const [description, setDescription] = useState('')
  const [autoSlug, setAutoSlug] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!isOpen) return null

  const handleTitleChange = (value: string) => {
    setTitle(value)
    if (autoSlug) {
      setSlug(slugify(value))
    }
  }

  const handleSlugChange = (value: string) => {
    setSlug(value.toLowerCase())
    setAutoSlug(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)

    if (!slug.trim()) {
      setError('Slug is required')
      setLoading(false)
      return
    }

    if (!isValidSlug(slug)) {
      setError('Slug must be lowercase, alphanumeric with hyphens only (max 60 chars)')
      setLoading(false)
      return
    }

    try {
      const response = await fetch('/api/admin/pages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template,
          title: title.trim() || undefined,
          slug: slug.trim(),
          description: description.trim() || undefined,
        }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to create page')
      }

      const data = await response.json()
      onSuccess()
      onClose()
      // Reset form
      setTitle('')
      setSlug('')
      setDescription('')
      setAutoSlug(true)
      setError(null)
      // Redirect to the new page
      window.location.href = `/admin/pages/${data.page.slug}`
    } catch (e: any) {
      setError(e.message || 'Failed to create page')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Create New Page</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-100 text-red-800 rounded-md text-sm">
              {error}
            </div>
          )}

          <div>
            <label htmlFor="template" className="block text-sm font-medium text-gray-700 mb-1">
              Template
            </label>
            <select
              id="template"
              value={template}
              onChange={(e) => setTemplate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
            >
              <option value="homepage">Homepage</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">Template determines which sections are created automatically</p>
          </div>

          <div>
            <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
              Title <span className="text-gray-400">(optional but recommended)</span>
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => handleTitleChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="About Us"
            />
          </div>

          <div>
            <label htmlFor="slug" className="block text-sm font-medium text-gray-700 mb-1">
              Slug <span className="text-red-500">*</span>
            </label>
            <input
              id="slug"
              type="text"
              value={slug}
              onChange={(e) => handleSlugChange(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 font-mono text-sm"
              placeholder="about-us"
              required
            />
            <p className="text-xs text-gray-500 mt-1">
              Lowercase, alphanumeric with hyphens only. Max 60 chars. "home" is reserved.
            </p>
            {slug && !isValidSlug(slug) && (
              <p className="text-xs text-red-600 mt-1">Invalid slug format</p>
            )}
          </div>

          <div>
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Description <span className="text-gray-400">(optional)</span>
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
              placeholder="Brief description of this page..."
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={loading || !slug.trim() || !isValidSlug(slug)}
            >
              {loading ? 'Creating...' : 'Create Page'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}









