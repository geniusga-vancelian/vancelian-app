import { appDsCryptoSvgPath } from '@/components/design-system/app/AppProductBasketCard'
import {
  bundleTargetWeightToPct,
  normalizeVaultModuleType,
  readAllocationSlices,
} from '@/lib/portal/bundleProductFormat'
import type {
  PortalBundleAllocationRow,
  PortalBundleProductDetailPayload,
  PortalBundleVaultModule,
} from '@/lib/portal/bundleProductTypes'
import { cryptoBrandColor } from '@/lib/portal/cryptoInstrumentAssets'

function isCoffreProductCode(code: string): boolean {
  const c = code.toLowerCase()
  return (
    c.includes('flex') ||
    c.includes('avenir') ||
    c.includes('future') ||
    c.includes('coffre')
  )
}

export type PortalPanierMetricRow = {
  key: string
  value: string
  tip?: string
  icon: string
}

export type PortalPanierCompositionItem = {
  sym: string
  name: string
  pct: number
  icon: string
  color: string
}

export type PortalPanierExitItem = {
  kind: string
  desc: string
  chip?: string
  cta?: boolean
}

export type PortalPanierPerfWindow = {
  label: string
  pct: number
}

export type PortalPanierDetailView = {
  productCode: string
  title: string
  subtitle: string
  category: string
  heroImageUrl: string | null
  perf1yLabel: string | null
  assetCount: number
  advisorText: string | null
  headline: {
    aum: string | null
    holders: string | null
    flow30d: string | null
  }
  metrics: PortalPanierMetricRow[]
  whyTitle: string
  whyItems: Array<{ title: string; body: string }>
  overviewTitle: string
  overviewText: string | null
  composition: PortalPanierCompositionItem[]
  rebalanceLabel: string | null
  exits: PortalPanierExitItem[]
  faq: Array<{ q: string; a: string }>
  faqFooterHref: string | null
  resources: Array<{ name: string; size: string; type: string; downloadUrl: string }>
  aside: {
    perfHighlight: string | null
    ticket: string | null
    fees: string | null
    liquidity: string
    aum: string | null
    holders: string | null
  }
  isCoffre: boolean
}

const DEFAULT_PANIER_EXITS: PortalPanierExitItem[] = [
  {
    kind: 'Sortie standard',
    desc: 'Cession à tout moment au prix du marché. Fonds disponibles sous 24 h sur votre compte Vancelian.',
    chip: 'Instantanée',
  },
  {
    kind: 'Sortie programmée',
    desc: 'Mise en place d’un ordre de vente échelonné sur 4 à 12 semaines pour lisser le prix de sortie.',
    chip: 'Sur demande',
    cta: true,
  },
]

function asRecord(v: unknown): Record<string, unknown> | null {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}

function findModule(modules: PortalBundleVaultModule[], type: string): PortalBundleVaultModule | undefined {
  const norm = normalizeVaultModuleType(type)
  return modules.find((m) => normalizeVaultModuleType(m.type) === norm)
}

function findModules(modules: PortalBundleVaultModule[], types: string[]): PortalBundleVaultModule[] {
  const set = new Set(types.map(normalizeVaultModuleType))
  return modules.filter((m) => set.has(normalizeVaultModuleType(m.type)))
}

function titleMatches(title: string, pattern: RegExp): boolean {
  return pattern.test(title.trim())
}

function iconForMetricLabel(label: string): string {
  const l = label.toLowerCase()
  if (/performance|rendement|1 an|5 ans/i.test(l)) return 'trending-up'
  if (/volatilit/i.test(l)) return 'bar-chart-2'
  if (/ticket|minimum/i.test(l)) return 'money-dollar'
  if (/rebalance|rééquilibr/i.test(l)) return 'exchange'
  if (/frais|fee/i.test(l)) return 'info'
  if (/apy|taux/i.test(l)) return 'graph'
  return 'info'
}

function readAdvisorText(modules: PortalBundleVaultModule[], subtitle: string): string | null {
  for (const mod of findModules(modules, ['simplemarkdowncontentmodule'])) {
    const title =
      typeof mod.content.moduleTitle === 'string' ? mod.content.moduleTitle.trim() : ''
    const markdown = typeof mod.content.markdown === 'string' ? mod.content.markdown.trim() : ''
    if (titleMatches(title, /conseil|advisor/i) && markdown) return markdown
  }
  if (subtitle.trim()) return subtitle.trim()
  return null
}

function readWhy(modules: PortalBundleVaultModule[]) {
  const mod = findModule(modules, 'competitiveadvantagesmodule')
  if (!mod) return { whyTitle: 'Pourquoi ce panier', whyItems: [] as Array<{ title: string; body: string }> }
  const titleRaw = typeof mod.content.title === 'string' ? mod.content.title.trim() : ''
  const rows = Array.isArray(mod.content.rows) ? mod.content.rows : []
  const whyItems = rows.flatMap((raw) => {
    const row = asRecord(raw)
    const t = typeof row?.title === 'string' ? row.title.trim() : ''
    const b = typeof row?.description === 'string' ? row.description.trim() : ''
    if (!t && !b) return []
    return [{ title: t, body: b }]
  })
  return { whyTitle: titleRaw || 'Pourquoi ce panier', whyItems }
}

function readOverview(modules: PortalBundleVaultModule[], title: string) {
  for (const mod of findModules(modules, ['simplemarkdowncontentmodule', 'descriptionmodule'])) {
    const moduleTitle =
      typeof mod.content.moduleTitle === 'string'
        ? mod.content.moduleTitle.trim()
        : typeof mod.content.title === 'string'
          ? mod.content.title.trim()
          : ''
    const markdown =
      typeof mod.content.markdown === 'string'
        ? mod.content.markdown.trim()
        : typeof mod.content.text === 'string'
          ? mod.content.text.trim()
          : ''
    if (titleMatches(moduleTitle, /panier|détail|overview|aperçu/i) && markdown) {
      return { overviewTitle: moduleTitle || 'Le panier en détail', overviewText: markdown }
    }
  }
  for (const mod of findModules(modules, ['simplemarkdowncontentmodule'])) {
    const markdown = typeof mod.content.markdown === 'string' ? mod.content.markdown.trim() : ''
    if (markdown.length > 80) {
      return { overviewTitle: 'Le panier en détail', overviewText: markdown }
    }
  }
  return { overviewTitle: 'Le panier en détail', overviewText: null }
}

function readKeyMetrics(modules: PortalBundleVaultModule[]): PortalPanierMetricRow[] {
  const mod = findModule(modules, 'keyinformationmodule')
  if (!mod) return []
  const rows = Array.isArray(mod.content.rows) ? mod.content.rows : []
  return rows.flatMap((raw) => {
    const row = asRecord(raw)
    const label = typeof row?.label === 'string' ? row.label.trim() : ''
    const value = typeof row?.value === 'string' ? row.value.trim() : ''
    const tip = typeof row?.tooltip === 'string' ? row.tooltip.trim() : undefined
    if (!label || !value) return []
    return [{ key: label, value, tip, icon: iconForMetricLabel(label) }]
  })
}

function readHeadlineFromMetrics(metrics: PortalPanierMetricRow[]) {
  let aum: string | null = null
  let holders: string | null = null
  let flow30d: string | null = null
  for (const row of metrics) {
    const l = row.key.toLowerCase()
    if (/encours|aum|tvl/i.test(l)) aum = row.value
    if (/détenteur|investisseur|depositor/i.test(l)) holders = row.value
    if (/flux|30\s*j|inflow/i.test(l)) flow30d = row.value
  }
  return { aum, holders, flow30d }
}

function readFaq(modules: PortalBundleVaultModule[]) {
  const mod = findModule(modules, 'faqaccordionmodule')
  if (!mod) return { faq: [], faqFooterHref: null as string | null }
  const items = Array.isArray(mod.content.items) ? mod.content.items : []
  const faq = items.flatMap((raw) => {
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
  const faqFooterHref =
    typeof mod.content.footerLinkUrl === 'string' ? mod.content.footerLinkUrl.trim() : null
  return { faq, faqFooterHref }
}

function readResources(modules: PortalBundleVaultModule[]) {
  const mod = findModule(modules, 'documentslistmodule')
  if (!mod) return []
  const items = Array.isArray(mod.content.documentItems) ? mod.content.documentItems : []
  return items.flatMap((raw) => {
    const row = asRecord(raw)
    const downloadUrl = typeof row?.downloadUrl === 'string' ? row.downloadUrl.trim() : ''
    const displayName = typeof row?.displayName === 'string' ? row.displayName.trim() : 'Document'
    const dateLabel = typeof row?.dateLabel === 'string' ? row.dateLabel.trim() : ''
    if (!downloadUrl) return []
    return [
      {
        name: displayName,
        size: dateLabel || 'PDF',
        type: 'PDF',
        downloadUrl,
      },
    ]
  })
}

function readRebalanceLabel(metrics: PortalPanierMetricRow[]): string | null {
  const row = metrics.find((m) => /rebalance|rééquilibr/i.test(m.key))
  return row?.value ?? null
}

function buildComposition(
  allocations: PortalBundleAllocationRow[],
  modules: PortalBundleVaultModule[],
): PortalPanierCompositionItem[] {
  if (allocations.length > 0) {
    return allocations.map((a) => ({
      sym: a.assetSymbol,
      name: a.name || a.assetSymbol,
      pct: bundleTargetWeightToPct(a.targetWeight),
      icon: appDsCryptoSvgPath(a.assetSymbol) ?? '/app-ds/assets/crypto/btc.svg',
      color: cryptoBrandColor(a.assetSymbol),
    }))
  }
  const allocMod = findModule(modules, 'allocationmodule')
  if (!allocMod) return []
  return readAllocationSlices(allocMod.content).map((slice) => {
    const sym = slice.label.split(' ')[0]?.toUpperCase() ?? slice.label
    return {
      sym,
      name: slice.label,
      pct: slice.percentage,
      icon: appDsCryptoSvgPath(sym) ?? '/app-ds/assets/crypto/btc.svg',
      color: slice.colorHex || cryptoBrandColor(sym),
    }
  })
}

function resolveHeroImage(payload: PortalBundleProductDetailPayload): string | null {
  if (payload.headerMediaUrl?.trim()) return payload.headerMediaUrl.trim()
  if (payload.detailMediaUrl?.trim()) return payload.detailMediaUrl.trim()
  const code = payload.productCode.toLowerCase()
  if (code.includes('flex')) return '/app-ds/assets/photos/coffre-flex.png'
  if (code.includes('avenir') || code.includes('future')) {
    return '/app-ds/assets/photos/coffre-avenir.png'
  }
  return '/app-ds/assets/photos/panier-crypto.png'
}

export function formatPerfPctLabel(pct: number | null | undefined): string | null {
  if (pct == null || !Number.isFinite(pct)) return null
  const sign = pct >= 0 ? '+ ' : '− '
  const formatted = Math.abs(pct).toLocaleString('fr-FR', {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  })
  return `${sign}${formatted} %`
}

export function buildPortalPanierDetailView(
  payload: PortalBundleProductDetailPayload,
  options?: { perf1yPct?: number | null },
): PortalPanierDetailView {
  const isCoffre = isCoffreProductCode(payload.productCode)

  const { whyTitle, whyItems } = readWhy(payload.modules)
  const { overviewTitle, overviewText } = readOverview(payload.modules, payload.title)
  const metrics = readKeyMetrics(payload.modules)
  const headline = readHeadlineFromMetrics(metrics)
  const composition = buildComposition(payload.allocations, payload.modules)
  const { faq, faqFooterHref } = readFaq(payload.modules)
  const resources = readResources(payload.modules)
  const rebalanceLabel = readRebalanceLabel(metrics)

  const perf1yLabel = formatPerfPctLabel(options?.perf1yPct ?? null)

  const ticketRow = metrics.find((m) => /ticket|minimum/i.test(m.key))
  const feesRow = metrics.find((m) => /frais|fee/i.test(m.key))
  const perfRow = metrics.find((m) => /performance.*1 an|1 an/i.test(m.key))

  return {
    productCode: payload.productCode,
    title: payload.title,
    subtitle: payload.subtitle,
    category: isCoffre ? 'Coffre' : 'Panier crypto',
    heroImageUrl: resolveHeroImage(payload),
    perf1yLabel: perf1yLabel ?? perfRow?.value ?? null,
    assetCount: composition.length,
    advisorText: readAdvisorText(payload.modules, payload.subtitle),
    headline,
    metrics,
    whyTitle,
    whyItems,
    overviewTitle,
    overviewText,
    composition,
    rebalanceLabel,
    exits: DEFAULT_PANIER_EXITS,
    faq,
    faqFooterHref,
    resources,
    aside: {
      perfHighlight: perf1yLabel ?? perfRow?.value ?? null,
      ticket: ticketRow?.value ?? '100 €',
      fees: feesRow?.value ?? null,
      liquidity: '24 h',
      aum: headline.aum,
      holders: headline.holders,
    },
    isCoffre,
  }
}

export const PANIER_PERF_WINDOW_PERIODS: Array<{ label: string; period: string }> = [
  { label: '30 jours', period: '1m' },
  { label: '6 mois', period: '1m' },
  { label: '1 an', period: '1a' },
  { label: '3 ans', period: '5a' },
  { label: '5 ans', period: '5a' },
]

