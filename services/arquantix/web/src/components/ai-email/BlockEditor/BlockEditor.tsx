'use client'

import { useState } from 'react'
import { EmailSpec, Block } from '../types'
import { BlockCard } from './BlockCard'
import { HeroEditor } from './editors/HeroEditor'
import { TextEditor } from './editors/TextEditor'
import { ImageEditor } from './editors/ImageEditor'
import { CtaEditor } from './editors/CtaEditor'
import { getBlockDefinition } from '../registry-helpers'

interface BlockEditorProps {
  spec: EmailSpec
  onUpdate: (spec: EmailSpec) => void
}

export function BlockEditor({ spec, onUpdate }: BlockEditorProps) {
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [showAddMenu, setShowAddMenu] = useState(false)

  const handleBlockUpdate = (index: number, updatedBlock: Block) => {
    const newBlocks = [...spec.blocks]
    newBlocks[index] = updatedBlock
    onUpdate({ ...spec, blocks: newBlocks })
    setEditingIndex(null)
  }

  const handleBlockRemove = (index: number) => {
    const block = spec.blocks[index]
    const definition = getBlockDefinition(block.type, (block as any).variant || 'default')
    
    if (definition.slot === 'optional') {
      const newBlocks = spec.blocks.filter((_, i) => i !== index)
      onUpdate({ ...spec, blocks: newBlocks })
    }
  }

  const handleAddBlock = (blockType: string, variant: string) => {
    // Create new block based on type
    const newBlock = createEmptyBlock(blockType, variant)
    if (newBlock) {
      // Insert before footer
      const footerIndex = spec.blocks.findIndex(b => b.type === 'footer')
      const insertIndex = footerIndex >= 0 ? footerIndex : spec.blocks.length
      const newBlocks = [...spec.blocks]
      newBlocks.splice(insertIndex, 0, newBlock)
      onUpdate({ ...spec, blocks: newBlocks })
    }
    setShowAddMenu(false)
  }

  const optionalBlockTypes = [
    { type: 'image', variant: 'contained', label: 'Image' },
    { type: 'divider', variant: 'default', label: 'Divider' },
    { type: 'spacer', variant: 'md', label: 'Spacer (md)' },
    { type: 'spacer', variant: 'lg', label: 'Spacer (lg)' },
  ]

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Email Blocks</h3>
        <button
          onClick={() => setShowAddMenu(!showAddMenu)}
          className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 text-sm"
        >
          + Add Optional Block
        </button>
      </div>

      {showAddMenu && (
        <div className="border border-gray-200 rounded-lg p-2 bg-white shadow-lg">
          <div className="text-xs font-medium text-gray-500 mb-2">Optional Blocks</div>
          <div className="space-y-1">
            {optionalBlockTypes.map(({ type, variant, label }) => (
              <button
                key={`${type}-${variant}`}
                onClick={() => handleAddBlock(type, variant)}
                className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 rounded"
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-4">
        {spec.blocks.map((block, index) => {
          const definition = getBlockDefinition(block.type, (block as any).variant || 'default')
          const slot = definition.slot
          const canRemove = slot === 'optional' && block.type !== 'footer'

          return (
            <div key={index}>
              <BlockCard
                block={block}
                index={index}
                slot={slot}
                onUpdate={handleBlockUpdate}
                onRemove={canRemove ? handleBlockRemove : undefined}
                canRemove={canRemove}
              />
              
              {editingIndex === index && (
                <div className="mt-4 p-4 border border-gray-200 rounded-lg bg-gray-50">
                  {block.type === 'hero' && (
                    <HeroEditor
                      block={block as any}
                      onChange={(updated) => handleBlockUpdate(index, updated)}
                    />
                  )}
                  {block.type === 'text' && (
                    <TextEditor
                      block={block as any}
                      onChange={(updated) => handleBlockUpdate(index, updated)}
                    />
                  )}
                  {block.type === 'image' && (
                    <ImageEditor
                      block={block as any}
                      onChange={(updated) => handleBlockUpdate(index, updated)}
                    />
                  )}
                  {block.type === 'cta' && (
                    <CtaEditor
                      block={block as any}
                      onChange={(updated) => handleBlockUpdate(index, updated)}
                    />
                  )}
                  {(block.type === 'section_title' || block.type === 'bullets' || block.type === 'footer' || block.type === 'divider' || block.type === 'spacer' || block.type === 'feature_cards') && (
                    <div className="text-sm text-gray-500">
                      Editor for {block.type} not yet implemented. Use AI Copilot mode to edit.
                    </div>
                  )}
                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={() => setEditingIndex(null)}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => setEditingIndex(null)}
                      className="px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800 text-sm"
                    >
                      Save
                    </button>
                  </div>
                </div>
              )}
              
              {editingIndex !== index && (
                <button
                  onClick={() => setEditingIndex(index)}
                  className="mt-2 text-sm text-gray-600 hover:text-gray-900"
                >
                  Edit
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

function createEmptyBlock(type: string, variant: string): Block | null {
  switch (type) {
    case 'image':
      return {
        type: 'image',
        variant: 'contained',
        image_url: '',
        alt_text: undefined,
        caption: undefined,
      } as any
    case 'divider':
      return {
        type: 'divider',
        variant: 'default',
      } as any
    case 'spacer':
      return {
        type: 'spacer',
        variant: variant as 'md' | 'lg',
      } as any
    default:
      return null
  }
}

