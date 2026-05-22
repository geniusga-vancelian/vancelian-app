export type PortalNewsItem = {
  id: string
  slug: string
  title: string
  coverUrl: string
  readingTime: number
  tag?: string
  publishedAt?: string | null
  publishedDate?: string
  authorName?: string
  href: string
}

export type PortalNewsWidgetData = {
  title: string
  headerHref?: string
  items: PortalNewsItem[]
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  return value as Record<string, unknown>
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback
}

function asInt(value: unknown, fallback: number): number {
  if (typeof value === 'number' && Number.isFinite(value)) return Math.floor(value)
  if (typeof value === 'string') {
    const parsed = Number.parseInt(value, 10)
    if (Number.isFinite(parsed)) return parsed
  }
  return fallback
}

function mapKey(itemToCard: Record<string, unknown>, key: string): string {
  const mapped = itemToCard[key]
  return typeof mapped === 'string' && mapped.trim() ? mapped.trim() : key
}

function articleHref(slug: string): string {
  const s = slug.trim()
  if (!s) return '/blog'
  if (s.startsWith('/')) return s
  return `/blog/${s}`
}

function resolveHeaderHref(schema: Record<string, unknown>): string | undefined {
  const redirect = asRecord(schema.titleRedirect)
  if (!redirect) return '/blog'
  const type = asString(redirect.type).toLowerCase()
  const target = asString(redirect.target).toLowerCase()
  if (type === 'internal' && target === 'blog') return '/blog'
  if (type === 'internal' && target === 'research') return '/blog?type=research'
  return '/blog'
}

/** Parse la réponse `GET /api/mobile/flutter/widgets/top10news` (même source que Flutter). */
export function parseTop10NewsWidget(payload: unknown): PortalNewsWidgetData | null {
  const root = asRecord(payload)
  if (!root) return null

  const widgetRaw = asRecord(root.widget)
  const feedsRaw = asRecord(root.feeds)
  if (!widgetRaw || !feedsRaw) return null

  const schema = asRecord(widgetRaw.schemaJson) ?? {}
  const widgetTitle = asString(schema.title, 'Vancelian News')
  const headerHref = resolveHeaderHref(schema)
  const modules = Array.isArray(schema.modules) ? schema.modules : []

  const allItems: PortalNewsItem[] = []

  for (const module of modules) {
    const m = asRecord(module)
    if (!m) continue
    const type = asString(m.type).trim().toLowerCase()
    if (type !== 'blogalaune' && type !== 'blog_a_la_une') continue

    const feedSlug = asString(m.feedSlug).trim()
    if (!feedSlug) continue
    const feed = asRecord(feedsRaw[feedSlug])
    if (!feed) continue

    const itemsRaw = Array.isArray(feed.items) ? feed.items : []
    const feedBinding = asRecord(m.feedBinding) ?? {}
    const itemToCard = asRecord(feedBinding.itemToCard) ?? {}

    const coverKey = mapKey(itemToCard, 'coverUrl')
    const titleKey = mapKey(itemToCard, 'title')
    const readingKey = mapKey(itemToCard, 'readingTime')
    const tagKey = mapKey(itemToCard, 'tag')

    const sectionTitle = asString(m.title, widgetTitle)

    for (const raw of itemsRaw) {
      const it = asRecord(raw)
      if (!it) continue
      const slug = asString(it.slug).trim()
      const title = asString(it[titleKey], asString(it.title, 'Article')).trim()
      const coverUrl = asString(it[coverKey], asString(it.coverUrl)).trim()
      const tag = asString(it[tagKey], asString(it.categoryLabel)).trim()
      const readingTime = asInt(it[readingKey] ?? it.readingTime, 1)
      const publishedAt = asString(it.publishedAt) || null
      const publishedDate = asString(it.publishedDate, asString(it.metaText))
      const authorName = asString(it.authorName).trim()
      const id = asString(it.id, slug || title)

      allItems.push({
        id,
        slug,
        title,
        coverUrl,
        readingTime: Math.max(1, readingTime),
        tag: tag || undefined,
        publishedAt: publishedAt || undefined,
        publishedDate: publishedDate || undefined,
        authorName: authorName || undefined,
        href: articleHref(slug),
      })
    }

    if (allItems.length > 0) {
      return {
        title: sectionTitle || widgetTitle,
        headerHref,
        items: allItems,
      }
    }
  }

  return null
}
