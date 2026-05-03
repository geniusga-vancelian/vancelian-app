/**
 * Media helper functions for resolving media IDs to URLs and metadata
 */

import { prisma } from '@/lib/prisma'
import { isR2Configured } from '@/lib/storage/r2Env'

/** URL same-origin pour charger un fichier depuis R2 via le serveur (bucket privé). */
export function siteMediaProxyPath(mediaId: string): string {
  return `/api/site/media/${mediaId}`
}

/**
 * Remplace les `*MediaUrl` / `mediaUrl` par le proxy site pour chaque `*MediaId` / `mediaId`
 * présent dans l’arbre (récursif). Utile pour l’iframe d’aperçu admin : les URLs présignées
 * R2 peuvent être refusées (referrer, HEAD/GET, politique bucket) alors que le proxy marche.
 */
export function rewriteMediaUrlsToSiteProxyDeep(data: unknown): unknown {
  if (data === null || data === undefined) {
    return data
  }
  if (Array.isArray(data)) {
    return data.map(rewriteMediaUrlsToSiteProxyDeep)
  }
  if (typeof data !== 'object') {
    return data
  }
  const src = data as Record<string, unknown>
  const out: Record<string, unknown> = {}
  for (const [k, v] of Object.entries(src)) {
    out[k] = rewriteMediaUrlsToSiteProxyDeep(v) as never
  }
  const bg = out.backgroundMediaId
  if (typeof bg === 'string' && bg.trim()) {
    out.backgroundMediaUrl = siteMediaProxyPath(bg.trim())
  }
  const img = out.imageMediaId
  if (typeof img === 'string' && img.trim()) {
    out.imageMediaUrl = siteMediaProxyPath(img.trim())
  }
  const mid = out.mediaId
  if (typeof mid === 'string' && mid.trim()) {
    out.mediaUrl = siteMediaProxyPath(mid.trim())
  }
  const av = out.avatarMediaId
  if (typeof av === 'string' && av.trim()) {
    out.avatarMediaUrl = siteMediaProxyPath(av.trim())
  }
  return out
}

/**
 * URL utilisable par le navigateur : présignature R2, sinon proxy `/api/site/media/[id]`
 * (évite de retomber sur `media.url` « public » qui renvoie 403 si le bucket est privé).
 */
async function resolvePublicMediaFileUrl(m: {
  id: string
  key: string
  url: string
}): Promise<string> {
  if (!isR2Configured()) {
    return m.url
  }
  try {
    const { getPresignedUrl } = await import('./storageClient')
    return await Promise.race([
      getPresignedUrl(m.key, 3600),
      new Promise<string>((_, reject) =>
        setTimeout(() => reject(new Error('Presigned URL timeout')), 5000),
      ),
    ])
  } catch (error) {
    console.error('[resolvePublicMediaFileUrl] presign failed, using site proxy:', m.id, error)
    return siteMediaProxyPath(m.id)
  }
}

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

    const url = await resolvePublicMediaFileUrl(media)

    return {
      id: media.id,
      url,
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
      if (obj.imageMediaId && typeof obj.imageMediaId === 'string') {
        mediaIds.push(obj.imageMediaId)
      }
      if (obj.avatarMediaId && typeof obj.avatarMediaId === 'string') {
        mediaIds.push(obj.avatarMediaId)
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
      const finalUrl = await resolvePublicMediaFileUrl(m)

      if (process.env.NODE_ENV === 'development') {
        console.log('[resolveMediaMap] Media:', m.id, 'Final URL:', finalUrl.substring(0, 120) + '...', 'Key:', m.key)
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

