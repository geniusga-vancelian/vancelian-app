'use client'

import { EmailSpec, Block } from '../types'
import { Lock, Sparkles } from 'lucide-react'

interface BlockCardProps {
  block: Block
  index: number
  slot: 'core' | 'optional'
  onUpdate: (index: number, updatedBlock: Block) => void
  onRemove?: (index: number) => void
  canRemove: boolean
}

export function BlockCard({ block, index, slot, onUpdate, onRemove, canRemove }: BlockCardProps) {
  const blockType = block.type.toUpperCase()
  const variant = (block as any).variant || 'default'
  
  return (
    <div className="border border-gray-200 rounded-lg p-4 bg-white">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {slot === 'core' ? (
            <Lock className="w-4 h-4 text-gray-500" />
          ) : (
            <Sparkles className="w-4 h-4 text-purple-500" />
          )}
          <span className="font-medium text-sm text-gray-900">
            {blockType} {variant !== 'default' && `(${variant})`}
          </span>
          <span className={`text-xs px-2 py-0.5 rounded ${
            slot === 'core' 
              ? 'bg-gray-100 text-gray-600' 
              : 'bg-purple-100 text-purple-600'
          }`}>
            {slot === 'core' ? 'Core' : 'Optional'}
          </span>
        </div>
        {canRemove && onRemove && (
          <button
            onClick={() => onRemove(index)}
            className="text-sm text-red-600 hover:text-red-700"
          >
            Remove
          </button>
        )}
      </div>
      
      {/* Block content preview */}
      <div className="text-sm text-gray-600 space-y-1">
        {block.type === 'hero' && (
          <>
            <div><strong>Title:</strong> {(block as any).title || '(empty)'}</div>
            {(block as any).subtitle && (
              <div><strong>Subtitle:</strong> {(block as any).subtitle}</div>
            )}
          </>
        )}
        {block.type === 'text' && (
          <>
            {(block as any).heading && (
              <div><strong>Heading:</strong> {(block as any).heading}</div>
            )}
            <div><strong>Body:</strong> {((block as any).body || '').substring(0, 100)}...</div>
          </>
        )}
        {block.type === 'section_title' && (
          <>
            <div><strong>Title:</strong> {(block as any).title || '(empty)'}</div>
            {(block as any).subtitle && (
              <div><strong>Subtitle:</strong> {(block as any).subtitle}</div>
            )}
          </>
        )}
        {block.type === 'bullets' && (
          <>
            {(block as any).heading && (
              <div><strong>Heading:</strong> {(block as any).heading}</div>
            )}
            <div><strong>Items:</strong> {((block as any).items || []).length} bullet(s)</div>
          </>
        )}
        {block.type === 'feature_cards' && (
          <>
            {(block as any).heading && (
              <div><strong>Heading:</strong> {(block as any).heading}</div>
            )}
            <div><strong>Cards:</strong> {((block as any).items || []).length} card(s)</div>
          </>
        )}
        {block.type === 'image' && (
          <>
            <div><strong>Image URL:</strong> {(block as any).image_url || '(empty)'}</div>
            {(block as any).caption && (
              <div><strong>Caption:</strong> {(block as any).caption}</div>
            )}
          </>
        )}
        {block.type === 'cta' && (
          <>
            <div><strong>Label:</strong> {(block as any).label || '(empty)'}</div>
            <div><strong>URL:</strong> {(block as any).url || '(empty)'}</div>
          </>
        )}
        {block.type === 'footer' && (
          <>
            <div><strong>Company:</strong> {(block as any).company_name || '(empty)'}</div>
          </>
        )}
        {(block.type === 'divider' || block.type === 'spacer') && (
          <div className="text-gray-400 italic">No editable content</div>
        )}
      </div>
    </div>
  )
}









