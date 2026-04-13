'use client'

import { useState, useEffect, useMemo } from 'react'
import { X, Search } from 'lucide-react'
import { SectionCategory } from '@/lib/sections/library'

interface SectionType {
  key: string
  label: string
  category: SectionCategory
  schemaVersion: string
  defaultData: any
  allowedOnTemplates: string[]
  description?: string
}

interface SectionLibraryModalProps {
  isOpen: boolean
  onClose: () => void
  onSelect: (typeKey: string) => void
  pageTemplate?: string
}

export function SectionLibraryModal({
  isOpen,
  onClose,
  onSelect,
  pageTemplate = 'homepage',
}: SectionLibraryModalProps) {
  const [types, setTypes] = useState<SectionType[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<SectionCategory | 'ALL'>('ALL')

  useEffect(() => {
    if (!isOpen) return

    fetch('/api/admin/section-types')
      .then((res) => res.json())
      .then((data) => {
        if (data.types) {
          // Filter by template if provided
          const filtered = data.types.filter((type: SectionType) =>
            type.allowedOnTemplates.includes(pageTemplate) ||
            type.allowedOnTemplates.includes('default')
          )
          setTypes(filtered)
        }
        setLoading(false)
      })
      .catch((error) => {
        console.error('Error fetching section types:', error)
        setLoading(false)
      })
  }, [isOpen, pageTemplate])

  const filteredTypes = useMemo(() => {
    let filtered = types

    // Filter by category
    if (selectedCategory !== 'ALL') {
      filtered = filtered.filter((type) => type.category === selectedCategory)
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      filtered = filtered.filter(
        (type) =>
          type.label.toLowerCase().includes(query) ||
          type.key.toLowerCase().includes(query) ||
          type.description?.toLowerCase().includes(query)
      )
    }

    return filtered
  }, [types, selectedCategory, searchQuery])

  const handleSelect = (typeKey: string) => {
    onSelect(typeKey)
    onClose()
  }

  if (!isOpen) return null

  const categories = [
    { value: 'ALL' as const, label: 'All Categories' },
    { value: SectionCategory.LAYOUT, label: 'Layout' },
    { value: SectionCategory.CONTENT, label: 'Content' },
    { value: SectionCategory.PROJECTS, label: 'Projects' },
    { value: SectionCategory.BLOG, label: 'Blog' },
  ]

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold">Section Library</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Filters */}
        <div className="p-4 border-b bg-gray-50">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* Search */}
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search sections..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
            </div>

            {/* Category filter */}
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as SectionCategory | 'ALL')}
              className="px-4 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
            >
              {categories.map((cat) => (
                <option key={cat.value} value={cat.value}>
                  {cat.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-500">Loading section types...</div>
            </div>
          ) : filteredTypes.length === 0 ? (
            <div className="text-center text-gray-500 py-12">
              {searchQuery ? 'No sections found matching your search.' : 'No sections available.'}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredTypes.map((type) => (
                <button
                  key={type.key}
                  onClick={() => handleSelect(type.key)}
                  className="p-4 border border-gray-200 rounded-lg hover:border-indigo-500 hover:shadow-md transition-all text-left group"
                >
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-semibold text-gray-900 group-hover:text-indigo-600">
                      {type.label}
                    </h3>
                    <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded-full">
                      {type.category}
                    </span>
                  </div>
                  {type.description && (
                    <p className="text-sm text-gray-600 mb-2">{type.description}</p>
                  )}
                  <div className="text-xs text-gray-400">
                    Key: <code className="font-mono">{type.key}</code>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 hover:text-gray-900 transition-colors"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  )
}









