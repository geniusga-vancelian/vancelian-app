import { ArticleBlockType } from '@prisma/client'
import type { PrismaClient } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { enrichPublicArticleBlockData } from '@/lib/blog/enrichPublicArticleBlockData'

/** Bloc article après fusion i18n + résolution médias / enrichissement Vault (web + API). */
export interface NormalizedArticleBlock {
  id: string
  type: ArticleBlockType
  order: number
  data: unknown
  imageUrl?: string
}

export type ArticleBlockResolveInput = {
  id: string
  type: ArticleBlockType
  order: number
  data: unknown
  i18n?: Array<{ data: unknown } | null> | null
}

/** Données affichées : `article_block_i18n` pour la locale si présent, sinon `article_blocks.data`. */
export function mergeArticleBlockLocalizedData(block: {
  data: unknown
  i18n?: Array<{ data: unknown } | null> | null
}): unknown {
  const row = block.i18n?.[0]
  if (row != null && typeof row === 'object' && 'data' in row) {
    return row.data
  }
  return block.data
}

function asRecord(data: unknown): Record<string, unknown> {
  if (data && typeof data === 'object' && !Array.isArray(data)) {
    return data as Record<string, unknown>
  }
  return {}
}

const ENRICHED_BLOCK_TYPES = new Set<ArticleBlockType>([
  ArticleBlockType.MEDIA_IMAGE_CAROUSEL,
  ArticleBlockType.DOCUMENTS_LIST,
  ArticleBlockType.LOCALISATION,
  ArticleBlockType.VIDEO_BLOCK_ARTICLE,
  ArticleBlockType.STEPS_MODULE,
  ArticleBlockType.VIDEO,
  // Résout `steps[].imageMediaId` → `steps[].imageMediaUrl` (cf.
  // `enrichPublicArticleBlockData`).
  ArticleBlockType.HOW_IT_WORKS_CAROUSEL,
])

/**
 * Résolution unique pour le site (`getPublicArticle`) et l’API (`getArticleBySlug`) :
 * médias signés, enrichissement carrousel / liste docs / vidéos poster / étapes.
 */
export async function resolveArticleBlockForPublic(
  prisma: PrismaClient,
  block: ArticleBlockResolveInput,
): Promise<NormalizedArticleBlock> {
  try {
    const blockData = mergeArticleBlockLocalizedData(block)

    if (block.type === ArticleBlockType.IMAGE && (blockData as { mediaId?: string })?.mediaId) {
      try {
        const media = await prisma.media.findUnique({
          where: { id: (blockData as { mediaId: string }).mediaId },
        })
        if (media?.key) {
          try {
            const url = await getPresignedUrl(media.key, 3600)
            return { id: block.id, type: block.type, order: block.order, data: blockData, imageUrl: url }
          } catch {
            return { id: block.id, type: block.type, order: block.order, data: blockData, imageUrl: media.url }
          }
        }
        return {
          id: block.id,
          type: block.type,
          order: block.order,
          data: blockData,
          imageUrl: media?.url || '',
        }
      } catch (error) {
        console.error('Error fetching block media:', error)
        return { id: block.id, type: block.type, order: block.order, data: blockData, imageUrl: '' }
      }
    }

    if (block.type === ArticleBlockType.DOCUMENT && (blockData as { mediaId?: string })?.mediaId) {
      try {
        const media = await prisma.media.findUnique({
          where: { id: (blockData as { mediaId: string }).mediaId },
        })
        if (media) {
          let url = media.url
          if (media.key) {
            try {
              url = await getPresignedUrl(media.key, 3600)
            } catch {
              // keep
            }
          }
          return {
            id: block.id,
            type: block.type,
            order: block.order,
            data: { ...(asRecord(blockData)), url },
          }
        }
        return { id: block.id, type: block.type, order: block.order, data: blockData }
      } catch (error) {
        console.error('Error fetching document media:', error)
        return { id: block.id, type: block.type, order: block.order, data: blockData }
      }
    }

    if (ENRICHED_BLOCK_TYPES.has(block.type)) {
      const enriched = await enrichPublicArticleBlockData(prisma, block.type, asRecord(blockData))
      return { id: block.id, type: block.type, order: block.order, data: enriched }
    }

    return { id: block.id, type: block.type, order: block.order, data: blockData }
  } catch (error) {
    console.error('Error processing block:', error)
    return {
      id: block.id,
      type: block.type,
      order: block.order,
      data: mergeArticleBlockLocalizedData(block),
    }
  }
}

export async function resolveArticleBlocksForPublic(
  prisma: PrismaClient,
  blocks: ArticleBlockResolveInput[],
): Promise<NormalizedArticleBlock[]> {
  return Promise.all(blocks.map((b) => resolveArticleBlockForPublic(prisma, b)))
}
