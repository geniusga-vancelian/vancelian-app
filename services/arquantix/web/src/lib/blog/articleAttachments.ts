import type { PrismaClient } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'

/** Parse `articles.gallery_media_ids` (JSON array ou string JSON legacy). */
export function parseArticleGalleryMediaIds(raw: unknown): string[] {
  if (!raw) return []
  if (Array.isArray(raw)) {
    return raw.filter((x): x is string => typeof x === 'string' && x.length > 0)
  }
  if (typeof raw === 'string') {
    try {
      const parsed = JSON.parse(raw)
      return Array.isArray(parsed)
        ? parsed.filter((x: unknown): x is string => typeof x === 'string' && x.length > 0)
        : []
    } catch {
      return []
    }
  }
  return []
}

export async function resolveGalleryUrlsForMediaIds(
  prisma: PrismaClient,
  mediaIds: string[],
): Promise<string[]> {
  const urls: string[] = []
  for (const mediaId of mediaIds) {
    if (!mediaId) continue
    try {
      const media = await prisma.media.findUnique({ where: { id: mediaId } })
      if (media) {
        let url = media.url
        if (media.key) {
          try {
            url = await getPresignedUrl(media.key, 3600)
          } catch {
            // keep url
          }
        }
        urls.push(url)
      }
    } catch (error) {
      console.error('Error fetching gallery media:', error)
    }
  }
  return urls
}

export type ArticleDocumentWithUrl = {
  mediaId?: string
  title?: string
  url: string | null
  [k: string]: unknown
}

/** Résout les URLs des pièces jointes `articles.documents` (JSON). */
export async function resolveArticleDocumentsWithUrls(
  prisma: PrismaClient,
  documentsRaw: unknown,
): Promise<ArticleDocumentWithUrl[]> {
  const documents = Array.isArray(documentsRaw) ? documentsRaw : []
  return Promise.all(
    documents.map(async (doc: unknown) => {
      const d = doc as { mediaId?: string; title?: string; [k: string]: unknown }
      if (!d || !d.mediaId) {
        return { ...d, url: null as string | null }
      }
      try {
        const media = await prisma.media.findUnique({
          where: { id: d.mediaId as string },
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
          return { ...d, url }
        }
        return { ...d, url: null }
      } catch (error) {
        console.error('Error fetching document media:', error)
        return { ...d, url: null }
      }
    }),
  )
}
