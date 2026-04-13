'use client'

import { TextBlock } from '../../types'

interface TextEditorProps {
  block: TextBlock
  onChange: (block: TextBlock) => void
}

export function TextEditor({ block, onChange }: TextEditorProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Heading
        </label>
        <input
          type="text"
          value={block.heading || ''}
          onChange={(e) => onChange({ ...block, heading: e.target.value || undefined })}
          maxLength={120}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Body *
        </label>
        <textarea
          value={block.body || ''}
          onChange={(e) => onChange({ ...block, body: e.target.value })}
          maxLength={1500}
          rows={6}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
          required
        />
        <div className="text-xs text-gray-500 mt-1">
          {block.body?.length || 0} / 1500 characters
        </div>
      </div>
    </div>
  )
}









