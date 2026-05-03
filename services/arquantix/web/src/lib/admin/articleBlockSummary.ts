import type { ArticleBlockType } from '@prisma/client'

/**
 * Résumé court (1 ligne, ~80 chars) d'un bloc article, affiché dans le summary
 * pliable des cartes de blocs admin. Extrait de
 * `src/app/admin/articles/[id]/page.tsx` pour pouvoir être réutilisé par
 * d'autres écrans (admin Help, futur hub `/admin/content`).
 */
export function getBlockSummary(block: { type: ArticleBlockType; data: any }): string {
  const d = (block.data ?? {}) as Record<string, unknown>
  const truncate = (s: string, n = 80) => (s.length > n ? `${s.slice(0, n - 1)}…` : s)
  const str = (v: unknown): string => (typeof v === 'string' ? v.trim() : '')
  switch (block.type) {
    case 'HEADING':
      return truncate(str(d.text)) || '—'
    case 'PARAGRAPH':
      return truncate(str(d.text).replace(/\s+/g, ' ')) || '—'
    case 'QUOTE': {
      const t = str(d.text)
      const a = str(d.author)
      return truncate(a ? `« ${t} » — ${a}` : `« ${t} »`)
    }
    case 'BULLET_LIST':
    case 'NUMBERED_LIST': {
      const items = Array.isArray(d.items) ? (d.items as unknown[]).map(str).filter(Boolean) : []
      return items.length > 0 ? `${items.length} élément(s) — ${truncate(items[0], 50)}` : '—'
    }
    case 'IMAGE':
      return 'Bloc image obsolète'
    case 'VIDEO':
      return truncate(str(d.caption) || str(d.url)) || '—'
    case 'DOCUMENT':
      return truncate(str(d.title)) || '—'
    case 'MEDIA_IMAGE_CAROUSEL': {
      const ids = Array.isArray(d.imageMediaIds) ? d.imageMediaIds.length : 0
      return `${ids} image(s)${str(d.moduleTitle) ? ` — ${truncate(str(d.moduleTitle), 50)}` : ''}`
    }
    case 'LOCALISATION':
      return truncate(str(d.moduleTitle) || 'Carte Google Maps') || '—'
    case 'DOCUMENTS_LIST': {
      const entries = Array.isArray(d.documentEntries) ? d.documentEntries.length : 0
      return `${entries} document(s)${str(d.moduleTitle) ? ` — ${truncate(str(d.moduleTitle), 50)}` : ''}`
    }
    case 'KEY_INFORMATION': {
      const rows = Array.isArray(d.rows) ? d.rows.length : 0
      return `${rows} ligne(s)${str(d.title) ? ` — ${truncate(str(d.title), 50)}` : ''}`
    }
    case 'VIDEO_BLOCK_ARTICLE': {
      const items = Array.isArray(d.items) ? d.items.length : 0
      return `${items} vidéo(s)${str(d.title) ? ` — ${truncate(str(d.title), 50)}` : ''}`
    }
    case 'STEPS_MODULE': {
      const items = Array.isArray(d.items) ? d.items.length : 0
      return `${items} étape(s)${str(d.title) ? ` — ${truncate(str(d.title), 50)}` : ''}`
    }
    case 'HOW_IT_WORKS_CAROUSEL': {
      const steps = Array.isArray(d.steps) ? d.steps.length : 0
      return `${steps} étape(s)${str(d.title) ? ` — ${truncate(str(d.title), 50)}` : ''}`
    }
    default:
      return '—'
  }
}
