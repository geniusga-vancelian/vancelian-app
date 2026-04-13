'use client'

import { HeroBlock } from '../../types'

interface HeroEditorProps {
  block: HeroBlock
  onChange: (block: HeroBlock) => void
}

export function HeroEditor({ block, onChange }: HeroEditorProps) {
  const variant = block.variant || 'text_only'
  
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Title *
        </label>
        <input
          type="text"
          value={block.title || ''}
          onChange={(e) => onChange({ ...block, title: e.target.value })}
          maxLength={120}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
          required
        />
      </div>
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Subtitle
        </label>
        <input
          type="text"
          value={block.subtitle || ''}
          onChange={(e) => onChange({ ...block, subtitle: e.target.value || undefined })}
          maxLength={200}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
        />
      </div>
      
      {variant === 'image_top' && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Image URL
          </label>
          <input
            type="url"
            value={block.image_url || ''}
            onChange={(e) => onChange({ ...block, image_url: e.target.value || undefined })}
            placeholder="https://..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
          />
        </div>
      )}
      
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          CTA Label
        </label>
        <input
          type="text"
          value={block.cta_label || ''}
          onChange={(e) => onChange({ ...block, cta_label: e.target.value || undefined })}
          maxLength={50}
          className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
        />
      </div>
      
      {block.cta_label && (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            CTA URL
          </label>
          <input
            type="url"
            value={block.cta_url || ''}
            onChange={(e) => onChange({ ...block, cta_url: e.target.value || undefined })}
            placeholder="https://..."
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900"
          />
        </div>
      )}
    </div>
  )
}









