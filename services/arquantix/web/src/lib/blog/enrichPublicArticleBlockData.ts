import { ArticleBlockType } from '@prisma/client'
import type { PrismaClient } from '@prisma/client'

import { resolveMediaUrl } from '@/lib/catalog/packagedCatalogHelpers'
import { resolveVideoThumbnailUrl } from '@/lib/blog/videoThumbnail'

function formatDocumentListDateLabel(d: Date): string {
  const s = d.toLocaleString('sv-SE', { timeZone: 'Europe/Paris' })
  return s.length >= 16 ? s.slice(0, 16) : s
}

/**
 * Taille fichier formatée FR (« 3,4 Mo », « 456 Ko », « 12 o »).
 * Utilisé par les modules `DOCUMENTS_LIST` (web + mobile Flutter) — base 1024.
 */
function formatDocumentSizeLabelFr(bytes: number | null | undefined): string {
  if (typeof bytes !== 'number' || !Number.isFinite(bytes) || bytes <= 0) return ''
  const KB = 1024
  const MB = KB * 1024
  const GB = MB * 1024
  if (bytes < KB) return `${bytes} o`
  if (bytes < MB) return `${(bytes / KB).toFixed(1).replace('.', ',')} Ko`
  if (bytes < GB) return `${(bytes / MB).toFixed(1).replace('.', ',')} Mo`
  return `${(bytes / GB).toFixed(2).replace('.', ',')} Go`
}

/**
 * Étiquette format dérivée du `mimeType` (ou, à défaut, de l'extension du
 * filename) — sortie courte et lisible : « PDF », « DOCX », « ZIP », « MP4 »…
 */
function deriveDocumentFormatLabel(mimeType: string | null | undefined, filename: string): string {
  const m = (mimeType ?? '').toLowerCase()
  if (m.includes('pdf')) return 'PDF'
  if (m.includes('msword') || m.includes('wordprocessingml')) return 'DOCX'
  if (m.includes('spreadsheetml') || m.includes('ms-excel')) return 'XLSX'
  if (m.includes('presentationml') || m.includes('ms-powerpoint')) return 'PPTX'
  if (m.includes('zip')) return 'ZIP'
  if (m.includes('csv')) return 'CSV'
  if (m.startsWith('image/') || m.startsWith('video/') || m.startsWith('audio/')) {
    const sub = m.split('/')[1] ?? ''
    if (sub) return sub.toUpperCase()
  }
  const dot = filename.lastIndexOf('.')
  if (dot >= 0 && dot < filename.length - 1) {
    return filename.slice(dot + 1).toUpperCase()
  }
  return ''
}

function parseDocumentEntries(c: Record<string, unknown>): Array<{ mediaId: string; documentName: string }> {
  if (Array.isArray(c.documentEntries)) {
    const out: Array<{ mediaId: string; documentName: string }> = []
    for (const x of c.documentEntries) {
      if (x != null && typeof x === 'object' && !Array.isArray(x)) {
        const o = x as Record<string, unknown>
        const mediaId = typeof o.mediaId === 'string' ? o.mediaId.trim() : ''
        if (!mediaId) continue
        const documentName = typeof o.documentName === 'string' ? o.documentName : ''
        out.push({ mediaId, documentName })
      }
    }
    return out
  }
  const rawIds = c.documentMediaIds
  if (!Array.isArray(rawIds)) return []
  return rawIds
    .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    .map((mediaId) => ({ mediaId, documentName: '' }))
}

/**
 * Résout URLs et libellés pour les blocs article alignés sur les modules Vault Builder
 * (même JSON source : `imageMediaIds`, `documentEntries`, etc.).
 */
export async function enrichPublicArticleBlockData(
  prisma: PrismaClient,
  type: ArticleBlockType,
  data: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  const out = { ...data }
  switch (type) {
    case ArticleBlockType.MEDIA_IMAGE_CAROUSEL: {
      const rawIds = Array.isArray(out.imageMediaIds) ? out.imageMediaIds : []
      const imageMediaIds = rawIds.filter(
        (x): x is string => typeof x === 'string' && x.trim().length > 0,
      )
      const carouselItems: Array<{ mediaId: string; url: string; alt: string | null }> = []
      for (const mediaId of imageMediaIds) {
        const url = await resolveMediaUrl(prisma, mediaId)
        if (!url) continue
        const row = await prisma.media.findUnique({
          where: { id: mediaId },
          select: { alt: true },
        })
        carouselItems.push({ mediaId, url, alt: row?.alt ?? null })
      }
      return { ...out, imageMediaIds, carouselItems }
    }
    case ArticleBlockType.DOCUMENTS_LIST: {
      const entries = parseDocumentEntries(out)
      const documentItems: Array<{
        mediaId: string
        downloadUrl: string
        displayName: string
        dateLabel: string
        sizeBytes: number
        sizeLabel: string
        mimeType: string
        formatLabel: string
      }> = []
      for (const { mediaId, documentName } of entries) {
        const downloadUrl = await resolveMediaUrl(prisma, mediaId)
        if (!downloadUrl) continue
        const row = await prisma.media.findUnique({
          where: { id: mediaId },
          select: { filename: true, createdAt: true, size: true, mimeType: true },
        })
        if (!row) continue
        const custom = documentName.trim()
        const sizeBytes = typeof row.size === 'number' && Number.isFinite(row.size) ? row.size : 0
        const mimeType = typeof row.mimeType === 'string' ? row.mimeType : ''
        documentItems.push({
          mediaId,
          downloadUrl,
          displayName: custom.length > 0 ? custom : row.filename,
          dateLabel: formatDocumentListDateLabel(row.createdAt),
          sizeBytes,
          sizeLabel: formatDocumentSizeLabelFr(sizeBytes),
          mimeType,
          formatLabel: deriveDocumentFormatLabel(mimeType, row.filename),
        })
      }
      return { ...out, documentItems }
    }
    case ArticleBlockType.LOCALISATION:
      return out
    case ArticleBlockType.VIDEO_BLOCK_ARTICLE: {
      const raw = Array.isArray(out.items) ? out.items : []
      const items = await Promise.all(
        raw.map(async (it) => {
          const row = it != null && typeof it === 'object' && !Array.isArray(it) ? (it as Record<string, unknown>) : {}
          const posterMediaId =
            typeof row.posterMediaId === 'string' && row.posterMediaId.trim().length > 0
              ? row.posterMediaId.trim()
              : null
          let posterImageUrl = typeof row.posterImageUrl === 'string' ? row.posterImageUrl : ''
          if (posterMediaId) {
            const url = await resolveMediaUrl(prisma, posterMediaId)
            if (url) posterImageUrl = url
          }
          return { ...row, posterImageUrl, ...(posterMediaId ? { posterMediaId } : {}) }
        }),
      )
      return { ...out, items }
    }
    case ArticleBlockType.KEY_INFORMATION:
      return out
    case ArticleBlockType.STEPS_MODULE:
      return out
    case ArticleBlockType.HOW_IT_WORKS_CAROUSEL: {
      // Calque de la résolution médias de la section CMS `how_it_works`
      // (cf. `injectMediaUrls` dans `src/lib/cms/content.ts`) : pour chaque
      // étape, si `imageMediaId` est défini, on résout l'URL signée et on
      // l'injecte dans `imageMediaUrl` (consommé tel quel par
      // `SectionHowItWorksCms` côté web et mappé sur `imageUrl` côté mobile).
      const rawSteps = Array.isArray(out.steps) ? out.steps : []
      const steps = await Promise.all(
        rawSteps.map(async (raw) => {
          if (raw == null || typeof raw !== 'object' || Array.isArray(raw)) return raw
          const row = raw as Record<string, unknown>
          const imageMediaId =
            typeof row.imageMediaId === 'string' && row.imageMediaId.trim().length > 0
              ? row.imageMediaId.trim()
              : null
          if (!imageMediaId) return row
          const url = await resolveMediaUrl(prisma, imageMediaId)
          if (!url) return row
          const media = await prisma.media.findUnique({
            where: { id: imageMediaId },
            select: { alt: true },
          })
          return {
            ...row,
            imageMediaId,
            imageMediaUrl: url,
            ...(media?.alt ? { imageMediaAlt: media.alt } : {}),
          }
        }),
      )
      return { ...out, steps }
    }
    case ArticleBlockType.VIDEO: {
      // Préserver un `thumbnailUrl` éventuellement fourni par l'admin (override
      // manuel). Sinon, tenter la résolution auto YouTube/Vimeo depuis `data.url`.
      const adminThumb = typeof out.thumbnailUrl === 'string' ? out.thumbnailUrl.trim() : ''
      if (adminThumb.length > 0) return out
      const url = typeof out.url === 'string' ? out.url : ''
      const auto = await resolveVideoThumbnailUrl(url)
      return auto ? { ...out, thumbnailUrl: auto } : out
    }
    default:
      return out
  }
}
