import { siteMediaProxyPath } from '@/lib/storage/media'

/** Détecte un média vidéo (mime CMS, nom de fichier ou extension URL). */
export function isVideoMedia(
  mime?: unknown,
  filename?: unknown,
  url?: unknown,
): boolean {
  if (typeof mime === 'string' && mime.startsWith('video/')) return true
  if (typeof filename === 'string' && /\.(mp4|webm|mov|m4v)$/i.test(filename.trim())) {
    return true
  }
  if (typeof url === 'string' && /\.(mp4|webm|mov|m4v)(\?|$)/i.test(url.trim())) {
    return true
  }
  return false
}

export type SplitCmsMediaResult = {
  imageUrl?: string
  videoUrl?: string
}

/**
 * Sépare URL image / vidéo pour les champs `backgroundMedia*` CMS.
 * Les vidéos passent par le proxy same-origin (`/api/site/media/[id]`).
 */
export function splitCmsBackgroundMedia(data: {
  backgroundMediaUrl?: unknown
  backgroundMediaMimeType?: unknown
  backgroundMediaFilename?: unknown
  backgroundMediaId?: unknown
}): SplitCmsMediaResult {
  const url =
    typeof data.backgroundMediaUrl === 'string' ? data.backgroundMediaUrl.trim() : ''
  if (!url) return {}

  const mediaId =
    typeof data.backgroundMediaId === 'string' ? data.backgroundMediaId.trim() : ''
  const video = isVideoMedia(
    data.backgroundMediaMimeType,
    data.backgroundMediaFilename,
    url,
  )

  if (video) {
    return { videoUrl: mediaId ? siteMediaProxyPath(mediaId) : url }
  }
  return { imageUrl: url }
}

/** Variante pour `imageMediaId` / `imageMediaUrl`. */
export function splitCmsInlineMedia(data: {
  imageMediaUrl?: unknown
  imageMediaMimeType?: unknown
  imageMediaFilename?: unknown
  imageMediaId?: unknown
}): SplitCmsMediaResult {
  const url = typeof data.imageMediaUrl === 'string' ? data.imageMediaUrl.trim() : ''
  if (!url) return {}

  const mediaId = typeof data.imageMediaId === 'string' ? data.imageMediaId.trim() : ''
  const video = isVideoMedia(data.imageMediaMimeType, data.imageMediaFilename, url)

  if (video) {
    return { videoUrl: mediaId ? siteMediaProxyPath(mediaId) : url }
  }
  return { imageUrl: url }
}
