import matter from 'gray-matter'
import { ArticleBlockType } from '@prisma/client'
import { isValidLocale, type Locale } from '@/config/locales'
import { BLOCK_TYPE_LABELS, type AddableBlockType } from '@/lib/admin/articleBlockCatalog'
import { getBlockSummary } from '@/lib/admin/articleBlockSummary'

export const ARTICLE_BLOCKS_MARKDOWN_FORMAT = 'vancelian-article-blocks'
export const ARTICLE_BLOCKS_MARKDOWN_VERSION = 1

export type ArticleBlockMarkdownRow = {
  type: ArticleBlockType
  data: Record<string, unknown>
}

export type ArticleBlockMarkdownWarningCode =
  | 'YAML_INVALID'
  | 'FORMAT_UNKNOWN'
  | 'VERSION_UNSUPPORTED'
  | 'BODY_EMPTY'
  | 'LOCALE_MISMATCH'
  | 'BLOCK_TYPE_UNKNOWN'
  | 'BLOCK_JSON_INVALID'
  | 'BLOCK_SECTION_SKIPPED'
  | 'BLOCKS_WILL_REPLACE'

export type ArticleBlockMarkdownWarning = {
  code: ArticleBlockMarkdownWarningCode
  messageFr: string
  blockIndex?: number
  blockType?: string
}

export type ArticleBlocksMarkdownExportInput = {
  type: ArticleBlockType
  data: Record<string, unknown>
}

export type ArticleBlocksMarkdownParseResult = {
  locale: Locale
  blocks: ArticleBlockMarkdownRow[]
  warnings: ArticleBlockMarkdownWarning[]
}

const BLOCK_SECTION_RE = /^## Block:\s*([A-Za-z0-9_]+)\s*$/gm
const JSON_FENCE_RE = /```article-block-json\s*\n([\s\S]*?)\n```/i

const KNOWN_BLOCK_TYPES = new Set<string>(Object.values(ArticleBlockType))

function cloneData(data: Record<string, unknown>): Record<string, unknown> {
  return structuredClone(data) as Record<string, unknown>
}

function normalizeBlockData(data: unknown): Record<string, unknown> {
  if (data != null && typeof data === 'object' && !Array.isArray(data)) {
    return cloneData(data as Record<string, unknown>)
  }
  return {}
}

/** Sérialise les Content Blocks d'un article (sans metadata article, SEO, cover). */
export function exportArticleBlocksToMarkdown(
  blocks: ArticleBlocksMarkdownExportInput[],
  locale: Locale,
): string {
  const rows = blocks.map((b) => ({
    type: b.type,
    data: normalizeBlockData(b.data),
  }))

  const sections = rows.map((row) => {
    const json = JSON.stringify(row.data, null, 2)
    return [
      `## Block: ${row.type}`,
      '',
      '```article-block-json',
      json,
      '```',
      '',
    ].join('\n')
  })

  const body = [
    '# Content Blocks',
    '',
    '> Export CMS article — section **Content Blocks** uniquement.',
    '> Exclut : titre, slug, standfirst, SEO, cover et métadonnées éditoriales.',
    '',
    rows.length === 0 ? '_Aucun bloc._' : sections.join('\n').trimEnd(),
    '',
  ].join('\n')

  const fm = {
    format: ARTICLE_BLOCKS_MARKDOWN_FORMAT,
    version: ARTICLE_BLOCKS_MARKDOWN_VERSION,
    locale,
    blockCount: rows.length,
    exportedAt: new Date().toISOString(),
  }

  return matter.stringify(body, fm)
}

function parseBlockSection(
  sectionBody: string,
  blockType: string,
  blockIndex: number,
): { row: ArticleBlockMarkdownRow | null; warnings: ArticleBlockMarkdownWarning[] } {
  const warnings: ArticleBlockMarkdownWarning[] = []

  if (!KNOWN_BLOCK_TYPES.has(blockType)) {
    warnings.push({
      code: 'BLOCK_TYPE_UNKNOWN',
      messageFr: `Type de bloc ignoré (inconnu) : « ${blockType} ».`,
      blockIndex,
      blockType,
    })
    return { row: null, warnings }
  }

  const jsonMatch = sectionBody.match(JSON_FENCE_RE)
  if (!jsonMatch?.[1]?.trim()) {
    warnings.push({
      code: 'BLOCK_JSON_INVALID',
      messageFr: `Bloc JSON manquant ou vide pour le bloc « ${blockType} ».`,
      blockIndex,
      blockType,
    })
    return { row: null, warnings }
  }

  let data: Record<string, unknown>
  try {
    const parsed = JSON.parse(jsonMatch[1]) as unknown
    if (parsed == null || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('data must be object')
    }
    data = parsed as Record<string, unknown>
  } catch {
    warnings.push({
      code: 'BLOCK_JSON_INVALID',
      messageFr: `JSON invalide pour le bloc « ${blockType} ».`,
      blockIndex,
      blockType,
    })
    return { row: null, warnings }
  }

  return {
    row: { type: blockType as ArticleBlockType, data },
    warnings,
  }
}

/** Lit un export Markdown et reconstruit la liste ordonnée de blocs article. */
export function parseArticleBlocksMarkdown(
  markdown: string,
  editorLocale: Locale,
): ArticleBlocksMarkdownParseResult {
  const warnings: ArticleBlockMarkdownWarning[] = []

  if (!markdown.trim()) {
    return {
      locale: editorLocale,
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
      locale: editorLocale,
      blocks: [],
      warnings: [{ code: 'YAML_INVALID', messageFr: 'Frontmatter YAML invalide.' }],
    }
  }

  const format = typeof fm.format === 'string' ? fm.format.trim() : ''
  if (format && format !== ARTICLE_BLOCKS_MARKDOWN_FORMAT) {
    warnings.push({
      code: 'FORMAT_UNKNOWN',
      messageFr: `Format non reconnu (« ${format} »). Attendu : ${ARTICLE_BLOCKS_MARKDOWN_FORMAT}.`,
    })
  }

  const version = Number(fm.version)
  if (Number.isFinite(version) && version !== ARTICLE_BLOCKS_MARKDOWN_VERSION) {
    warnings.push({
      code: 'VERSION_UNSUPPORTED',
      messageFr: `Version ${version} non supportée (attendu ${ARTICLE_BLOCKS_MARKDOWN_VERSION}).`,
    })
  }

  const fmLocale = typeof fm.locale === 'string' ? fm.locale.trim() : ''
  const locale: Locale = isValidLocale(fmLocale) ? fmLocale : editorLocale
  if (fmLocale && isValidLocale(fmLocale) && fmLocale !== editorLocale) {
    warnings.push({
      code: 'LOCALE_MISMATCH',
      messageFr: `Locale du fichier (${fmLocale.toUpperCase()}) différente de la langue éditée (${editorLocale.toUpperCase()}).`,
    })
  }

  const matches = [...body.matchAll(BLOCK_SECTION_RE)]
  if (matches.length === 0) {
    if (!body.trim() || /_Aucun bloc\._/i.test(body)) {
      return { locale, blocks: [], warnings }
    }
    warnings.push({
      code: 'BODY_EMPTY',
      messageFr: 'Aucune section « ## Block: … » trouvée dans le fichier.',
    })
    return { locale, blocks: [], warnings }
  }

  const blocks: ArticleBlockMarkdownRow[] = []

  for (let i = 0; i < matches.length; i++) {
    const match = matches[i]!
    const blockType = match[1]!.trim()
    const start = (match.index ?? 0) + match[0].length
    const end = i + 1 < matches.length ? (matches[i + 1]!.index ?? body.length) : body.length
    const sectionBody = body.slice(start, end)

    const { row, warnings: sectionWarnings } = parseBlockSection(sectionBody, blockType, i)
    warnings.push(...sectionWarnings)
    if (row) blocks.push(row)
  }

  if (blocks.length === 0 && matches.length > 0) {
    warnings.push({
      code: 'BLOCK_SECTION_SKIPPED',
      messageFr: 'Aucun bloc valide n’a pu être reconstruit.',
    })
  }

  return { locale, blocks, warnings }
}

export function isArticleBlocksMarkdownExport(markdown: string): boolean {
  if (!markdown.trim()) return false
  try {
    const parsed = matter(markdown)
    const fm = (parsed.data ?? {}) as Record<string, unknown>
    return fm.format === ARTICLE_BLOCKS_MARKDOWN_FORMAT
  } catch {
    return false
  }
}

export function summarizeArticleBlockImportPreview(
  blocks: ArticleBlockMarkdownRow[],
): Array<{ index: number; type: string; label: string; preview: string }> {
  return blocks.map((b, index) => {
    const label =
      BLOCK_TYPE_LABELS[b.type as AddableBlockType] ??
      (KNOWN_BLOCK_TYPES.has(b.type) ? b.type : 'Bloc inconnu')
    const preview = getBlockSummary({ type: b.type, data: b.data })
    return { index, type: b.type, label, preview }
  })
}
