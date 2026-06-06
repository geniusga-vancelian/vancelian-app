import type { VaultModulePublic } from '@/lib/cms/exclusiveOfferVaultPage'
import type { KeyInformationRow } from '@/lib/cms/exclusiveOfferTypes'

export type PortalVaultMetricRow = {
  key: string
  value: string
  icon: string
  tip?: string
}

export type PortalVaultTimelineStep = {
  state: 'done' | 'current' | 'future'
  label: string
  sub: string
  chip?: string
}

export type PortalVaultFaqItem = { q: string; a: string }

export type PortalVaultResource = {
  name: string
  size: string
  type: string
  downloadUrl: string
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}

export function normVaultModuleType(type: string): string {
  return type.trim().toLowerCase()
}

export function iconForMetricLabel(label: string): string {
  const l = label.toLowerCase()
  if (/rendement total|5 ans|cumulative/i.test(l)) return 'trending-up'
  if (/rendement annuel|apr|target/i.test(l)) return 'bar-chart-2'
  if (/rendement net|net/i.test(l)) return 'graph'
  if (/ticket|minimum/i.test(l)) return 'money-dollar'
  if (/durée|engagement|période|mois|ans/i.test(l)) return 'calendar'
  return 'info'
}

export function readKeyInformationRows(content: Record<string, unknown>): KeyInformationRow[] {
  const rows = Array.isArray(content.rows) ? content.rows : []
  return rows.flatMap((raw) => {
    const row = asRecord(raw)
    const label = typeof row?.label === 'string' ? row.label.trim() : ''
    const value = typeof row?.value === 'string' ? row.value.trim() : ''
    if (!label || !value) return []
    return [{ label, value }]
  })
}

export function readKeyInformationMetrics(content: Record<string, unknown>): PortalVaultMetricRow[] {
  return readKeyInformationRows(content).map((row) => ({
    key: row.label,
    value: row.value,
    icon: iconForMetricLabel(row.label),
  }))
}

/**
 * Bande « raised / funded » dans la section métriques portail : réservée au module
 * FundingModule explicite. Ne pas l’afficher pour KeyInformationModule seul même si
 * l’offre a un produit lending (`ctx.lending`).
 */
export function shouldShowVaultMetricsFundingStrip(fundingMod: unknown): boolean {
  return fundingMod != null
}

export function readFundingBlock(content: Record<string, unknown>, coverUrl: string | null) {
  const resolved = asRecord(content._resolved)
  if (!resolved) return null
  const pctRaw = resolved.progressPct
  const pct =
    typeof pctRaw === 'number'
      ? Math.min(100, Math.max(0, Math.round(pctRaw)))
      : typeof pctRaw === 'string'
        ? Math.min(100, Math.max(0, Math.round(Number.parseFloat(pctRaw))))
        : 0
  const target = typeof resolved.totalDisplay === 'string' ? resolved.totalDisplay : '—'
  const raised = typeof resolved.raisedDisplay === 'string' ? resolved.raisedDisplay : '—'
  return { raised, target, pct, coverUrl }
}

export function readCompetitiveAdvantages(content: Record<string, unknown>) {
  const title = typeof content.title === 'string' ? content.title.trim() : ''
  const rows = Array.isArray(content.rows) ? content.rows : []
  const items = rows.flatMap((raw) => {
    const row = asRecord(raw)
    const t = typeof row?.title === 'string' ? row.title.trim() : ''
    const body = typeof row?.description === 'string' ? row.description.trim() : ''
    if (!t && !body) return []
    return [{ title: t, body }]
  })
  return { title, items }
}

export function readStepsTimeline(content: Record<string, unknown>): PortalVaultTimelineStep[] {
  const items = Array.isArray(content.items) ? content.items : []
  const steps: PortalVaultTimelineStep[] = []
  let foundCurrent = false

  for (const raw of items) {
    const row = asRecord(raw)
    const label = typeof row?.title === 'string' ? row.title.trim() : ''
    if (!label) continue
    const sub =
      typeof row?.description === 'string'
        ? row.description.trim()
        : typeof row?.date === 'string'
          ? row.date.trim()
          : typeof row?.dayLabel === 'string'
            ? row.dayLabel.trim()
            : ''
    const tags = Array.isArray(row?.tags) ? row.tags : []
    const chip = typeof tags[0] === 'string' ? tags[0] : undefined
    const completed = row?.isCompleted === true

    let state: PortalVaultTimelineStep['state']
    if (completed) state = 'done'
    else if (!foundCurrent) {
      state = 'current'
      foundCurrent = true
    } else state = 'future'

    steps.push({ state, label, sub, chip })
  }

  return steps
}

export function readFaqItems(content: Record<string, unknown>): PortalVaultFaqItem[] {
  const items = Array.isArray(content.items) ? content.items : []
  return items.flatMap((raw) => {
    const row = asRecord(raw)
    const q = typeof row?.question === 'string' ? row.question.trim() : ''
    const a =
      typeof row?.standfirst === 'string'
        ? row.standfirst.trim()
        : typeof row?.answer === 'string'
          ? row.answer.trim()
          : ''
    if (!q || !a) return []
    return [{ q, a }]
  })
}

export function readDocumentResources(content: Record<string, unknown>): PortalVaultResource[] {
  const items = Array.isArray(content.documentItems) ? content.documentItems : []
  return items.flatMap((raw) => {
    const row = asRecord(raw)
    const downloadUrl = typeof row?.downloadUrl === 'string' ? row.downloadUrl.trim() : ''
    const displayName = typeof row?.displayName === 'string' ? row.displayName.trim() : 'Document'
    const dateLabel = typeof row?.dateLabel === 'string' ? row.dateLabel.trim() : ''
    if (!downloadUrl) return []
    return [{ name: displayName, size: dateLabel || 'PDF', type: 'PDF', downloadUrl }]
  })
}

export function readMarkdownModule(content: Record<string, unknown>) {
  const moduleTitle = typeof content.moduleTitle === 'string' ? content.moduleTitle.trim() : ''
  const markdown = typeof content.markdown === 'string' ? content.markdown.trim() : ''
  const links = Array.isArray(content.links)
    ? (content.links as Array<{ label?: string; url?: string }>)
    : []
  return { moduleTitle, markdown, links }
}

export function readParagraphText(content: Record<string, unknown>): string {
  if (typeof content.text === 'string' && content.text.trim()) return content.text.trim()
  if (typeof content.markdown === 'string' && content.markdown.trim()) return content.markdown.trim()
  return ''
}

export function isAdvisorMarkdownModule(mod: VaultModulePublic): boolean {
  if (normVaultModuleType(mod.type) !== 'simplemarkdowncontentmodule') return false
  const title = typeof mod.content.moduleTitle === 'string' ? mod.content.moduleTitle.trim() : ''
  return /conseil|advisor/i.test(title)
}

export type PortalVaultCarouselItem = {
  url: string
  alt: string | null
  mediaId: string
}

export function readCarouselItems(content: Record<string, unknown>): PortalVaultCarouselItem[] {
  const items = Array.isArray(content.carouselItems) ? content.carouselItems : []
  return items.flatMap((raw) => {
    const row = asRecord(raw)
    const url = typeof row?.url === 'string' ? row.url.trim() : ''
    const mediaId = typeof row?.mediaId === 'string' ? row.mediaId : url
    if (!url) return []
    const alt = typeof row?.alt === 'string' ? row.alt : null
    return [{ url, alt, mediaId }]
  })
}

export type PortalVaultBlogArticle = {
  id: string
  slug: string
  title: string
  standfirst: string
  coverUrl: string
  readingTime: number
  publishedAt: string | null
}

export function readBlogArticles(content: Record<string, unknown>): PortalVaultBlogArticle[] {
  const raw = Array.isArray(content._resolvedArticles) ? content._resolvedArticles : []
  return raw.flatMap((row) => {
    const o = asRecord(row)
    if (!o) return []
    const id = typeof o.id === 'string' ? o.id : ''
    const slug = typeof o.slug === 'string' ? o.slug : ''
    const title = typeof o.title === 'string' ? o.title : ''
    if (!id || !slug || !title) return []
    const rt = typeof o.readingTime === 'number' ? o.readingTime : NaN
    return [
      {
        id,
        slug,
        title,
        standfirst: typeof o.standfirst === 'string' ? o.standfirst : '',
        coverUrl: typeof o.coverUrl === 'string' ? o.coverUrl : '',
        readingTime: Number.isFinite(rt) ? rt : 0,
        publishedAt: typeof o.publishedAt === 'string' ? o.publishedAt : null,
      },
    ]
  })
}

export function extractBlogArticleSlug(slugOrPath: string): string {
  const normalized = slugOrPath.trim().replace(/^\/+/, '')
  if (!normalized) return ''
  const parts = normalized.split('/').filter(Boolean)
  return parts[parts.length - 1] ?? normalized
}

export type PortalVaultMarketingCard = {
  imageUrl: string
  title: string
  description: string
  href: string
}

export function readMarketingCardItems(content: Record<string, unknown>): PortalVaultMarketingCard[] {
  const raw = content.items
  if (!Array.isArray(raw)) return []
  return raw.flatMap((it) => {
    const row = asRecord(it)
    if (!row) return []
    const imageUrl =
      typeof row.imageUrl === 'string'
        ? row.imageUrl.trim()
        : typeof row.posterImageUrl === 'string'
          ? row.posterImageUrl.trim()
          : ''
    if (!imageUrl) return []
    return [
      {
        imageUrl,
        title: typeof row.title === 'string' ? row.title.trim() : '',
        description: typeof row.description === 'string' ? row.description.trim() : '',
        href:
          typeof row.redirectUrl === 'string'
            ? row.redirectUrl.trim()
            : typeof row.href === 'string'
              ? row.href.trim()
              : '',
      },
    ]
  })
}

export function readPerformanceChartValues(content: Record<string, unknown>): number[] {
  const resolved = asRecord(content._resolved)
  const points = Array.isArray(resolved?.points) ? resolved!.points : []
  return points.flatMap((raw) => {
    const row = asRecord(raw)
    const value = Number(row?.value)
    return Number.isFinite(value) ? [value] : []
  })
}

export type PortalVaultTransactionRow = {
  label: string
  amount: string
  date: string
}

export function readTransactionRows(content: Record<string, unknown>): PortalVaultTransactionRow[] {
  const resolved = asRecord(content._resolved)
  const rows = Array.isArray(resolved?.rows) ? resolved!.rows : []
  return rows.flatMap((raw) => {
    const row = asRecord(raw)
    if (!row) return []
    return [
      {
        label: typeof row.label === 'string' ? row.label.trim() : '—',
        amount: typeof row.amount === 'string' ? row.amount.trim() : '',
        date: typeof row.date === 'string' ? row.date.trim() : '',
      },
    ]
  })
}

export type PortalVaultVideoItem = {
  title: string
  posterImageUrl: string
  videoUrl: string
  date: string
}

export function readVideoItems(content: Record<string, unknown>): PortalVaultVideoItem[] {
  const raw = content.items
  if (!Array.isArray(raw)) return []
  return raw.flatMap((it) => {
    const row = asRecord(it)
    if (!row) return []
    const posterImageUrl = typeof row.posterImageUrl === 'string' ? row.posterImageUrl.trim() : ''
    const videoUrl = typeof row.videoUrl === 'string' ? row.videoUrl.trim() : ''
    if (!posterImageUrl && !videoUrl) return []
    return [
      {
        title: typeof row.title === 'string' ? row.title.trim() : '',
        posterImageUrl,
        videoUrl,
        date: typeof row.date === 'string' ? row.date.trim() : '',
      },
    ]
  })
}

export function readQuoteBlock(content: Record<string, unknown>) {
  const text = typeof content.text === 'string' ? content.text.trim() : ''
  const author = typeof content.author === 'string' ? content.author.trim() : ''
  return { text, author }
}

export function readListItems(content: Record<string, unknown>): string[] {
  const raw = content.items
  if (!Array.isArray(raw)) return []
  return raw.flatMap((it) => (typeof it === 'string' && it.trim() ? [it.trim()] : []))
}
