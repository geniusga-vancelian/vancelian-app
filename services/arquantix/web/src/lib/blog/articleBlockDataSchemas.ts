import { ArticleBlockType } from '@prisma/client'
import type { ZodIssue } from 'zod'
import { z } from 'zod'

function mustBeObject(data: unknown): data is Record<string, unknown> {
  return data !== null && typeof data === 'object' && !Array.isArray(data)
}

function issue(message: string, path: (string | number)[] = []): ZodIssue {
  return { code: z.ZodIssueCode.custom, message, path }
}

/**
 * Validation structurelle des `data` JSON (admin POST/PUT blocs).
 * Tolère champs vides (workflow « ajouter puis remplir ») ; rejette types incorrects.
 */
export function safeParseArticleBlockData(
  type: ArticleBlockType,
  data: unknown,
): { success: true; data: Record<string, unknown> } | { success: false; issues: ZodIssue[] } {
  if (!mustBeObject(data)) {
    return { success: false, issues: [issue('Le corps du bloc doit être un objet JSON')] }
  }
  const d = data
  const issues: ZodIssue[] = []

  const str = (key: string) => {
    if (d[key] !== undefined && typeof d[key] !== 'string') {
      issues.push(issue(`« ${key} » doit être une chaîne`, [key]))
    }
  }
  const strArray = (key: string) => {
    if (d[key] === undefined) return
    const v = d[key]
    if (!Array.isArray(v) || !(v as unknown[]).every((x) => typeof x === 'string')) {
      issues.push(issue(`« ${key} » doit être un tableau de chaînes`, [key]))
    }
  }

  switch (type) {
    case ArticleBlockType.HEADING:
    case ArticleBlockType.PARAGRAPH:
      str('text')
      break
    case ArticleBlockType.QUOTE:
      str('text')
      str('author')
      break
    case ArticleBlockType.BULLET_LIST:
    case ArticleBlockType.NUMBERED_LIST:
      strArray('items')
      break
    case ArticleBlockType.VIDEO:
      str('url')
      str('caption')
      break
    case ArticleBlockType.DOCUMENT:
      str('mediaId')
      str('title')
      break
    case ArticleBlockType.IMAGE:
      str('mediaId')
      str('caption')
      break
    case ArticleBlockType.MEDIA_IMAGE_CAROUSEL:
      strArray('imageMediaIds')
      str('moduleTitle')
      str('description')
      break
    case ArticleBlockType.LOCALISATION:
      str('moduleTitle')
      str('description')
      str('embedUrl')
      break
    case ArticleBlockType.DOCUMENTS_LIST:
      str('subtitle')
      str('moduleTitle')
      str('description')
      strArray('documentMediaIds')
      if (d.documentEntries !== undefined && !Array.isArray(d.documentEntries)) {
        issues.push(issue('« documentEntries » doit être un tableau', ['documentEntries']))
      }
      break
    case ArticleBlockType.KEY_INFORMATION:
      str('title')
      str('ctaLabel')
      str('ctaHref')
      if (d.rows !== undefined && !Array.isArray(d.rows)) {
        issues.push(issue('« rows » doit être un tableau', ['rows']))
      }
      break
    case ArticleBlockType.VIDEO_BLOCK_ARTICLE:
      str('title')
      if (d.items !== undefined && !Array.isArray(d.items)) {
        issues.push(issue('« items » doit être un tableau', ['items']))
      }
      break
    case ArticleBlockType.STEPS_MODULE:
      for (const k of ['title', 'subtitle', 'description', 'rightLabel'] as const) {
        str(k)
      }
      if (d.items !== undefined && !Array.isArray(d.items)) {
        issues.push(issue('« items » doit être un tableau', ['items']))
      }
      break
    case ArticleBlockType.HOW_IT_WORKS_CAROUSEL:
      // Calque de la section CMS `how_it_works` (cf. `howItWorksSchema` dans
      // `src/lib/sections/library.ts`) — même JSON pour pouvoir réutiliser
      // `SectionHowItWorksCms` côté rendu web et `HowItWorksCarousel` côté
      // mobile sans transformation. Tous les champs sont optionnels (workflow
      // « ajouter puis remplir ») ; on contrôle uniquement les types.
      for (const k of [
        'label',
        'title',
        'subtitle',
        'primaryCtaText',
        'primaryCtaHref',
        'secondaryCtaText',
        'secondaryCtaHref',
      ] as const) {
        str(k)
      }
      if (d.hideStepNumbering !== undefined && typeof d.hideStepNumbering !== 'boolean') {
        issues.push(issue('« hideStepNumbering » doit être un booléen', ['hideStepNumbering']))
      }
      if (d.surface !== undefined && d.surface !== 'light' && d.surface !== 'dark') {
        issues.push(issue('« surface » doit valoir "light" ou "dark"', ['surface']))
      }
      if (d.steps !== undefined && !Array.isArray(d.steps)) {
        issues.push(issue('« steps » doit être un tableau', ['steps']))
      }
      break
    default:
      break
  }

  if (issues.length > 0) {
    return { success: false, issues }
  }
  return { success: true, data: d }
}
