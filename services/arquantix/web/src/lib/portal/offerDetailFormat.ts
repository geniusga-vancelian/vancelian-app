import type { ExclusiveOfferVaultPayload } from '@/lib/cms/exclusiveOfferVaultPage'
import {
  normVaultModuleType,
  readCarouselItems,
} from '@/lib/portal/vaultModulePortalFormat'

export type PortalOfferHeroView = {
  title: string
  category: string | null
  /** URLs hero — carrousel CMS ou image d'en-tête. */
  photos: string[]
  /** Vidéo promo TitlePage — prioritaire sur `photos` (lecture auto en arrière-plan). */
  promoVideoUrl: string | null
  closingLabel: string | null
  /** Premier `MediaImageCarouselModule` alimentant le hero (reste aussi rendu dans le corps). */
  heroCarouselModuleId: string | null
}

export type PortalOfferAsideView = {
  yearlyReturn: string | null
  ticket: string | null
  term: string | null
  closingLabel: string | null
  raised: string | null
  pct: number
  investors: number | null
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}

function readClosingLabel(payload: ExclusiveOfferVaultPayload): string | null {
  for (const row of payload.lending?.keyInformationRows ?? []) {
    if (/clôture|closing|fin de souscription/i.test(row.label)) return row.value
  }

  for (const mod of payload.contentModules) {
    if (mod.type !== 'KeyInformationModule') continue
    const rows = Array.isArray(mod.content.rows) ? mod.content.rows : []
    for (const raw of rows) {
      const row = asRecord(raw)
      const label = typeof row?.label === 'string' ? row.label : ''
      const value = typeof row?.value === 'string' ? row.value : ''
      if (/clôture|closing|fin de souscription/i.test(label)) return value
    }
  }

  return null
}

function readTerm(payload: ExclusiveOfferVaultPayload): string | null {
  for (const row of payload.lending?.keyInformationRows ?? []) {
    if (/durée|engagement|période|mois|ans/i.test(row.label)) return row.value
  }

  for (const mod of payload.contentModules) {
    if (mod.type !== 'KeyInformationModule') continue
    const rows = Array.isArray(mod.content.rows) ? mod.content.rows : []
    for (const raw of rows) {
      const row = asRecord(raw)
      const label = typeof row?.label === 'string' ? row.label : ''
      const value = typeof row?.value === 'string' ? row.value : ''
      if (/durée|engagement|période|mois|ans/i.test(label)) return value
    }
  }

  return null
}

function readYearlyReturn(payload: ExclusiveOfferVaultPayload): string | null {
  if (payload.lending) {
    return `${payload.lending.supplyAprPct.toLocaleString('en-US', {
      minimumFractionDigits: 1,
      maximumFractionDigits: 1,
    })} %`
  }

  for (const mod of payload.contentModules) {
    if (mod.type !== 'KeyInformationModule') continue
    const rows = Array.isArray(mod.content.rows) ? mod.content.rows : []
    for (const raw of rows) {
      const row = asRecord(raw)
      const label = typeof row?.label === 'string' ? row.label : ''
      const value = typeof row?.value === 'string' ? row.value : ''
      if (/rendement annuel|apr/i.test(label) && value) return value
    }
  }

  return null
}

function readFundingProgress(payload: ExclusiveOfferVaultPayload): {
  raised: string | null
  pct: number
} {
  if (payload.lending) {
    return {
      raised: payload.lending.raised,
      pct: Math.min(100, Math.max(0, Math.round(payload.lending.progressPct))),
    }
  }

  for (const mod of payload.contentModules) {
    if (mod.type !== 'FundingModule') continue
    const resolved = asRecord(mod.content._resolved)
    if (!resolved) continue
    const pctRaw = resolved.progressPct
    const pct =
      typeof pctRaw === 'number'
        ? Math.min(100, Math.max(0, Math.round(pctRaw)))
        : typeof pctRaw === 'string'
          ? Math.min(100, Math.max(0, Math.round(Number.parseFloat(pctRaw))))
          : 0
    return { raised: null, pct }
  }

  return { raised: null, pct: 0 }
}

function pushUniquePhoto(photos: string[], url: string | null | undefined) {
  const trimmed = url?.trim()
  if (!trimmed || photos.includes(trimmed)) return
  photos.push(trimmed)
}

/** Photos hero — priorité au `MediaImageCarouselModule`, repli sur `headerImageUrl`. */
export function resolveHeroPhotos(payload: ExclusiveOfferVaultPayload): {
  photos: string[]
  heroCarouselModuleId: string | null
} {
  const photos: string[] = []
  let heroCarouselModuleId: string | null = null

  for (const mod of payload.contentModules) {
    if (normVaultModuleType(mod.type) !== 'mediaimagecarouselmodule') continue
    const items = readCarouselItems(mod.content)
    if (!items.length) continue
    for (const item of items) pushUniquePhoto(photos, item.url)
    heroCarouselModuleId = mod.id
    break
  }

  if (!photos.length) pushUniquePhoto(photos, payload.headerImageUrl)

  return { photos, heroCarouselModuleId }
}

/** Données hero portail — titre / tags / visuel issus du payload Vault Builder. */
export function buildPortalOfferHeroView(payload: ExclusiveOfferVaultPayload): PortalOfferHeroView {
  const { photos, heroCarouselModuleId } = resolveHeroPhotos(payload)
  return {
    title: payload.heroTitle,
    category: payload.heroTags[0] ?? null,
    photos,
    promoVideoUrl: payload.heroPromoVideoUrl,
    closingLabel: readClosingLabel(payload),
    heroCarouselModuleId,
  }
}

/** Données aside investissement (module volant) — lending + métriques Vault, en attendant le CMS. */
export function buildPortalOfferAsideView(payload: ExclusiveOfferVaultPayload): PortalOfferAsideView {
  const closingLabel = readClosingLabel(payload)
  const { raised, pct } = readFundingProgress(payload)

  return {
    yearlyReturn: readYearlyReturn(payload),
    ticket: payload.lending?.minTicket ?? null,
    term: readTerm(payload),
    closingLabel,
    raised,
    pct,
    investors: null,
  }
}
