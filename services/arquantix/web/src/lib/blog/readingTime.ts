import { ArticleBlockType } from '@prisma/client'

/**
 * Calculate reading time in minutes from article blocks
 * Based on average reading speed of 220 words per minute
 */
export function calculateReadingTime(
  blocks: Array<{ type: string; data: unknown }>
): number {
  let totalWords = 0

  for (const block of blocks) {
    switch (block.type as ArticleBlockType) {
      case ArticleBlockType.HEADING:
        const headingText = (block.data as any).text || ''
        totalWords += headingText.split(/\s+/).filter((w: string) => w.length > 0).length
        break

      case ArticleBlockType.PARAGRAPH:
        const paragraphText = (block.data as any).text || ''
        // Strip markdown syntax (simple regex, safe for common patterns)
        const cleanText = paragraphText
          .replace(/#{1,6}\s+/g, '') // Headers
          .replace(/\*\*([^*]+)\*\*/g, '$1') // Bold
          .replace(/\*([^*]+)\*/g, '$1') // Italic
          .replace(/\[([^\]]+)\]\([^\)]+\)/g, '$1') // Links
          .replace(/`([^`]+)`/g, '$1') // Inline code
          .replace(/```[\s\S]*?```/g, '') // Code blocks
          .replace(/^\s*[-*+]\s+/gm, '') // List markers
          .replace(/^\s*\d+\.\s+/gm, '') // Numbered list markers
        totalWords += cleanText.split(/\s+/).filter((w: string) => w.length > 0).length
        break

      case ArticleBlockType.QUOTE:
        const quoteText = (block.data as any).text || ''
        totalWords += quoteText.split(/\s+/).filter((w: string) => w.length > 0).length
        break

      case ArticleBlockType.BULLET_LIST:
      case ArticleBlockType.NUMBERED_LIST: {
        const items = (block.data as { items?: unknown }).items || []
        if (Array.isArray(items)) {
          for (const item of items) {
            if (typeof item === 'string') {
              totalWords += item.split(/\s+/).filter((w: string) => w.length > 0).length
            }
          }
        }
        break
      }

      case ArticleBlockType.DOCUMENT: {
        const t = (block.data as { title?: string }).title || ''
        totalWords += t.split(/\s+/).filter((w: string) => w.length > 0).length
        break
      }

      case ArticleBlockType.IMAGE: {
        const cap = (block.data as { caption?: string }).caption || ''
        totalWords += cap.split(/\s+/).filter((w: string) => w.length > 0).length
        break
      }

      case ArticleBlockType.VIDEO: {
        const cap = (block.data as { caption?: string }).caption || ''
        totalWords += cap.split(/\s+/).filter((w: string) => w.length > 0).length
        const url = String((block.data as { url?: string }).url || '').trim()
        if (url.length > 0) totalWords += 15
        break
      }

      case ArticleBlockType.MEDIA_IMAGE_CAROUSEL:
      case ArticleBlockType.LOCALISATION:
      case ArticleBlockType.DOCUMENTS_LIST: {
        const d = (block.data || {}) as Record<string, unknown>
        const t0 = typeof d.subtitle === 'string' ? d.subtitle : ''
        const t1 = typeof d.moduleTitle === 'string' ? d.moduleTitle : ''
        const t2 = typeof d.description === 'string' ? d.description : ''
        totalWords += (t0 + ' ' + t1 + ' ' + t2)
          .split(/\s+/)
          .filter((w) => w.length > 0).length
        break
      }

      case ArticleBlockType.KEY_INFORMATION: {
        const d = (block.data || {}) as Record<string, unknown>
        const t0 = typeof d.title === 'string' ? d.title : ''
        const ctaL = typeof d.ctaLabel === 'string' ? d.ctaLabel : ''
        totalWords += (t0 + ' ' + ctaL).split(/\s+/).filter((w) => w.length > 0).length
        const rows = Array.isArray(d.rows) ? d.rows : []
        for (const raw of rows) {
          if (raw == null || typeof raw !== 'object' || Array.isArray(raw)) continue
          const r = raw as Record<string, unknown>
          const a = typeof r.label === 'string' ? r.label : ''
          const b = typeof r.value === 'string' ? r.value : ''
          totalWords += (a + ' ' + b).split(/\s+/).filter((w) => w.length > 0).length
        }
        break
      }

      case ArticleBlockType.VIDEO_BLOCK_ARTICLE: {
        const d = (block.data || {}) as Record<string, unknown>
        const t0 = typeof d.title === 'string' ? d.title : ''
        totalWords += t0.split(/\s+/).filter((w) => w.length > 0).length
        const items = Array.isArray(d.items) ? d.items : []
        for (const it of items) {
          if (it == null || typeof it !== 'object' || Array.isArray(it)) continue
          const o = it as Record<string, unknown>
          const ti = typeof o.title === 'string' ? o.title : ''
          const da = typeof o.date === 'string' ? o.date : ''
          totalWords += (ti + ' ' + da).split(/\s+/).filter((w) => w.length > 0).length
        }
        break
      }

      case ArticleBlockType.STEPS_MODULE: {
        const d = (block.data || {}) as Record<string, unknown>
        const t0 = typeof d.title === 'string' ? d.title : ''
        const t1 = typeof d.subtitle === 'string' ? d.subtitle : ''
        const t1b = typeof d.description === 'string' ? d.description : ''
        const t2 = typeof d.rightLabel === 'string' ? d.rightLabel : ''
        totalWords += (t0 + ' ' + t1 + ' ' + t1b + ' ' + t2)
          .split(/\s+/)
          .filter((w) => w.length > 0).length
        const items = Array.isArray(d.items) ? d.items : []
        for (const it of items) {
          if (it == null || typeof it !== 'object' || Array.isArray(it)) continue
          const o = it as Record<string, unknown>
          const parts = [
            typeof o.title === 'string' ? o.title : '',
            typeof o.date === 'string' ? o.date : '',
            typeof o.description === 'string' ? o.description : '',
            typeof o.dayLabel === 'string' ? o.dayLabel : '',
          ]
          totalWords += parts.join(' ').split(/\s+/).filter((w) => w.length > 0).length
        }
        break
      }

      case ArticleBlockType.HOW_IT_WORKS_CAROUSEL: {
        const d = (block.data || {}) as Record<string, unknown>
        const headerParts = [
          typeof d.label === 'string' ? d.label : '',
          typeof d.title === 'string' ? d.title : '',
          typeof d.subtitle === 'string' ? d.subtitle : '',
          typeof d.primaryCtaText === 'string' ? d.primaryCtaText : '',
          typeof d.secondaryCtaText === 'string' ? d.secondaryCtaText : '',
        ]
        totalWords += headerParts.join(' ').split(/\s+/).filter((w) => w.length > 0).length
        const steps = Array.isArray(d.steps) ? d.steps : []
        for (const it of steps) {
          if (it == null || typeof it !== 'object' || Array.isArray(it)) continue
          const o = it as Record<string, unknown>
          const parts = [
            typeof o.number === 'string' ? o.number : '',
            typeof o.title === 'string' ? o.title : '',
            typeof o.description === 'string' ? o.description : '',
            typeof o.stepButtonLabel === 'string' ? o.stepButtonLabel : '',
          ]
          totalWords += parts.join(' ').split(/\s+/).filter((w) => w.length > 0).length
        }
        break
      }

      default:
        break
    }
  }

  // Calculate minutes (220 words per minute average)
  const minutes = Math.ceil(totalWords / 220)
  return Math.max(1, minutes) // Minimum 1 minute
}


