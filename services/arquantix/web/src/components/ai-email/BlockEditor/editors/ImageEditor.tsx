'use client'

import { ImageBlock } from '../../types'

interface ImageEditorProps {
  block: ImageBlock
  onChange: (block: ImageBlock) => void
}

export function ImageEditor({ block, onChange }: ImageEditorProps) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Image URL *
        </label>
        <input
          type="url"
          value={block.image_url || ''}
          onChange={(e) => onChange({ ...block, image_url: e.target.value })}
          placeholder="https://..."
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Alt Text
        </label>
        <input
          type="text"
          value={block.alt_text || ''}
          onChange={(e) => onChange({ ...block, alt_text: e.target.value || undefined })}
          maxLength={200}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Caption
        </label>
        <input
          type="text"
          value={block.caption || ''}
          onChange={(e) => onChange({ ...block, caption: e.target.value || undefined })}
          maxLength={200}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
        />
      </div>
    </div>
  )
}









