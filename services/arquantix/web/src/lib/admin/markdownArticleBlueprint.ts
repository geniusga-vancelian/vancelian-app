import matter from 'gray-matter'
import { ArticleBlockType } from '@prisma/client'
import { isValidLocale, type Locale } from '@/config/locales'
import { isValidSlug } from '@/lib/utils/slugify'

export type ImportWarningCode =
  | 'YAML_INVALID'
  | 'BODY_EMPTY'
  | 'LOCALE_MISMATCH'
  | 'H1_SKIPPED'
  | 'STANDFIRST_LINE_SKIPPED'
  | 'IMAGE_LINE_SKIPPED'
  | 'HERO_IMAGE_IGNORED'
  | 'TAG_UNKNOWN'
  | 'SLUG_INVALID'
  | 'STATUS_DRAFT_KEPT'
  | 'KEY_INFORMATION_FROM_FRONTMATTER'
  | 'SOURCES_FRONTMATTER_ONLY'
  | 'BLOCKS_WILL_REPLACE'

export type ImportWarning = {
  code: ImportWarningCode
  messageFr: string
  blockIndex?: number
  blockType?: string
}

export type BlueprintBlock = {
  type: ArticleBlockType
  data: Record<string, unknown>
}

export type ArticleSeoJson = {
  focus_keywords?: string[]
  og_title?: string
  og_description?: string
  named_entities?: string[]
  key_facts?: string[]
  sources?: string[]
  reading_time?: string
}

export type ArticleBlueprintMetadata = {
  slug?: string
  title: string
  standfirst: string
  locale: Locale
  status: 'DRAFT' | 'PUBLISHED'
  categorySlugs: string[]
  authorName?: string
  metaTitle?: string | null
  metaDescription?: string | null
  seoJson: ArticleSeoJson
  lastUpdatedHint?: string
}

export type ArticleBlueprintResult = {
  metadata: ArticleBlueprintMetadata
  blocks: BlueprintBlock[]
  warnings: ImportWarning[]
}

const SECTION_LEARN_MORE = new Set([
  'learn more',
  'en savoir plus',
  'read more',
  'aller plus loin',
])

const SECTION_SOURCES = new Set(['sources', 'references', 'bibliography', 'source'])

function normalizeHeadingTitle(raw: string): string {
  return raw
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function stripHeadingMarks(line: string): string {
  return line.replace(/^#{1,6}\s+/, '').trim()
}

function isBulletLine(line: string): boolean {
  return /^\s*[-*+]\s+/.test(line)
}

function isNumberedLine(line: string): boolean {
  return /^\s*\d+\.\s+/.test(line)
}

function bulletContent(line: string): string {
  return line.replace(/^\s*[-*+]\s+/, '').trim()
}

function numberedContent(line: string): string {
  return line.replace(/^\s*\d+\.\s+/, '').trim()
}

function isQuoteLine(line: string): boolean {
  return /^\s*>\s?/.test(line)
}

function quoteContent(line: string): string {
  return line.replace(/^\s*>\s?/, '').trim()
}

function isImageLine(line: string): boolean {
  return /^\s*!\[[^\]]*\]\([^)]+\)\s*$/.test(line.trim())
}

function isVideoUrl(line: string): string | null {
  const t = line.trim()
  const md = t.match(/^\[([^\]]*)\]\((https?:\/\/[^)]+)\)\s*$/)
  const url = md ? md[2] : t
  if (!/^https?:\/\//i.test(url)) return null
  if (/youtube\.com|youtu\.be|vimeo\.com/i.test(url)) return url
  return null
}

function isPdfLine(line: string): boolean {
  const t = line.trim()
  if (/\.pdf(\?|#|$)/i.test(t)) return true
  const md = t.match(/\[([^\]]*)\]\(([^)]+)\)/)
  return md ? /\.pdf(\?|#|$)/i.test(md[2]) : false
}

function parseKeyFactRow(entry: string): { label: string; value: string } {
  const t = entry.trim()
  const colon = t.indexOf(': ')
  if (colon > 0 && colon < 80) {
    return { label: t.slice(0, colon).trim(), value: t.slice(colon + 2).trim() }
  }
  return { label: '', value: t }
}

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return []
  return v.filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
}

function buildSeoJson(fm: Record<string, unknown>, seo: Record<string, unknown> | undefined): ArticleSeoJson {
  const out: ArticleSeoJson = {}
  if (typeof fm.reading_time === 'string' && fm.reading_time.trim()) {
    out.reading_time = fm.reading_time.trim()
  } else if (typeof fm.reading_time === 'number') {
    out.reading_time = `${fm.reading_time} min`
  }
  const sources = asStringArray(fm.sources)
  if (sources.length) out.sources = sources

  if (!seo || typeof seo !== 'object') return out

  const fk = asStringArray(seo.focus_keywords)
  if (fk.length) out.focus_keywords = fk
  if (typeof seo.og_title === 'string' && seo.og_title.trim()) out.og_title = seo.og_title.trim()
  if (typeof seo.og_description === 'string' && seo.og_description.trim()) {
    out.og_description = seo.og_description.trim()
  }
  const ne = asStringArray(seo.named_entities)
  if (ne.length) out.named_entities = ne
  const kf = asStringArray(seo.key_facts)
  if (kf.length) out.key_facts = kf

  return out
}

function keyInformationBlockFromFacts(
  facts: string[],
  title = 'Informations clés',
): BlueprintBlock {
  const rows = facts.map(parseKeyFactRow).filter((r) => r.label || r.value)
  if (rows.length === 0) {
    rows.push({ label: '', value: '' })
  }
  return {
    type: ArticleBlockType.KEY_INFORMATION,
    data: {
      title,
      ctaLabel: '',
      ctaHref: '',
      rows,
    },
  }
}

function parseFrontmatterMetadata(
  fm: Record<string, unknown>,
  editorLocale: Locale,
): { metadata: ArticleBlueprintMetadata; warnings: ImportWarning[]; keyFactBlocks: BlueprintBlock[] } {
  const warnings: ImportWarning[] = []
  const seoRaw = fm.seo
  const seo = seoRaw && typeof seoRaw === 'object' && !Array.isArray(seoRaw) ? (seoRaw as Record<string, unknown>) : undefined

  const fmLocale = typeof fm.locale === 'string' ? fm.locale.trim().toLowerCase() : editorLocale
  const locale: Locale = isValidLocale(fmLocale) ? fmLocale : editorLocale
  if (typeof fm.locale === 'string' && fm.locale.trim().toLowerCase() !== editorLocale) {
    warnings.push({
      code: 'LOCALE_MISMATCH',
      messageFr: `Locale du fichier (${fm.locale}) différente de la locale éditeur (${editorLocale}). L'import cible ${editorLocale}.`,
    })
  }

  const title =
    (typeof fm.title === 'string' && fm.title.trim()) ||
    (typeof fm.slug === 'string' ? fm.slug : '') ||
    'Sans titre'

  const standfirst = typeof fm.subtitle === 'string' ? fm.subtitle.trim() : ''

  let status: 'DRAFT' | 'PUBLISHED' = 'DRAFT'
  const st = typeof fm.status === 'string' ? fm.status.trim().toLowerCase() : 'draft'
  if (st === 'published' || st === 'publish') {
    status = 'PUBLISHED'
  } else {
    warnings.push({
      code: 'STATUS_DRAFT_KEPT',
      messageFr: 'Statut draft conservé — pas de publication automatique.',
    })
  }

  const categorySlugs: string[] = []
  if (typeof fm.category === 'string' && fm.category.trim()) {
    categorySlugs.push(fm.category.trim())
  }
  for (const tag of asStringArray(fm.tags)) {
    if (!categorySlugs.includes(tag)) categorySlugs.push(tag)
  }

  const slug = typeof fm.slug === 'string' ? fm.slug.trim() : undefined
  if (slug && !isValidSlug(slug)) {
    warnings.push({
      code: 'SLUG_INVALID',
      messageFr: `Slug frontmatter invalide : « ${slug} ».`,
    })
  }

  if (typeof fm.hero_image === 'string' && fm.hero_image.trim() && fm.hero_image.trim().toUpperCase() !== 'TBD') {
    warnings.push({
      code: 'HERO_IMAGE_IGNORED',
      messageFr: 'hero_image ignoré à ce stade (pas de liaison médiathèque automatique).',
    })
  }

  const metaTitle =
    typeof seo?.meta_title === 'string' && seo.meta_title.trim() ? seo.meta_title.trim() : null
  const metaDescription =
    typeof seo?.meta_description === 'string' && seo.meta_description.trim()
      ? seo.meta_description.trim()
      : null

  const seoJson = buildSeoJson(fm, seo)

  const keyFactBlocks: BlueprintBlock[] = []
  const fmKeyFacts = seo ? asStringArray(seo.key_facts) : []
  if (fmKeyFacts.length > 0) {
    keyFactBlocks.push(keyInformationBlockFromFacts(fmKeyFacts))
    warnings.push({
      code: 'KEY_INFORMATION_FROM_FRONTMATTER',
      messageFr: 'Bloc « Informations clés » créé depuis seo.key_facts du frontmatter.',
      blockType: ArticleBlockType.KEY_INFORMATION,
    })
  }

  const metadata: ArticleBlueprintMetadata = {
    slug,
    title,
    standfirst,
    locale,
    status,
    categorySlugs,
    authorName: typeof fm.author === 'string' && fm.author.trim() ? fm.author.trim() : undefined,
    metaTitle,
    metaDescription,
    seoJson,
    lastUpdatedHint:
      typeof fm.last_updated === 'string' && fm.last_updated.trim() ? fm.last_updated.trim() : undefined,
  }

  return { metadata, warnings, keyFactBlocks }
}

type SectionKind = 'learn_more' | 'sources' | null

function parseBodyMarkdown(
  body: string,
  context: { standfirst: string; title: string },
): { blocks: BlueprintBlock[]; warnings: ImportWarning[] } {
  const warnings: ImportWarning[] = []
  const blocks: BlueprintBlock[] = []
  const lines = body.replace(/\r\n/g, '\n').split('\n')
  let i = 0
  let skippedH1 = false
  let skippedIntroH2 = false
  const standfirstNorm = context.standfirst.trim().toLowerCase()

  const skipBlank = () => {
    while (i < lines.length && lines[i].trim() === '') i++
  }

  while (i < lines.length) {
    skipBlank()
    if (i >= lines.length) break

    const line = lines[i]
    const trimmed = line.trim()

    if (/^---+$/.test(trimmed) || /^\*\*\*+$/.test(trimmed)) {
      i++
      continue
    }

    if (/^#\s+/.test(line) && !/^##\s+/.test(line)) {
      const h1Text = stripHeadingMarks(line)
      if (!context.title || h1Text.toLowerCase() === context.title.trim().toLowerCase()) {
        warnings.push({
          code: 'H1_SKIPPED',
          messageFr: 'Titre H1 du body ignoré (déjà défini dans le frontmatter).',
        })
      }
      skippedH1 = true
      i++
      continue
    }

    if (/^##\s+/.test(line) && !/^###\s+/.test(line)) {
      const headingText = stripHeadingMarks(line)
      const norm = normalizeHeadingTitle(headingText)

      if (skippedH1 && !skippedIntroH2) {
        skippedIntroH2 = true
        if (standfirstNorm.length > 0 && standfirstNorm === headingText.toLowerCase()) {
          warnings.push({
            code: 'STANDFIRST_LINE_SKIPPED',
            messageFr: 'Intertitre ## du body ignoré (identique au subtitle / standfirst).',
          })
          i++
          continue
        }
      }

      if (SECTION_LEARN_MORE.has(norm)) {
        i++
        const contentLines: string[] = []
        while (i < lines.length) {
          if (/^##\s+/.test(lines[i]) && !/^###\s+/.test(lines[i])) break
          if (/^#\s+/.test(lines[i]) && !/^##\s+/.test(lines[i])) break
          contentLines.push(lines[i])
          i++
        }
        blocks.push({ type: ArticleBlockType.HEADING, data: { text: headingText } })
        const text = contentLines
          .map((l) => l.trim())
          .filter(Boolean)
          .join('\n\n')
        if (text) {
          blocks.push({ type: ArticleBlockType.PARAGRAPH, data: { text } })
        }
        continue
      }

      if (SECTION_SOURCES.has(norm)) {
        i++
        const items: string[] = []
        while (i < lines.length) {
          if (/^##\s+/.test(lines[i]) && !/^###\s+/.test(lines[i])) break
          if (/^#\s+/.test(lines[i]) && !/^##\s+/.test(lines[i])) break
          if (isBulletLine(lines[i])) {
            items.push(bulletContent(lines[i]))
            i++
            continue
          }
          if (lines[i].trim() === '') {
            i++
            continue
          }
          break
        }
        blocks.push({ type: ArticleBlockType.HEADING, data: { text: headingText } })
        blocks.push({
          type: ArticleBlockType.BULLET_LIST,
          data: { items: items.length ? items : [''] },
        })
        continue
      }

      blocks.push({ type: ArticleBlockType.HEADING, data: { text: headingText } })
      i++
      continue
    }

    if (/^###\s+/.test(line)) {
      blocks.push({ type: ArticleBlockType.HEADING, data: { text: stripHeadingMarks(line) } })
      i++
      continue
    }

    if (isImageLine(line)) {
      warnings.push({
        code: 'IMAGE_LINE_SKIPPED',
        messageFr: 'Image markdown ignorée (pas de média URL à ce stade).',
      })
      i++
      continue
    }

    const videoUrl = isVideoUrl(line)
    if (videoUrl) {
      const md = trimmed.match(/^\[([^\]]*)\]\((https?:\/\/[^)]+)\)\s*$/)
      blocks.push({
        type: ArticleBlockType.VIDEO,
        data: { url: videoUrl, caption: md?.[1]?.trim() || '' },
      })
      i++
      continue
    }

    if (isPdfLine(line)) {
      const md = trimmed.match(/\[([^\]]*)\]\(([^)]+)\)/)
      blocks.push({
        type: ArticleBlockType.DOCUMENT,
        data: {
          mediaId: '',
          title: md?.[1]?.trim() || trimmed,
        },
      })
      i++
      continue
    }

    if (isQuoteLine(line)) {
      const quoteLines: string[] = []
      while (i < lines.length && isQuoteLine(lines[i])) {
        quoteLines.push(quoteContent(lines[i]))
        i++
      }
      let author = ''
      let text = quoteLines.join('\n').trim()
      const attr = text.match(/\n?—\s*(.+)$/) || text.match(/\n?–\s*(.+)$/)
      if (attr) {
        author = attr[1].trim()
        text = text.slice(0, attr.index).trim()
      }
      blocks.push({ type: ArticleBlockType.QUOTE, data: { text, author } })
      continue
    }

    if (isBulletLine(line)) {
      const items: string[] = []
      while (i < lines.length && isBulletLine(lines[i])) {
        items.push(bulletContent(lines[i]))
        i++
      }
      blocks.push({ type: ArticleBlockType.BULLET_LIST, data: { items } })
      continue
    }

    if (isNumberedLine(line)) {
      const items: string[] = []
      while (i < lines.length && isNumberedLine(lines[i])) {
        items.push(numberedContent(lines[i]))
        i++
      }
      blocks.push({ type: ArticleBlockType.NUMBERED_LIST, data: { items } })
      continue
    }

    const paraLines: string[] = []
    while (i < lines.length) {
      const l = lines[i]
      if (l.trim() === '') break
      if (/^#{1,6}\s+/.test(l)) break
      if (isQuoteLine(l) || isBulletLine(l) || isNumberedLine(l)) break
      if (isImageLine(l)) break
      if (isVideoUrl(l)) break
      if (isPdfLine(l)) break
      paraLines.push(l)
      i++
    }
    if (paraLines.length) {
      blocks.push({
        type: ArticleBlockType.PARAGRAPH,
        data: { text: paraLines.join('\n').trim() },
      })
    }
  }

  return { blocks, warnings }
}

/**
 * Parse un fichier .md (frontmatter + body) en blueprint article CMS :
 * metadata + liste ordonnée de blocs + warnings.
 */
export function parseMarkdownArticleBlueprint(
  markdown: string,
  editorLocale: Locale,
): ArticleBlueprintResult {
  const warnings: ImportWarning[] = []

  if (!markdown.trim()) {
    return {
      metadata: {
        title: '',
        standfirst: '',
        locale: editorLocale,
        status: 'DRAFT',
        categorySlugs: [],
        seoJson: {},
      },
      blocks: [],
      warnings: [{ code: 'BODY_EMPTY', messageFr: 'Fichier markdown vide.' }],
    }
  }

  let fm: Record<string, unknown> = {}
  let body = markdown
  try {
    const parsed = matter(markdown)
    fm = (parsed.data ?? {}) as Record<string, unknown>
    body = parsed.content
  } catch {
    return {
      metadata: {
        title: '',
        standfirst: '',
        locale: editorLocale,
        status: 'DRAFT',
        categorySlugs: [],
        seoJson: {},
      },
      blocks: [],
      warnings: [{ code: 'YAML_INVALID', messageFr: 'Frontmatter YAML invalide.' }],
    }
  }

  const { metadata, warnings: fmWarnings, keyFactBlocks } = parseFrontmatterMetadata(fm, editorLocale)
  warnings.push(...fmWarnings)

  if (!body.trim()) {
    warnings.push({ code: 'BODY_EMPTY', messageFr: 'Corps markdown vide après le frontmatter.' })
  }

  const { blocks: bodyBlocks, warnings: bodyWarnings } = parseBodyMarkdown(body, {
    standfirst: metadata.standfirst,
    title: metadata.title,
  })
  warnings.push(...bodyWarnings)

  const blocks = [...keyFactBlocks, ...bodyBlocks]

  if (metadata.seoJson.sources?.length && !bodyBlocks.some((b) => b.type === ArticleBlockType.BULLET_LIST)) {
    const hasSourcesHeading = bodyBlocks.some(
      (b) =>
        b.type === ArticleBlockType.HEADING &&
        SECTION_SOURCES.has(normalizeHeadingTitle(String((b.data as { text?: string }).text ?? ''))),
    )
    if (!hasSourcesHeading) {
      warnings.push({
        code: 'SOURCES_FRONTMATTER_ONLY',
        messageFr: 'Sources listées dans le frontmatter uniquement (pas de section ## Sources dans le body).',
      })
    }
  }

  return { metadata, blocks, warnings }
}

export function filterKnownCategorySlugs(
  slugs: string[],
  knownSlugs: Set<string>,
): { accepted: string[]; warnings: ImportWarning[] } {
  const accepted: string[] = []
  const warnings: ImportWarning[] = []
  for (const slug of slugs) {
    if (knownSlugs.has(slug)) {
      accepted.push(slug)
    } else {
      warnings.push({
        code: 'TAG_UNKNOWN',
        messageFr: `Catégorie / tag ignoré (slug inconnu) : « ${slug} ».`,
      })
    }
  }
  return { accepted, warnings }
}
