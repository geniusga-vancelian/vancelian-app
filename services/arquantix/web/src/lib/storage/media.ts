/**
 * Media helper functions for resolving media IDs to URLs and metadata
 */

import { prisma } from '@/lib/prisma'

export interface MediaInfo {
  id: string
  url: string
  alt: string | null
  width: number | null
  height: number | null
  mimeType: string
  filename: string
}

/**
 * Resolve a media ID to media info
 * Returns null if media not found or invalid
 */
export async function resolveMedia(mediaId: string | null | undefined): Promise<MediaInfo | null> {
  if (!mediaId) {
    return null
  }

  try {
    const media = await prisma.media.findUnique({
      where: { id: mediaId },
    })

    if (!media) {
      return null
    }

    return {
      id: media.id,
      url: media.url,
      alt: media.alt,
      width: media.width,
      height: media.height,
      mimeType: media.mimeType,
      filename: media.filename,
    }
  } catch (error) {
    console.error('Error resolving media:', error)
    return null
  }
}

/**
 * Extract all mediaIds from section data
 * Supports nested structures like hero.backgroundMediaId, projects[].mediaId
 */
export function extractMediaIds(data: any): string[] {
  const mediaIds: string[] = []

  function traverse(obj: any) {
    if (obj === null || obj === undefined) {
      return
    }

    if (typeof obj === 'string') {
      return
    }

    if (Array.isArray(obj)) {
      obj.forEach(traverse)
      return
    }

    if (typeof obj === 'object') {
      // Check known mediaId fields
      if (obj.mediaId && typeof obj.mediaId === 'string') {
        mediaIds.push(obj.mediaId)
      }
      if (obj.backgroundMediaId && typeof obj.backgroundMediaId === 'string') {
        mediaIds.push(obj.backgroundMediaId)
      }

      // Recursively traverse
      Object.values(obj).forEach(traverse)
    }
  }

  traverse(data)
  return mediaIds
}

/**
 * Resolve multiple media IDs (batch query)
 * Alias for resolveMediaMap for backward compatibility
 */
export async function resolveMediaBatch(
  mediaIds: (string | null | undefined)[]
): Promise<Map<string, MediaInfo>> {
  return resolveMediaMap(mediaIds)
}

/**
 * Resolve multiple media IDs to a Map (batch query)
 * More efficient than calling resolveMedia multiple times
 */
export async function resolveMediaMap(
  mediaIds: (string | null | undefined)[]
): Promise<Map<string, MediaInfo>> {
  const validIds = mediaIds.filter((id): id is string => Boolean(id))
  if (validIds.length === 0) {
    return new Map()
  }

  try {
    const media = await prisma.media.findMany({
      where: {
        id: {
          in: validIds,
        },
      },
    })

    const mediaMap = new Map<string, MediaInfo>()
    for (const m of media) {
      let finalUrl = m.url
      
      // Always generate a fresh presigned URL since the bucket is not public
      // This ensures URLs don't expire. Timeout 5s to avoid blocking page load.
      try {
        const { getPresignedUrl } = await import('./storageClient')
        finalUrl = await Promise.race([
          getPresignedUrl(m.key, 3600),
          new Promise<string>((_, reject) =>
            setTimeout(() => reject(new Error('Presigned URL timeout')), 5000)
          ),
        ])
        if (process.env.NODE_ENV === 'development') {
          console.log('[resolveMediaMap] Generated fresh presigned URL for media:', {
            id: m.id,
            key: m.key,
            url: finalUrl.substring(0, 100) + '...',
          })
        }
      } catch (error) {
        console.error('[resolveMediaMap] Failed to generate presigned URL for media:', m.id, error)
        // Fallback to stored URL if presigned URL generation fails
        if (process.env.NODE_ENV === 'development') {
          console.log('[resolveMediaMap] Using stored URL as fallback:', m.url.substring(0, 100) + '...')
        }
      }
      
      if (process.env.NODE_ENV === 'development') {
        console.log('[resolveMediaMap] Media:', m.id, 'Final URL:', finalUrl.substring(0, 100) + '...', 'Key:', m.key)
      }
      
      mediaMap.set(m.id, {
        id: m.id,
        url: finalUrl,
        alt: m.alt,
        width: m.width,
        height: m.height,
        mimeType: m.mimeType,
        filename: m.filename,
      })
    }

    return mediaMap
  } catch (error) {
    console.error('Error resolving media batch:', error)
    return new Map()
  }
}

