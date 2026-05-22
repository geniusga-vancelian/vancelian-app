import type { PortalExclusiveOffer, PortalInvestPayload } from '@/lib/portal/investTypes'

type CatalogEngineSnapshot = {
  supply_apr?: number | string | null
  current_raised?: number | string | null
  target_size?: number | string | null
  progress_pct?: number | string | null
  investors_count?: number | string | null
  status?: string | null
  duration_months?: number | string | null
}

type CatalogProductRow = {
  id: string
  slug: string
  title?: string | null
  subtitle?: string | null
  coverUrl?: string | null
  category?: string | null
  engine?: {
    snapshot?: CatalogEngineSnapshot | null
  } | null
}

function toNumber(value: unknown, fallback = 0): number {
  if (value == null) return fallback
  if (typeof value === 'number' && !Number.isNaN(value)) return value
  const parsed = Number(String(value).replace(',', '.'))
  return Number.isNaN(parsed) ? fallback : parsed
}

function formatMoney(amount: number, currency = 'EUR'): string {
  try {
    return new Intl.NumberFormat('fr-FR', {
      style: 'currency',
      currency,
      maximumFractionDigits: 0,
    }).format(amount)
  } catch {
    return `${Math.round(amount)} ${currency}`
  }
}

function displayCategory(slug: string | null | undefined): string {
  const raw = (slug ?? '').trim()
  if (!raw) return 'Exclusive offer'
  return raw
    .split(/[-_]/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function mapOffer(row: CatalogProductRow): PortalExclusiveOffer {
  const snap = row.engine?.snapshot ?? {}
  const raised = toNumber(snap.current_raised)
  const target = toNumber(snap.target_size)
  const progressPct = Math.min(
    100,
    Math.max(0, toNumber(snap.progress_pct, target > 0 ? (raised / target) * 100 : 0)),
  )
  const apy = toNumber(snap.supply_apr)
  const status = (snap.status ?? '').toString().toLowerCase()
  const isFunded = progressPct >= 100 || status.includes('funded') || status.includes('closed')
  const slug = row.slug.trim()

  return {
    id: row.id,
    slug,
    title: row.title?.trim() || 'Exclusive offer',
    subtitle: row.subtitle?.trim() || '',
    coverUrl: row.coverUrl?.trim() || '',
    category: displayCategory(row.category),
    description: row.subtitle?.trim() || '',
    progressPct,
    raisedLabel: formatMoney(raised),
    targetLabel: target > 0 ? formatMoney(target) : '—',
    investorsCount: Math.max(0, Math.floor(toNumber(snap.investors_count))),
    apyLabel: apy > 0 ? `${apy.toFixed(2)}% APR` : '—',
    durationMonths: snap.duration_months != null ? Math.floor(toNumber(snap.duration_months)) : null,
    isFunded,
    href: slug ? `/app/invest/${encodeURIComponent(slug)}` : '/app/invest',
  }
}

export function buildPortalInvestPayload(products: CatalogProductRow[]): PortalInvestPayload {
  const offers = products.map(mapOffer)
  const first = offers[0]

  let heroImageUrl: string | null = null
  for (const offer of offers) {
    if (offer.coverUrl) {
      heroImageUrl = offer.coverUrl
      break
    }
  }

  return {
    heroImageUrl,
    heroTitle: first?.title || 'Invest',
    heroSubtitle:
      first?.subtitle ||
      'Build your portfolio with savings, exclusive real estate offers, and crypto.',
    offers,
  }
}
