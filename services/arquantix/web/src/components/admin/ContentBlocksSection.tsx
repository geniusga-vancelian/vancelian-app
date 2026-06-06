'use client'

import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Download, FileUp, Plus } from 'lucide-react'
import { ArticleBlockType } from '@prisma/client'
import { Button } from '@/components/ui/button'
import { MediaField } from '@/components/admin/MediaField'
import { VaultDocumentsListModuleEditor } from '@/components/admin/VaultDocumentsListModuleEditor'
import { VaultKeyInformationModuleEditor } from '@/components/admin/VaultKeyInformationModuleEditor'
import { VaultLocalisationModuleEditor } from '@/components/admin/VaultLocalisationModuleEditor'
import { VaultMediaCarouselModuleEditor } from '@/components/admin/VaultMediaCarouselModuleEditor'
import { VaultVideoBlockArticleModuleEditor } from '@/components/admin/VaultVideoBlockArticleModuleEditor'
import { ArticleStepsModuleEditor } from '@/components/admin/ArticleStepsModuleEditor'
import { HowItWorksCarouselEditor } from '@/components/admin/HowItWorksCarouselEditor'
import { BLOCK_TYPE_LABELS, type AddableBlockType } from '@/lib/admin/articleBlockCatalog'
import { getBlockSummary } from '@/lib/admin/articleBlockSummary'

export interface ContentBlock {
  id: string
  type: ArticleBlockType
  order: number
  data: any
}

export interface ContentBlocksSectionProps {
  /** Liste de blocs à éditer (ordre préservé). */
  blocks: ContentBlock[]
  /** Mise à jour locale d'un bloc (data complète). Le parent décide du moment de persister. */
  onUpdateBlock: (blockId: string, data: any) => void
  /** Patch partiel (utilisé par les éditeurs Vault* type onPatch). */
  onPatchBlock: (blockId: string, patch: Record<string, unknown>) => void
  /** Suppression d'un bloc (parent appelle l'API + refetch). */
  onDeleteBlock: (blockId: string) => void
  /** Réordonnancement (parent appelle l'API reorder + refetch). */
  onReorderBlocks: (orderedBlockIds: string[]) => void
  /** Action « Ajouter un bloc » : navigation ou modal au choix du parent. */
  onClickAddBlock: () => void | Promise<void>
  /** Export Markdown des blocs (optionnel). */
  onClickExportMarkdown?: () => void
  /** Import Markdown blueprint (optionnel). */
  onClickImportMarkdown?: () => void
  /** Désactive le bouton « Ajouter » pendant un save. */
  saving?: boolean
  /** Identifiant utilisé pour ne déclencher l'auto-collapse qu'une fois par entité. */
  entityId: string
  /** Titre de la section (par défaut « Content Blocks »). */
  title?: string
}

/**
 * Section éditeur de « Content Blocks » réutilisable. Extraite de
 * `src/app/admin/articles/[id]/page.tsx` pour permettre à l'admin Help (puis
 * au futur hub `/admin/content`) d'embarquer le même builder sans dupliquer
 * la logique de rendu, de pliage et de tri.
 *
 * Le composant gère lui-même :
 * - l'auto-collapse si > 5 blocs au premier rendu (par `entityId`),
 * - les toggles individuels et le « Tout déplier / replier »,
 * - le rendu des éditeurs spécifiques par type (HEADING, PARAGRAPH, …
 *   jusqu'aux modules Vault).
 *
 * Le parent reste maître des effets de bord serveur (POST/PUT/DELETE).
 */
export function ContentBlocksSection({
  blocks,
  onUpdateBlock,
  onPatchBlock,
  onDeleteBlock,
  onReorderBlocks,
  onClickAddBlock,
  onClickExportMarkdown,
  onClickImportMarkdown,
  saving = false,
  entityId,
  title = 'Content Blocks',
}: ContentBlocksSectionProps) {
  const [collapsedBlocks, setCollapsedBlocks] = useState<Set<string>>(new Set())
  const collapseInitRef = useRef<string | null>(null)

  // Auto-collapse si > 5 blocs, une seule fois par `entityId`.
  useEffect(() => {
    if (!entityId || collapseInitRef.current === entityId) return
    if (blocks.length === 0) return
    collapseInitRef.current = entityId
    if (blocks.length > 5) {
      setCollapsedBlocks(new Set(blocks.map((b) => b.id)))
    }
  }, [entityId, blocks])

  const toggleBlockCollapsed = (blockId: string) => {
    setCollapsedBlocks((prev) => {
      const next = new Set(prev)
      if (next.has(blockId)) next.delete(blockId)
      else next.add(blockId)
      return next
    })
  }

  const allCollapsed =
    blocks.length > 0 && blocks.every((b) => collapsedBlocks.has(b.id))

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-semibold text-gray-900">{title}</h2>
          {blocks.length > 0 ? (
            <span className="text-xs text-gray-500">{blocks.length} bloc(s)</span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {blocks.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                setCollapsedBlocks(allCollapsed ? new Set() : new Set(blocks.map((b) => b.id)))
              }
            >
              {allCollapsed ? 'Tout déplier' : 'Tout replier'}
            </Button>
          ) : null}
          {onClickExportMarkdown ? (
            <Button
              variant="outline"
              size="sm"
              disabled={saving || blocks.length === 0}
              onClick={onClickExportMarkdown}
              title="Télécharger les Content Blocks au format Markdown"
            >
              <Download className="mr-1 h-4 w-4" /> Export Markdown
            </Button>
          ) : null}
          {onClickImportMarkdown ? (
            <Button
              variant="outline"
              size="sm"
              disabled={saving}
              onClick={onClickImportMarkdown}
              title="Importer un fichier .md (Content Blocks ou blueprint article complet)"
            >
              <FileUp className="mr-1 h-4 w-4" /> Importer un Markdown
            </Button>
          ) : null}
          <Button
            size="sm"
            className="bg-indigo-600 hover:bg-indigo-700"
            disabled={saving}
            onClick={() => {
              void onClickAddBlock()
            }}
            title="Ouvrir le catalogue de blocs avec preview"
          >
            <Plus className="mr-1 h-4 w-4" /> Ajouter un bloc
          </Button>
        </div>
      </div>

      <div className="space-y-2">
        {blocks.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No blocks yet. Add your first block!</p>
        ) : (
          blocks.map((block, index) => {
            const isCollapsed = collapsedBlocks.has(block.id)
            const summary = getBlockSummary(block)
            const typeLabel =
              BLOCK_TYPE_LABELS[block.type as AddableBlockType] ?? block.type
            return (
              <div key={block.id} className="rounded-lg border border-gray-200 bg-white">
                <div className="flex items-center gap-2 p-2">
                  <button
                    type="button"
                    onClick={() => toggleBlockCollapsed(block.id)}
                    className="rounded p-1 text-gray-500 hover:bg-gray-100"
                    title={isCollapsed ? 'Déplier' : 'Replier'}
                    aria-expanded={!isCollapsed}
                  >
                    <ChevronDown
                      className={`h-4 w-4 transition-transform ${isCollapsed ? '-rotate-90' : ''}`}
                    />
                  </button>
                  <span className="shrink-0 rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-600">
                    {typeLabel}
                  </span>
                  <button
                    type="button"
                    onClick={() => toggleBlockCollapsed(block.id)}
                    className="min-w-0 flex-1 truncate text-left text-sm text-gray-900 hover:text-indigo-700"
                    title={summary}
                  >
                    {summary}
                  </button>
                  <div className="flex shrink-0 items-center gap-0.5">
                    {index > 0 && (
                      <button
                        onClick={() => {
                          const newOrder = [...blocks]
                          ;[newOrder[index], newOrder[index - 1]] = [
                            newOrder[index - 1],
                            newOrder[index],
                          ]
                          onReorderBlocks(newOrder.map((b) => b.id))
                        }}
                        className="rounded p-1 text-gray-500 hover:bg-gray-100"
                        title="Monter"
                      >
                        ↑
                      </button>
                    )}
                    {index < blocks.length - 1 && (
                      <button
                        onClick={() => {
                          const newOrder = [...blocks]
                          ;[newOrder[index], newOrder[index + 1]] = [
                            newOrder[index + 1],
                            newOrder[index],
                          ]
                          onReorderBlocks(newOrder.map((b) => b.id))
                        }}
                        className="rounded p-1 text-gray-500 hover:bg-gray-100"
                        title="Descendre"
                      >
                        ↓
                      </button>
                    )}
                    <button
                      onClick={() => onDeleteBlock(block.id)}
                      className="rounded px-2 py-0.5 text-xs text-red-600 hover:bg-red-50"
                      title="Supprimer ce bloc"
                    >
                      Supprimer
                    </button>
                  </div>
                </div>
                {!isCollapsed ? (
                  <div className="space-y-2 border-t border-gray-100 p-3">
                    {block.type === ArticleBlockType.HEADING && (
                      <input
                        type="text"
                        value={(block.data as any).text || ''}
                        onChange={(e) =>
                          onUpdateBlock(block.id, { ...block.data, text: e.target.value })
                        }
                        className="w-full px-3 py-2 border border-gray-300 rounded-md text-xl font-bold"
                        placeholder="Heading text"
                      />
                    )}
                    {block.type === ArticleBlockType.PARAGRAPH && (
                      <textarea
                        value={(block.data as any).text || ''}
                        onChange={(e) =>
                          onUpdateBlock(block.id, { ...block.data, text: e.target.value })
                        }
                        rows={4}
                        className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono text-sm"
                        placeholder="Paragraph text (Markdown supporté — rendu visible dans la preview à droite)"
                      />
                    )}
                    {block.type === ArticleBlockType.QUOTE && (
                      <div className="space-y-2">
                        <textarea
                          value={(block.data as any).text || ''}
                          onChange={(e) =>
                            onUpdateBlock(block.id, { ...block.data, text: e.target.value })
                          }
                          rows={3}
                          className="w-full px-3 py-2 border border-gray-300 rounded-md italic"
                          placeholder="Quote text"
                        />
                        <input
                          type="text"
                          value={(block.data as any).author || ''}
                          onChange={(e) =>
                            onUpdateBlock(block.id, { ...block.data, author: e.target.value })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md"
                          placeholder="Author (optional)"
                        />
                      </div>
                    )}
                    {block.type === ArticleBlockType.BULLET_LIST && (
                      <ItemListEditor block={block} onUpdate={onUpdateBlock} placeholderPrefix="Item" addLabel="+ Add item" />
                    )}
                    {block.type === ArticleBlockType.NUMBERED_LIST && (
                      <ItemListEditor block={block} onUpdate={onUpdateBlock} placeholderPrefix="Élément" addLabel="+ Ajouter une ligne" />
                    )}
                    {block.type === ArticleBlockType.IMAGE && (
                      <div className="rounded-md border border-amber-200 bg-amber-50/90 p-3 text-sm text-amber-950">
                        <p className="font-medium">Bloc Image (obsolète)</p>
                        <p className="mt-1 text-amber-900/90">
                          Supprimez ce bloc et ajoutez un <strong>Carrousel</strong> avec une ou plusieurs images — le
                          rendu public est déjà celui du carrousel (y compris une seule image).
                        </p>
                      </div>
                    )}
                    {block.type === ArticleBlockType.VIDEO && (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={(block.data as any).url || ''}
                          onChange={(e) =>
                            onUpdateBlock(block.id, { ...block.data, url: e.target.value })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md"
                          placeholder="Video URL (YouTube/Vimeo)"
                        />
                        <input
                          type="text"
                          value={(block.data as any).caption || ''}
                          onChange={(e) =>
                            onUpdateBlock(block.id, { ...block.data, caption: e.target.value })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md"
                          placeholder="Caption"
                        />
                      </div>
                    )}
                    {block.type === ArticleBlockType.DOCUMENT && (
                      <div className="space-y-2">
                        <MediaField
                          value={(block.data as any).mediaId || undefined}
                          onChange={(mediaId) =>
                            onUpdateBlock(block.id, { ...block.data, mediaId: mediaId || '' })
                          }
                          label="Document (PDF)"
                          allowClear
                        />
                        <input
                          type="text"
                          value={(block.data as any).title || ''}
                          onChange={(e) =>
                            onUpdateBlock(block.id, { ...block.data, title: e.target.value })
                          }
                          className="w-full px-3 py-2 border border-gray-300 rounded-md"
                          placeholder="Document title"
                        />
                      </div>
                    )}
                    {block.type === ArticleBlockType.MEDIA_IMAGE_CAROUSEL && (
                      <VaultMediaCarouselModuleEditor
                        content={(block.data || {}) as Record<string, unknown>}
                        onPatch={(patch) => onPatchBlock(block.id, patch)}
                      />
                    )}
                    {block.type === ArticleBlockType.LOCALISATION && (
                      <VaultLocalisationModuleEditor
                        content={(block.data || {}) as Record<string, unknown>}
                        onPatch={(patch) => onPatchBlock(block.id, patch)}
                      />
                    )}
                    {block.type === ArticleBlockType.DOCUMENTS_LIST && (
                      <VaultDocumentsListModuleEditor
                        content={(block.data || {}) as Record<string, unknown>}
                        onPatch={(patch) => onPatchBlock(block.id, patch)}
                      />
                    )}
                    {block.type === ArticleBlockType.KEY_INFORMATION && (
                      <VaultKeyInformationModuleEditor
                        content={(block.data || {}) as Record<string, unknown>}
                        onPatch={(patch) => onPatchBlock(block.id, patch)}
                      />
                    )}
                    {block.type === ArticleBlockType.VIDEO_BLOCK_ARTICLE && (
                      <VaultVideoBlockArticleModuleEditor
                        content={(block.data || {}) as Record<string, unknown>}
                        onPatch={(patch) => onPatchBlock(block.id, patch)}
                      />
                    )}
                    {block.type === ArticleBlockType.STEPS_MODULE && (
                      <ArticleStepsModuleEditor
                        content={(block.data || {}) as Record<string, unknown>}
                        onPatch={(patch) => onPatchBlock(block.id, patch)}
                      />
                    )}
                    {block.type === ArticleBlockType.HOW_IT_WORKS_CAROUSEL && (
                      <HowItWorksCarouselEditor
                        content={(block.data || {}) as Record<string, unknown>}
                        onPatch={(patch) => onPatchBlock(block.id, patch)}
                      />
                    )}
                  </div>
                ) : null}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

/** Petit éditeur de liste d'items (BULLET_LIST / NUMBERED_LIST). */
function ItemListEditor({
  block,
  onUpdate,
  placeholderPrefix,
  addLabel,
}: {
  block: ContentBlock
  onUpdate: (blockId: string, data: any) => void
  placeholderPrefix: string
  addLabel: string
}) {
  const items: string[] = (block.data as any)?.items ?? ['']
  return (
    <div className="space-y-2">
      {items.map((item, i) => (
        <input
          key={i}
          type="text"
          value={item}
          onChange={(e) => {
            const next = [...items]
            next[i] = e.target.value
            onUpdate(block.id, { ...block.data, items: next })
          }}
          className="w-full px-3 py-2 border border-gray-300 rounded-md"
          placeholder={`${placeholderPrefix} ${i + 1}`}
        />
      ))}
      <button
        onClick={() => {
          const next = [...items, '']
          onUpdate(block.id, { ...block.data, items: next })
        }}
        className="text-sm text-indigo-600 hover:text-indigo-900"
      >
        {addLabel}
      </button>
    </div>
  )
}
