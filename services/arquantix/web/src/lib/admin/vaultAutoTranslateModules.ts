/**
 * Traduction allowlistée par type de module — structure JSON préservée.
 */

import { translateMarkdown } from '@/lib/translate/translateMarkdown'
import { translateText } from '@/lib/translate/translateText'
import type { TranslationOptions } from '@/lib/translate/types'

import { shouldSkipPlainString } from '@/lib/admin/vaultAutoTranslateAllowlist'

export type TranslateStats = { fieldsTranslated: number; tokensUsedApprox: number }

async function trPlain(
  s: string | undefined,
  opts: TranslationOptions,
  stats: TranslateStats,
): Promise<string | undefined> {
  if (s == null || typeof s !== 'string') return s
  if (!s.trim()) return s
  if (shouldSkipPlainString(s)) return s
  const r = await translateText(s, opts)
  stats.fieldsTranslated += 1
  stats.tokensUsedApprox += r.tokensUsed ?? 0
  return r.translated
}

async function trMd(
  s: string | undefined,
  opts: TranslationOptions,
  stats: TranslateStats,
): Promise<string | undefined> {
  if (s == null || typeof s !== 'string') return s
  if (!s.trim()) return s
  const r = await translateMarkdown(s, opts)
  stats.fieldsTranslated += 1
  stats.tokensUsedApprox += r.tokensUsed ?? 0
  return r.translated
}

async function trTags(arr: unknown, opts: TranslationOptions, stats: TranslateStats): Promise<string[]> {
  if (!Array.isArray(arr)) return []
  const out: string[] = []
  for (const x of arr) {
    if (typeof x !== 'string') continue
    if (!x.trim()) {
      out.push(x)
      continue
    }
    if (shouldSkipPlainString(x)) {
      out.push(x)
      continue
    }
    const r = await translateText(x, opts)
    stats.fieldsTranslated += 1
    stats.tokensUsedApprox += r.tokensUsed ?? 0
    out.push(r.translated)
  }
  return out
}

/**
 * Traduit uniquement les champs éditoriaux connus pour ce type de module.
 */
export async function translateModuleContent(
  moduleType: string,
  content: Record<string, unknown>,
  opts: TranslationOptions,
  stats: TranslateStats,
): Promise<Record<string, unknown>> {
  const c = { ...content }

  switch (moduleType) {
    case 'TitlePage': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (typeof c.subtitle === 'string') c.subtitle = (await trPlain(c.subtitle, opts, stats)) ?? c.subtitle
      return c
    }
    case 'TagsModule': {
      if (Array.isArray(c.tags)) c.tags = await trTags(c.tags, opts, stats)
      return c
    }
    case 'FundingModule': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (typeof c.footnote === 'string') c.footnote = (await trPlain(c.footnote, opts, stats)) ?? c.footnote
      if (Array.isArray(c.items)) {
        c.items = await Promise.all(
          c.items.map(async (row) => {
            if (row == null || typeof row !== 'object') return row
            const r = { ...(row as Record<string, unknown>) }
            if (typeof r.label === 'string') {
              r.label = (await trPlain(r.label, opts, stats)) ?? r.label
            }
            return r
          }),
        )
      }
      if (c.manual && typeof c.manual === 'object') {
        const m = { ...(c.manual as Record<string, unknown>) }
        if (typeof m.rateDisplay === 'string') {
          m.rateDisplay = (await trPlain(m.rateDisplay, opts, stats)) ?? m.rateDisplay
        }
        if (typeof m.totalDisplay === 'string') {
          m.totalDisplay = (await trPlain(m.totalDisplay, opts, stats)) ?? m.totalDisplay
        }
        c.manual = m
      }
      return c
    }
    case 'SimpleMarkdownContentModule': {
      if (typeof c.moduleTitle === 'string') {
        c.moduleTitle = (await trPlain(c.moduleTitle, opts, stats)) ?? c.moduleTitle
      }
      if (typeof c.markdown === 'string') {
        c.markdown = (await trMd(c.markdown, opts, stats)) ?? c.markdown
      }
      if (Array.isArray(c.links)) {
        c.links = await Promise.all(
          c.links.map(async (link) => {
            if (link == null || typeof link !== 'object') return link
            const l = { ...(link as Record<string, unknown>) }
            if (typeof l.label === 'string') {
              l.label = (await trPlain(l.label, opts, stats)) ?? l.label
            }
            return l
          }),
        )
      }
      return c
    }
    case 'CompetitiveAdvantagesModule': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (Array.isArray(c.rows)) {
        c.rows = await Promise.all(
          c.rows.map(async (row) => {
            if (row == null || typeof row !== 'object') return row
            const r = { ...(row as Record<string, unknown>) }
            if (typeof r.title === 'string') r.title = (await trPlain(r.title, opts, stats)) ?? r.title
            if (typeof r.description === 'string') {
              r.description = (await trPlain(r.description, opts, stats)) ?? r.description
            }
            return r
          }),
        )
      }
      return c
    }
    case 'FaqAccordionModule': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (typeof c.intro === 'string') c.intro = (await trPlain(c.intro, opts, stats)) ?? c.intro
      if (typeof c.footerLinkLabel === 'string') {
        c.footerLinkLabel = (await trPlain(c.footerLinkLabel, opts, stats)) ?? c.footerLinkLabel
      }
      if (typeof c.footerFilterLabel === 'string') {
        c.footerFilterLabel = (await trPlain(c.footerFilterLabel, opts, stats)) ?? c.footerFilterLabel
      }
      return c
    }
    case 'ContentBasDePageSansModuleBlanc': {
      if (typeof c.markdown === 'string') {
        c.markdown = (await trMd(c.markdown, opts, stats)) ?? c.markdown
      }
      return c
    }
    case 'MarktingCardLargePortrait': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      return c
    }
    case 'MarketingCardsSmallCarouselModule':
    case 'MarketingCardsSmallSlidingCarrousel_Portrait':
    case 'MarketingCardsSmallSlidingCarrousel_Paysage': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (Array.isArray(c.items)) {
        c.items = await Promise.all(
          c.items.map(async (item) => {
            if (item == null || typeof item !== 'object') return item
            const it = { ...(item as Record<string, unknown>) }
            if (typeof it.title === 'string') it.title = (await trPlain(it.title, opts, stats)) ?? it.title
            if (typeof it.description === 'string') {
              it.description = (await trPlain(it.description, opts, stats)) ?? it.description
            }
            return it
          }),
        )
      }
      return c
    }
    case 'TransactionLatest10Module':
    case 'BlogALaUne': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      return c
    }
    case 'AllocationModule': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (typeof c.introText === 'string') {
        c.introText = (await trPlain(c.introText, opts, stats)) ?? c.introText
      }
      if (Array.isArray(c.slices)) {
        c.slices = await Promise.all(
          c.slices.map(async (slice) => {
            if (slice == null || typeof slice !== 'object') return slice
            const s = { ...(slice as Record<string, unknown>) }
            if (typeof s.label === 'string') s.label = (await trPlain(s.label, opts, stats)) ?? s.label
            return s
          }),
        )
      }
      return c
    }
    case 'KeyInformationModule': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (typeof c.ctaLabel === 'string') c.ctaLabel = (await trPlain(c.ctaLabel, opts, stats)) ?? c.ctaLabel
      if (Array.isArray(c.rows)) {
        c.rows = await Promise.all(
          c.rows.map(async (row) => {
            if (row == null || typeof row !== 'object') return row
            const r = { ...(row as Record<string, unknown>) }
            if (typeof r.label === 'string') r.label = (await trPlain(r.label, opts, stats)) ?? r.label
            if (typeof r.value === 'string' && !shouldSkipPlainString(r.value)) {
              r.value = (await trPlain(r.value, opts, stats)) ?? r.value
            }
            return r
          }),
        )
      }
      return c
    }
    case 'MediaImageCarouselModule':
    case 'DocumentsListModule': {
      if (typeof c.moduleTitle === 'string') {
        c.moduleTitle = (await trPlain(c.moduleTitle, opts, stats)) ?? c.moduleTitle
      }
      if (typeof c.description === 'string') {
        c.description = (await trPlain(c.description, opts, stats)) ?? c.description
      }
      if (moduleType === 'DocumentsListModule' && typeof c.subtitle === 'string') {
        c.subtitle = (await trPlain(c.subtitle, opts, stats)) ?? c.subtitle
      }
      if (moduleType === 'DocumentsListModule' && Array.isArray(c.documentEntries)) {
        c.documentEntries = await Promise.all(
          c.documentEntries.map(async (entry) => {
            if (entry == null || typeof entry !== 'object') return entry
            const e = { ...(entry as Record<string, unknown>) }
            if (typeof e.documentName === 'string' && e.documentName.trim()) {
              e.documentName = (await trPlain(e.documentName, opts, stats)) ?? e.documentName
            }
            return e
          }),
        )
      }
      return c
    }
    case 'PerformanceChart': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      return c
    }
    case 'StepsModule': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (typeof c.subtitle === 'string') c.subtitle = (await trPlain(c.subtitle, opts, stats)) ?? c.subtitle
      if (typeof c.description === 'string') {
        c.description = (await trPlain(c.description, opts, stats)) ?? c.description
      }
      if (typeof c.rightLabel === 'string') {
        c.rightLabel = (await trPlain(c.rightLabel, opts, stats)) ?? c.rightLabel
      }
      if (Array.isArray(c.items)) {
        c.items = await Promise.all(
          c.items.map(async (item) => {
            if (item == null || typeof item !== 'object') return item
            const it = { ...(item as Record<string, unknown>) }
            if (typeof it.dayLabel === 'string') {
              it.dayLabel = (await trPlain(it.dayLabel, opts, stats)) ?? it.dayLabel
            }
            if (typeof it.date === 'string') it.date = (await trPlain(it.date, opts, stats)) ?? it.date
            if (typeof it.title === 'string') it.title = (await trPlain(it.title, opts, stats)) ?? it.title
            if (typeof it.description === 'string') {
              it.description = (await trPlain(it.description, opts, stats)) ?? it.description
            }
            if (Array.isArray(it.tags)) {
              it.tags = await trTags(it.tags, opts, stats)
            }
            return it
          }),
        )
      }
      return c
    }
    case 'VideoBlockArticleModule': {
      if (typeof c.title === 'string') c.title = (await trPlain(c.title, opts, stats)) ?? c.title
      if (Array.isArray(c.items)) {
        c.items = await Promise.all(
          c.items.map(async (item) => {
            if (item == null || typeof item !== 'object') return item
            const it = { ...(item as Record<string, unknown>) }
            if (typeof it.title === 'string') it.title = (await trPlain(it.title, opts, stats)) ?? it.title
            if (typeof it.date === 'string') it.date = (await trPlain(it.date, opts, stats)) ?? it.date
            return it
          }),
        )
      }
      return c
    }
    case 'LocalisationModule': {
      if (typeof c.moduleTitle === 'string') {
        c.moduleTitle = (await trPlain(c.moduleTitle, opts, stats)) ?? c.moduleTitle
      }
      if (typeof c.description === 'string') {
        c.description = (await trPlain(c.description, opts, stats)) ?? c.description
      }
      return c
    }
    case 'VirtualVisualizationModule': {
      if (typeof c.moduleTitle === 'string') {
        c.moduleTitle = (await trPlain(c.moduleTitle, opts, stats)) ?? c.moduleTitle
      }
      if (typeof c.description === 'string') {
        c.description = (await trPlain(c.description, opts, stats)) ?? c.description
      }
      return c
    }
    default:
      return c
  }
}
