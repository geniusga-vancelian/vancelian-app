'use client'

import { useState, useEffect } from 'react'
import { MediaField } from './MediaField'
import { ProjectSelector } from './ProjectSelector'
import { ConfirmDialog } from './ConfirmDialog'

interface SectionEditorProps {
  sectionKey: string
  data: any
  onChange: (data: any) => void
}

/**
 * Section-specific editor components
 * Provides structured editing based on section type
 */
export function SectionEditor({ sectionKey, data, onChange }: SectionEditorProps) {
  const updateField = (path: string, value: any) => {
    const keys = path.split('.')
    const newData = { ...data }
    let current: any = newData

    for (let i = 0; i < keys.length - 1; i++) {
      const key = keys[i]
      if (!(key in current) || typeof current[key] !== 'object' || current[key] === null) {
        current[key] = {}
      }
      current = current[key]
    }

    current[keys[keys.length - 1]] = value
    onChange(newData)
  }

  // Hero section editor
  if (sectionKey === 'hero') {
    return (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title
          </label>
          <input
            type="text"
            value={data.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Subtitle
          </label>
          <input
            type="text"
            value={data.subtitle || ''}
            onChange={(e) => updateField('subtitle', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div>
          <MediaField
            value={data.backgroundMediaId || null}
            onChange={(mediaId) => updateField('backgroundMediaId', mediaId)}
            label="Background Image"
            allowClear={true}
            preview={true}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CTA Text
          </label>
          <input
            type="text"
            value={data.ctaText || ''}
            onChange={(e) => updateField('ctaText', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CTA Link
          </label>
          <input
            type="text"
            value={data.ctaLink || ''}
            onChange={(e) => updateField('ctaLink', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>
      </div>
    )
  }

  // Projects section editor
  if (sectionKey === 'projects' || sectionKey === 'project_grid') {
    return (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title
          </label>
          <input
            type="text"
            value={data.title || ''}
            onChange={(e) => updateField('title', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            value={data.description || ''}
            onChange={(e) => updateField('description', e.target.value)}
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Limit
          </label>
          <input
            type="number"
            min="1"
            max="20"
            value={data.limit || 3}
            onChange={(e) => updateField('limit', parseInt(e.target.value, 10) || 3)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Maximum number of projects to display (default: 3)
          </p>
        </div>

        <div>
          <ProjectSelector
            selectedProjectIds={data.selectedProjectIds || []}
            onChange={(projectIds) => updateField('selectedProjectIds', projectIds)}
            limit={data.limit || 3}
          />
          <p className="text-xs text-gray-500 mt-1">
            {data.selectedProjectIds && data.selectedProjectIds.length > 0
              ? 'Selected projects will be displayed in the specified order. If none selected, latest published projects will be shown.'
              : 'No projects selected. Latest published projects will be displayed.'}
          </p>
        </div>
      </div>
    )
  }

  // FAQ section editor
  if (sectionKey === 'faq') {
    const items = data.items || []
    const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

    const generateId = () => {
      return `faq-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    }

    const addItem = () => {
      const newItem = {
        id: generateId(),
        question: '',
        answerMarkdown: '',
      }
      updateField('items', [...items, newItem])
    }

    const removeItem = (id: string) => {
      updateField(
        'items',
        items.filter((item: any) => item.id !== id)
      )
      setDeleteConfirm(null)
    }

    const updateItem = (id: string, field: 'question' | 'answerMarkdown', value: string) => {
      updateField(
        'items',
        items.map((item: any) => (item.id === id ? { ...item, [field]: value } : item))
      )
    }

    const moveItem = (index: number, direction: 'up' | 'down') => {
      const newItems = [...items]
      const targetIndex = direction === 'up' ? index - 1 : index + 1
      if (targetIndex >= 0 && targetIndex < newItems.length) {
        ;[newItems[index], newItems[targetIndex]] = [newItems[targetIndex], newItems[index]]
        updateField('items', newItems)
      }
    }

    return (
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Title
          </label>
          <input
            type="text"
            value={data.title || 'FAQ'}
            onChange={(e) => updateField('title', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Subtitle
          </label>
          <input
            type="text"
            value={data.subtitle || 'Frequently Asked Questions'}
            onChange={(e) => updateField('subtitle', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500"
          />
        </div>

        <div>
          <div className="flex justify-between items-center mb-2">
            <label className="block text-sm font-medium text-gray-700">
              FAQ Items
            </label>
            <button
              onClick={addItem}
              className="px-3 py-1 text-sm bg-indigo-600 text-white rounded-md hover:bg-indigo-700"
            >
              + Add question
            </button>
          </div>

          {items.length === 0 ? (
            <p className="text-sm text-gray-500 py-4 text-center border border-gray-200 rounded-md">
              No FAQ items yet. Click "Add question" to get started.
            </p>
          ) : (
            <div className="space-y-4">
              {items.map((item: any, index: number) => (
                <div
                  key={item.id}
                  className="border border-gray-200 rounded-lg p-4 bg-gray-50"
                >
                  <div className="flex justify-between items-start mb-3">
                    <span className="text-xs font-medium text-gray-500">
                      Question {index + 1}
                    </span>
                    <div className="flex gap-2">
                      {index > 0 && (
                        <button
                          onClick={() => moveItem(index, 'up')}
                          className="text-gray-600 hover:text-gray-900 text-sm"
                          title="Move up"
                        >
                          ↑
                        </button>
                      )}
                      {index < items.length - 1 && (
                        <button
                          onClick={() => moveItem(index, 'down')}
                          className="text-gray-600 hover:text-gray-900 text-sm"
                          title="Move down"
                        >
                          ↓
                        </button>
                      )}
                      <button
                        onClick={() => setDeleteConfirm(item.id)}
                        className="text-red-600 hover:text-red-900 text-sm"
                        title="Remove"
                      >
                        Remove
                      </button>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Question
                      </label>
                      <input
                        type="text"
                        value={item.question || ''}
                        onChange={(e) => updateItem(item.id, 'question', e.target.value)}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm"
                        placeholder="Enter question..."
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Answer (Markdown)
                      </label>
                      <textarea
                        value={item.answerMarkdown || ''}
                        onChange={(e) => updateItem(item.id, 'answerMarkdown', e.target.value)}
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-indigo-500 focus:border-indigo-500 text-sm font-mono"
                        placeholder="Enter answer in Markdown format..."
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Markdown supported: **bold**, *italic*, links, lists, etc.
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <ConfirmDialog
          open={deleteConfirm !== null}
          onOpenChange={(open) => !open && setDeleteConfirm(null)}
          title="Remove FAQ Item"
          description="Are you sure you want to remove this FAQ item? This action cannot be undone."
          onConfirm={() => { deleteConfirm && removeItem(deleteConfirm) }}
        />
      </div>
    )
  }

  // Default: fallback to JSON editor
  return null
}

