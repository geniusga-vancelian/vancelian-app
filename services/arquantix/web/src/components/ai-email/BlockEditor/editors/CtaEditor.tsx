'use client'

import { CtaBlock } from '../../types'

interface CtaEditorProps {
  block: CtaBlock
  onChange: (block: CtaBlock) => void
}

export function CtaEditor({ block, onChange }: CtaEditorProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Label *
        </label>
        <input
          type="text"
          value={block.label || ''}
          onChange={(e) => onChange({ ...block, label: e.target.value })}
          maxLength={50}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          URL *
        </label>
        <input
          type="url"
          value={block.url || ''}
          onChange={(e) => onChange({ ...block, url: e.target.value })}
          placeholder="https://..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Hint
        </label>
        <input
          type="text"
          value={block.hint || ''}
          onChange={(e) => onChange({ ...block, hint: e.target.value || undefined })}
          maxLength={150}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
        />
      </div>
    </div>
  )
}









