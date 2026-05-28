import type {
  ExclusiveOfferVaultPayload,
  VaultModulePublic,
} from '@/lib/cms/exclusiveOfferVaultPage'
import type { KeyInformationRow } from '@/lib/cms/exclusiveOfferTypes'

export type PortalOfferTimelineStep = {
  state: 'done' | 'current' | 'future'
  label: string
  sub: string
  chip?: string
}

export type PortalOfferMetricRow = {
  key: string
  value: string
  tip?: string
  icon: string
}

export type PortalOfferDetailView = {
  slug: string
  title: string
  subtitle: string | null
  category: string | null
  coverUrl: string | null
  galleryUrls: string[]
  closingLabel: string | null
  advisorText: string | null
  funding: {
    raised: string
    target: string
    pct: number
    investors: number | null
    coverUrl: string | null
  } | null
  metrics: PortalOfferMetricRow[]
  whyTitle: string | null
  whyItems: Array<{ title: string; body: string }>
  overviewTitle: string | null
  overviewText: string | null
  location: {
    title: string
    address: string | null
    access: string | null
    embedUrl: string | null
  } | null
  narrative: {
    title: string
    text: string
    primaryCta?: { label: string; href: string }
    secondaryCta?: { label: string; href: string }
  } | null
  timeline: PortalOfferTimelineStep[]
  faq: Array<{ q: string; a: string }>
  faqFooterLabel: string | null
  faqFooterHref: string | null
  resources: Array<{ name: string; size: string; type: string; downloadUrl: string }>
  aside: {
    yearlyReturn: string | null
    ticket: string | null
    term: string | null
    closingLabel: string | null
    raised: string | null
    pct: number
    investors: number | null
  }
  extraModules: VaultModulePublic[]
}

function normType(type: string): string {
  return type.trim().toLowerCase()
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}

function findModules(modules: VaultModulePublic[], types: string[]): VaultModulePublic[] {
  const set = new Set(types.map(normType))
  return modules.filter((m) => set.has(normType(m.type)))
}

function findFirstModule(modules: VaultModulePublic[], types: string[]): VaultModulePublic | null {
  const set = new Set(types.map(normType))
  return modules.find((m) => set.has(normType(m.type))) ?? null
}

function titleMatches(title: string, pattern: RegExp): boolean {
  return pattern.test(title.trim())
}

function readGalleryUrls(modules: VaultModulePublic[], headerImageUrl: string | null): string[] {
  const carousel = findFirstModule(modules, ['MediaImageCarouselModule'])
  const urls: string[] = []
  if (headerImageUrl?.trim()) urls.push(headerImageUrl.trim())
  if (carousel) {
    const items = Array.isArray(carousel.content.carouselItems) ? carousel.content.carouselItems : []
    for (const raw of items) {
      const row = asRecord(raw)
      const url = typeof row?.url === 'string' ? row.url.trim() : ''
      if (url && !urls.includes(url)) urls.push(url)
    }
  }
  return urls
}

function readMarkdownModule(mod: VaultModulePublic): { title: string; markdown: string } {
  const title = typeof mod.content.moduleTitle === 'string' ? mod.content.moduleTitle.trim() : ''
  const markdown = typeof mod.content.markdown === 'string' ? mod.content.markdown.trim() : ''
  return { title, markdown }
}

function readAdvisorText(modules: VaultModulePublic[], subtitle: string | null): string | null {
  for (const mod of findModules(modules, ['SimpleMarkdownContentModule'])) {
    const { title, markdown } = readMarkdownModule(mod)
    if (titleMatches(title, /conseil|advisor/i) && markdown) return markdown
  }
  if (subtitle?.trim()) return subtitle.trim()
  for (const mod of findModules(modules, ['SimpleMarkdownContentModule'])) {
    const { markdown } = readMarkdownModule(mod)
    if (markdown.length > 40) return markdown
  }
  return null
}

function readFunding(
  modules: VaultModulePublic[],
  lending: ExclusiveOfferVaultPayload['lending'],
  coverUrl: string | null,
): PortalOfferDetailView['funding'] {
  const fundingMod = findFirstModule(modules, ['FundingModule'])
  const resolved = asRecord(fundingMod?.content._resolved)

  if (lending) {
    return {
      raised: lending.raised,
      target: lending.target,
      pct: Math.min(100, Math.max(0, Math.round(lending.progressPct))),
      investors: null,
      coverUrl,
    }
  }

  if (resolved) {
    const pctRaw = resolved.progressPct
    const pct =
      typeof pctRaw === 'number'
        ? Math.min(100, Math.max(0, Math.round(pctRaw)))
        : typeof pctRaw === 'string'
          ? Math.min(100, Math.max(0, Math.round(Number.parseFloat(pctRaw))))
          : 0
    const target = typeof resolved.totalDisplay === 'string' ? resolved.totalDisplay : '—'
    return {
      raised: '—',
      target,
      pct,
      investors: null,
      coverUrl,
    }
  }

  return null
}

function readMetricRows(
  modules: VaultModulePublic[],
  lending: ExclusiveOfferVaultPayload['lending'],
): PortalOfferMetricRow[] {
  const rows: PortalOfferMetricRow[] = []
  const keyInfo = findFirstModule(modules, ['KeyInformationModule'])
  const keyRows: KeyInformationRow[] = Array.isArray(keyInfo?.content.rows)
    ? (keyInfo!.content.rows as KeyInformationRow[])
    : lending?.keyInformationRows ?? []

  for (const row of keyRows) {
    const label = row.label?.trim() ?? ''
    const value = row.value?.trim() ?? ''
    if (!label || !value) continue
    rows.push({
      key: label,
      value,
      icon: iconForMetricLabel(label),
    })
  }

  if (lending?.minTicket) {
    const hasTicket = rows.some((r) => /ticket|minimum/i.test(r.key))
    if (!hasTicket) {
      rows.push({
        key: 'Ticket minimum',
        value: lending.minTicket,
        icon: 'money-dollar',
        tip: "Montant minimum d'investissement pour une part.",
      })
    }
  }

  return rows
}

function iconForMetricLabel(label: string): string {
  const l = label.toLowerCase()
  if (/rendement total|5 ans|cumulative/i.test(l)) return 'trending-up'
  if (/rendement annuel|apr|target/i.test(l)) return 'bar-chart-2'
  if (/rendement net|net/i.test(l)) return 'graph'
  if (/ticket|minimum/i.test(l)) return 'money-dollar'
  if (/durée|engagement|période|mois|ans/i.test(l)) return 'calendar'
  return 'info'
}

function readWhySection(modules: VaultModulePublic[], locationCity: string | null) {
  const mod = findFirstModule(modules, ['CompetitiveAdvantagesModule'])
  if (!mod) return { whyTitle: null, whyItems: [] as Array<{ title: string; body: string }> }

  const titleRaw = typeof mod.content.title === 'string' ? mod.content.title.trim() : ''
  const rows = Array.isArray(mod.content.rows) ? mod.content.rows : []
  const whyItems = rows.flatMap((raw) => {
    const row = asRecord(raw)
    const title = typeof row?.title === 'string' ? row.title.trim() : ''
    const body = typeof row?.description === 'string' ? row.description.trim() : ''
    if (!title && !body) return []
    return [{ title, body }]
  })

  const city = locationCity?.split(',')[0]?.trim()
  const whyTitle =
    titleRaw ||
    (city ? `Pourquoi ${city}, pourquoi maintenant ?` : 'Pourquoi investir, pourquoi maintenant ?')

  return { whyTitle, whyItems }
}

function readOverview(modules: VaultModulePublic[], title: string) {
  for (const mod of findModules(modules, ['SimpleMarkdownContentModule'])) {
    const { title: moduleTitle, markdown } = readMarkdownModule(mod)
    if (titleMatches(moduleTitle, /bien|overview|aperçu|détail/i) && markdown) {
      return { overviewTitle: moduleTitle || 'Le bien en détail', overviewText: markdown }
    }
  }
  for (const mod of findModules(modules, ['PARAGRAPH'])) {
    const body =
      typeof mod.content.text === 'string'
        ? mod.content.text.trim()
        : typeof mod.content.markdown === 'string'
          ? mod.content.markdown.trim()
          : ''
    if (body.length > 80) {
      return { overviewTitle: 'Le bien en détail', overviewText: body }
    }
  }
  return { overviewTitle: 'Le bien en détail', overviewText: title }
}

function readLocation(modules: VaultModulePublic[]) {
  const mod = findFirstModule(modules, ['LocalisationModule'])
  if (!mod) return null
  const c = mod.content
  const moduleTitle = typeof c.moduleTitle === 'string' ? c.moduleTitle.trim() : 'Localisation'
  const description = typeof c.description === 'string' ? c.description.trim() : ''
  const embedUrl = typeof c.embedUrl === 'string' ? c.embedUrl.trim() : ''
  if (!description && !embedUrl) return null
  return {
    title: moduleTitle,
    address: description || null,
    access: null,
    embedUrl: embedUrl || null,
  }
}

function readNarrative(modules: VaultModulePublic[]) {
  for (const mod of findModules(modules, ['SimpleMarkdownContentModule'])) {
    const { title, markdown } = readMarkdownModule(mod)
    if (titleMatches(title, /vancelian|narratif|projet|équipe|structur/i) && markdown) {
      const links = Array.isArray(mod.content.links)
        ? (mod.content.links as Array<{ label?: string; url?: string }>)
        : []
      const primary = links.find((l) => l?.label && l?.url)
      const secondary = links.find((l) => l !== primary && l?.label && l?.url)
      return {
        title: title || 'Pourquoi Vancelian a sélectionné ce projet',
        text: markdown,
        ...(primary?.label && primary.url
          ? { secondaryCta: { label: primary.label, href: primary.url } }
          : {}),
        ...(secondary?.label && secondary.url
          ? { primaryCta: { label: secondary.label, href: secondary.url } }
          : {}),
      }
    }
  }
  return null
}

function readTimeline(modules: VaultModulePublic[]): PortalOfferTimelineStep[] {
  const mod = findFirstModule(modules, ['stepsmodule', 'StepsModule'])
  if (!mod) return []
  const items = Array.isArray(mod.content.items) ? mod.content.items : []
  const steps: PortalOfferTimelineStep[] = []
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

    let state: PortalOfferTimelineStep['state']
    if (completed) {
      state = 'done'
    } else if (!foundCurrent) {
      state = 'current'
      foundCurrent = true
    } else {
      state = 'future'
    }

    steps.push({ state, label, sub, chip })
  }

  return steps
}

function readFaq(modules: VaultModulePublic[]) {
  const mod = findFirstModule(modules, ['FaqAccordionModule'])
  if (!mod) return { faq: [], faqFooterLabel: null, faqFooterHref: null }
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
  const faqFooterLabel =
    typeof mod.content.footerLinkLabel === 'string' ? mod.content.footerLinkLabel.trim() : null
  const faqFooterHref =
    typeof mod.content.footerLinkUrl === 'string' ? mod.content.footerLinkUrl.trim() : null
  return { faq, faqFooterLabel, faqFooterHref }
}

function readResources(modules: VaultModulePublic[]) {
  const mod = findFirstModule(modules, ['DocumentsListModule'])
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

function readClosingLabel(modules: VaultModulePublic[], lending: ExclusiveOfferVaultPayload['lending']) {
  for (const row of lending?.keyInformationRows ?? []) {
    if (/clôture|closing|fin de souscription/i.test(row.label)) return row.value
  }
  const keyInfo = findFirstModule(modules, ['KeyInformationModule'])
  const rows = Array.isArray(keyInfo?.content.rows) ? keyInfo!.content.rows : []
  for (const raw of rows) {
    const row = asRecord(raw)
    const label = typeof row?.label === 'string' ? row.label : ''
    const value = typeof row?.value === 'string' ? row.value : ''
    if (/clôture|closing|fin de souscription/i.test(label)) return value
  }
  return null
}

function readYearlyReturn(lending: ExclusiveOfferVaultPayload['lending'], metrics: PortalOfferMetricRow[]) {
  if (lending) {
    return `${lending.supplyAprPct.toLocaleString('fr-FR', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })} %`
  }
  const hit = metrics.find((m) => /rendement annuel|apr/i.test(m.key))
  return hit?.value ?? null
}

function readTerm(metrics: PortalOfferMetricRow[]) {
  const hit = metrics.find((m) => /durée|engagement|période/i.test(m.key))
  return hit?.value ?? null
}

const CONSUMED_TYPES = new Set([
  'mediaimagecarouselmodule',
  'simplemarkdowncontentmodule',
  'competitiveadvantagesmodule',
  'localisationmodule',
  'stepsmodule',
  'faqaccordionmodule',
  'documentslistmodule',
  'keyinformationmodule',
  'fundingmodule',
  'paragraph',
])

function isConsumedModule(mod: VaultModulePublic, advisorText: string | null, overviewText: string | null): boolean {
  const type = normType(mod.type)
  if (CONSUMED_TYPES.has(type)) return true
  if (type === 'simplemarkdowncontentmodule') {
    const { markdown } = readMarkdownModule(mod)
    if (markdown && (markdown === advisorText || markdown === overviewText)) return true
  }
  return false
}

/** Transforme le payload vault CMS en vue portail alignée handoff Offre.html. */
export function buildPortalOfferDetailView(payload: ExclusiveOfferVaultPayload): PortalOfferDetailView {
  const modules = payload.contentModules
  const coverUrl = payload.headerImageUrl
  const galleryUrls = readGalleryUrls(modules, coverUrl)
  const advisorText = readAdvisorText(modules, payload.heroSubtitle)
  const funding = readFunding(modules, payload.lending, coverUrl)
  const metrics = readMetricRows(modules, payload.lending)
  const location = readLocation(modules)
  const { whyTitle, whyItems } = readWhySection(
    modules,
    location?.address ?? payload.heroSubtitle,
  )
  const { overviewTitle, overviewText } = readOverview(modules, payload.heroTitle)
  const narrative = readNarrative(modules)
  const timeline = readTimeline(modules)
  const { faq, faqFooterLabel, faqFooterHref } = readFaq(modules)
  const resources = readResources(modules)
  const closingLabel = readClosingLabel(modules, payload.lending)

  const extraModules = modules.filter((m) => !isConsumedModule(m, advisorText, overviewText))

  return {
    slug: payload.pageSlug,
    title: payload.heroTitle,
    subtitle: payload.heroSubtitle,
    category: payload.heroTags[0] ?? null,
    coverUrl,
    galleryUrls,
    closingLabel,
    advisorText,
    funding,
    metrics,
    whyTitle,
    whyItems,
    overviewTitle,
    overviewText,
    location,
    narrative,
    timeline,
    faq,
    faqFooterLabel,
    faqFooterHref,
    resources,
    aside: {
      yearlyReturn: readYearlyReturn(payload.lending, metrics),
      ticket: payload.lending?.minTicket ?? null,
      term: readTerm(metrics),
      closingLabel,
      raised: funding?.raised ?? null,
      pct: funding?.pct ?? 0,
      investors: funding?.investors ?? null,
    },
    extraModules,
  }
}
