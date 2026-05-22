/**
 * Page publique « détail offre » : contenu Vault Builder (`vault_builder_v1`) + métadonnées produit packagé / lending.
 */
import {
  ContentStatus,
  PackagedCommercialStatus,
  PackagedProductType,
  PackagedVisibility,
} from '@prisma/client'

import { getLocaleOrDefault, defaultLocale, type Locale } from '@/config/locales'
import { prisma } from '@/lib/prisma'
import type { PrismaClient } from '@prisma/client'

import {
  VAULT_BUILDER_TEMPLATE,
  VAULT_SECTION_KEY,
  resolveMediaUrl,
} from '@/lib/catalog/packagedCatalogHelpers'
import { resolvePageSeoFields } from '@/lib/cms/resolvePageI18nMetadata'
import { resolveVaultSectionContentForExclusiveOfferPayload } from '@/lib/cms/resolveVaultSectionContent'
import { normalizeVaultModulesFromSectionData } from '@/lib/vault/normalizeVaultModules'
import {
  ensureBlogALaUneFromDraftWhenRelatedNews,
} from '@/lib/catalog/ensureBlogALaUneVaultModuleForRelatedNews'
import {
  getArticlesLinkedToVaultPageSlugs,
  type ArticlePreview,
} from '@/lib/blog/articleService'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import type { KeyInformationRow } from '@/lib/cms/exclusiveOfferTypes'

export type { KeyInformationRow } from '@/lib/cms/exclusiveOfferTypes'

const devShowDraftExclusiveOffers =
  process.env.NODE_ENV === 'development' &&
  process.env.ARQUANTIX_DEV_SHOW_DRAFT_EXCLUSIVE_OFFERS === 'true'

export type VaultModulePublic = {
  id: string
  type: string
  enabled: boolean
  content: Record<string, unknown>
}

export type LendingSnapshot = {
  asset: string
  supplyAprPct: number
  raised: string
  target: string
  progressPct: number
  status: string
  minTicket: string | null
  maxTicket: string | null
  keyInformationRows: KeyInformationRow[]
}

function buildKeyInformationRows(
  lpp: {
    supplyAprBps: unknown
    startDate: Date | null
    maturityDate: Date | null
  },
  locale: Locale,
): KeyInformationRow[] {
  const fr = locale === 'fr'
  const apr = Number(lpp.supplyAprBps) / 100
  const rows: KeyInformationRow[] = []

  rows.push({
    label: fr ? 'Rendement annuel fixe' : 'Fixed annual yield',
    value: fr
      ? `${apr.toFixed(1).replace('.', ',')}% APR`
      : `${apr.toFixed(1)}% APR`,
  })

  if (lpp.startDate && lpp.maturityDate) {
    const ms =
      new Date(lpp.maturityDate).getTime() - new Date(lpp.startDate).getTime()
    const months = Math.max(1, Math.round(ms / (30.44 * 86400000)))
    rows.push({
      label: fr ? "Période d'engagement" : 'Commitment period',
      value: fr ? `${months} mois` : `${months} months`,
    })
  }

  if (lpp.maturityDate) {
    rows.push({
      label: fr ? 'Date de livraison' : 'Delivery date',
      value: String(new Date(lpp.maturityDate).getFullYear()),
    })
  }

  return rows
}

/**
 * Origine du titre / sous-titre hero (web) :
 * - `titlePage` : premier module Vault `TitlePage` (titre/sous-titre éditoriaux).
 * - `pageSeo` : fallback unique via `resolvePageSeoFields` — **PageI18n** (locale demandée) → **PageI18n** (locale par défaut) → champs **`Page.title` / `Page.description`**.
 */
export type HeroTitleProvenance = 'titlePage' | 'pageSeo'

export type ExclusiveOfferVaultPayload = {
  pageSlug: string
  /** Titre / description : `PageI18n` pour la locale, puis défaut, puis `Page.title` / `description` (`resolvePageSeoFields`). */
  pageTitle: string
  pageDescription: string | null
  urlPath: string
  locale: Locale
  headerImageUrl: string | null
  packagedProductId: string | null
  productType: PackagedProductType | null
  lending: LendingSnapshot | null
  /**
   * Titre / sous-titre hero (module `TitlePage` en tête si présent — aligné hero-secondary DS),
   * sinon métadonnées Page CMS.
   */
  heroTitle: string
  heroSubtitle: string | null
  /**
   * @deprecated Toujours tableau vide — plus d’injection produit / libellé exclusivité sur le web.
   * Tags hero : utiliser `heroTags` (premier `TagsModule` du vault).
   */
  tagPills: string[]
  /** Pastilles hero (premier module `TagsModule` du vault, retiré du corps). */
  heroTags: string[]
  /** Origine titre/sous-titre hero (TitlePage vs SEO Page/PageI18n). */
  heroTitleSource: HeroTitleProvenance
  /** Modules sous le hero (sans le premier `TitlePage` ni le premier `TagsModule` consommés par le hero). */
  contentModules: VaultModulePublic[]
  /** @deprecated Utiliser `contentModules` ; conservé pour l’API JSON existante. */
  modules: VaultModulePublic[]
}

function asRecord(v: unknown): Record<string, unknown> | null {
  return v != null && typeof v === 'object' && !Array.isArray(v) ? (v as Record<string, unknown>) : null
}

function isBlogAlaUneVaultModuleType(raw: string): boolean {
  const t = raw.trim().toLowerCase()
  return t === 'blogalaune' || t === 'blog_a_la_une'
}

/**
 * Données blog pour le DS (chemins relatifs sous forme `{locale}/blog/...`).
 * Injecté sous `content._resolvedArticles` pour `BlogALaUne` lors du SSR.
 */
function enrichBlogAlaUneVaultModulesForWeb(
  modules: VaultModulePublic[],
  locale: Locale,
  previews: ArticlePreview[],
): VaultModulePublic[] {
  if (!previews.length) return modules
  const activeLocale = getLocaleOrDefault(locale)
  const blogHrefPrefix = `/${activeLocale}/blog`
  return modules.map((m) => {
    if (!m.enabled || !isBlogAlaUneVaultModuleType(m.type)) {
      return m
    }
    const c = m.content
    const limRaw = c.limit
    let limit = 3
    if (typeof limRaw === 'number' && Number.isFinite(limRaw)) limit = Math.round(limRaw)
    else if (typeof limRaw === 'string') limit = Number.parseInt(limRaw.trim(), 10) || 3
    limit = Math.min(Math.max(limit, 1), 24)

    const _resolvedArticles = previews.slice(0, limit).map((p) => ({
      id: p.id,
      slug: `${blogHrefPrefix}/${p.slug}`,
      title: p.title,
      standfirst: p.standfirst,
      coverUrl: p.coverUrl,
      authorName: p.authorName,
      publishedAt: p.publishedAt,
      readingTime: p.readingTime,
    }))

    return { ...m, content: { ...c, _resolvedArticles } }
  })
}

function parseTagsModuleTags(content: Record<string, unknown>): string[] {
  const rawTags = Array.isArray(content.tags) ? content.tags : []
  return rawTags
    .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    .map((t) => t.trim())
}

/**
 * Premier **TitlePage** (peu importe l’index) → titre / sous-titre hero ; premier **TagsModule** → pastilles hero.
 * Ces modules sont retirés de la liste corps. Fallback SEO : `resolvePageSeoFields` (PageI18n + Page).
 */
export function splitTitlePageHeroFromModules(
  pageTitle: string,
  pageDescription: string | null,
  modules: VaultModulePublic[],
): {
  heroTitle: string
  heroSubtitle: string | null
  heroTags: string[]
  contentModules: VaultModulePublic[]
  heroTitleSource: HeroTitleProvenance
} {
  const indicesToRemove = new Set<number>()
  let heroTitle = pageTitle
  let heroSubtitle = pageDescription
  let heroTitleSource: HeroTitleProvenance = 'pageSeo'
  const heroTags: string[] = []

  const titlePageIdx = modules.findIndex((m) => m.type === 'TitlePage')
  if (titlePageIdx !== -1) {
    const first = modules[titlePageIdx]!
    const c = first.content
    const t = typeof c.title === 'string' ? c.title.trim() : ''
    const s = typeof c.subtitle === 'string' ? c.subtitle.trim() : ''
    heroTitle = t || pageTitle
    heroSubtitle = s || pageDescription
    heroTitleSource = 'titlePage'
    indicesToRemove.add(titlePageIdx)
  }

  const tagsIdx = modules.findIndex((m) => m.type === 'TagsModule')
  if (tagsIdx !== -1) {
    heroTags.push(...parseTagsModuleTags(modules[tagsIdx]!.content))
    indicesToRemove.add(tagsIdx)
  }

  const contentModules = modules.filter((_, i) => !indicesToRemove.has(i))

  return {
    heroTitle,
    heroSubtitle,
    heroTags,
    contentModules,
    heroTitleSource,
  }
}

/**
 * Résout les IDs média du module `MediaImageCarouselModule` en URLs (pré-signées) + alt pour le rendu web.
 * Les données stockées restent `imageMediaIds` ; `carouselItems` est enrichi à la volée.
 */
async function enrichMediaCarouselModules(
  prisma: PrismaClient,
  modules: VaultModulePublic[],
  publicOrigin?: string | null,
): Promise<VaultModulePublic[]> {
  const out: VaultModulePublic[] = []
  for (const m of modules) {
    if (m.type !== 'MediaImageCarouselModule') {
      out.push(m)
      continue
    }
    const c = m.content
    const rawIds = Array.isArray(c.imageMediaIds) ? c.imageMediaIds : []
    const imageMediaIds = rawIds.filter(
      (x): x is string => typeof x === 'string' && x.trim().length > 0,
    )
    const carouselItems: Array<{ mediaId: string; url: string; alt: string | null }> = []
    for (const mediaId of imageMediaIds) {
      const url = await resolveMediaUrl(prisma, mediaId, { publicOrigin: publicOrigin ?? undefined })
      if (!url) continue
      const row = await prisma.media.findUnique({
        where: { id: mediaId },
        select: { alt: true },
      })
      carouselItems.push({ mediaId, url, alt: row?.alt ?? null })
    }
    out.push({
      ...m,
      content: {
        ...c,
        imageMediaIds,
        carouselItems,
      },
    })
  }
  return out
}

async function enrichTitlePageModuleImages(
  prisma: PrismaClient,
  modules: VaultModulePublic[],
  publicOrigin?: string | null,
): Promise<VaultModulePublic[]> {
  const out: VaultModulePublic[] = []
  for (const m of modules) {
    if (m.type !== 'TitlePage') {
      out.push(m)
      continue
    }
    const c = { ...m.content }
    const singleId =
      typeof c.imageMediaId === 'string' && c.imageMediaId.trim().length > 0
        ? c.imageMediaId.trim()
        : null
    let imageUrl = typeof c.imageUrl === 'string' ? c.imageUrl : ''
    if (singleId && (!imageUrl || !imageUrl.trim())) {
      const u = await resolveMediaUrl(prisma, singleId, {
        publicOrigin: publicOrigin ?? undefined,
      })
      if (u) imageUrl = u
    }
    if ((!imageUrl || !imageUrl.trim()) && Array.isArray(c.imageMediaIds)) {
      for (const id of c.imageMediaIds) {
        if (typeof id === 'string' && id.trim()) {
          const u = await resolveMediaUrl(prisma, id.trim(), {
            publicOrigin: publicOrigin ?? undefined,
          })
          if (u) {
            imageUrl = u
            break
          }
        }
      }
    }
    out.push({
      ...m,
      content: {
        ...c,
        ...(imageUrl.trim().length > 0 ? { imageUrl } : {}),
      },
    })
  }
  return out
}

/**
 * Résout `posterMediaId` par carte en `posterImageUrl` (pré-signée) pour le rendu app / web.
 * Conserve `posterImageUrl` saisi à la main si aucun ID médiathèque.
 */
async function enrichVideoBlockArticleModules(
  prisma: PrismaClient,
  modules: VaultModulePublic[],
  publicOrigin?: string | null,
): Promise<VaultModulePublic[]> {
  const out: VaultModulePublic[] = []
  for (const m of modules) {
    if (m.type !== 'VideoBlockArticleModule') {
      out.push(m)
      continue
    }
    const c = m.content
    const rawItems = Array.isArray(c.items) ? c.items : []
    const items = await Promise.all(
      rawItems.map(async (it) => {
        const row = it != null && typeof it === 'object' ? (it as Record<string, unknown>) : {}
        const posterMediaId =
          typeof row.posterMediaId === 'string' && row.posterMediaId.trim().length > 0
            ? row.posterMediaId.trim()
            : null
        let posterImageUrl = typeof row.posterImageUrl === 'string' ? row.posterImageUrl : ''
        if (posterMediaId) {
          const url = await resolveMediaUrl(prisma, posterMediaId, {
            publicOrigin: publicOrigin ?? undefined,
          })
          if (url) posterImageUrl = url
        }
        return {
          ...row,
          posterImageUrl,
          ...(posterMediaId ? { posterMediaId } : {}),
        }
      }),
    )
    out.push({
      ...m,
      content: {
        ...c,
        items,
      },
    })
  }
  return out
}

function formatDocumentListDateLabel(d: Date): string {
  const s = d.toLocaleString('sv-SE', { timeZone: 'Europe/Paris' })
  return s.length >= 16 ? s.slice(0, 16) : s
}

function parseDocumentEntriesFromVaultContent(c: Record<string, unknown>): Array<{
  mediaId: string
  documentName: string
}> {
  if (Array.isArray(c.documentEntries)) {
    const out: Array<{ mediaId: string; documentName: string }> = []
    for (const x of c.documentEntries) {
      if (x != null && typeof x === 'object' && !Array.isArray(x)) {
        const o = x as Record<string, unknown>
        const mediaId = typeof o.mediaId === 'string' ? o.mediaId.trim() : ''
        if (!mediaId) continue
        const documentName = typeof o.documentName === 'string' ? o.documentName : ''
        out.push({ mediaId, documentName })
      }
    }
    return out
  }
  const rawIds = c.documentMediaIds
  if (!Array.isArray(rawIds)) return []
  return rawIds
    .filter((x): x is string => typeof x === 'string' && x.trim().length > 0)
    .map((mediaId) => ({ mediaId, documentName: '' }))
}

/**
 * Résout les IDs média du module `DocumentsListModule` en URLs de téléchargement + libellés pour le rendu web.
 */
function formatFundingAprDisplay(supplyAprPct: number, locale: Locale): string {
  if (!Number.isFinite(supplyAprPct)) return ''
  if (locale === 'fr') {
    return `${supplyAprPct.toFixed(2).replace('.', ',')}%`
  }
  return `${supplyAprPct.toFixed(2)}%`
}

/**
 * Remplit `content._resolved` pour chaque `FundingModule` :
 * - `auto_product` : métriques depuis `lending` (pas de copie en JSON éditable).
 * - `manual` : valeurs depuis `content.manual.*` (builder).
 * Si `auto_product` et pas de lending → `_resolved: null` (le module ne s’affiche pas).
 */
function enrichFundingVaultModules(
  modules: VaultModulePublic[],
  lending: LendingSnapshot | null,
  locale: Locale,
): VaultModulePublic[] {
  return modules.map((m) => {
    if (m.type !== 'FundingModule') return m
    const c = m.content
    const mode = c.displayMode === 'manual' ? 'manual' : 'auto_product'

    if (mode === 'auto_product') {
      if (!lending) {
        return { ...m, content: { ...c, _resolved: null } }
      }
      return {
        ...m,
        content: {
          ...c,
          _resolved: {
            progressPct: lending.progressPct,
            rateDisplay: formatFundingAprDisplay(lending.supplyAprPct, locale),
            totalDisplay: lending.target,
          },
        },
      }
    }

    const man = asRecord(c.manual) ?? {}
    const progressRaw = man.progressPct
    const progressPct =
      typeof progressRaw === 'number'
        ? progressRaw
        : typeof progressRaw === 'string'
          ? Number.parseFloat(progressRaw)
          : NaN
    const rateDisplay = typeof man?.rateDisplay === 'string' ? man.rateDisplay : ''
    const totalDisplay = typeof man?.totalDisplay === 'string' ? man.totalDisplay : ''

    return {
      ...m,
      content: {
        ...c,
        _resolved: {
          progressPct: Number.isFinite(progressPct)
            ? Math.min(100, Math.max(0, progressPct))
            : 0,
          rateDisplay,
          totalDisplay,
        },
      },
    }
  })
}

async function enrichDocumentsListModules(
  prisma: PrismaClient,
  modules: VaultModulePublic[],
  publicOrigin?: string | null,
): Promise<VaultModulePublic[]> {
  const out: VaultModulePublic[] = []
  for (const m of modules) {
    if (m.type !== 'DocumentsListModule') {
      out.push(m)
      continue
    }
    const c = m.content
    const entries = parseDocumentEntriesFromVaultContent(c)
    const documentMediaIds = entries.map((e) => e.mediaId)
    const documentItems: Array<{
      mediaId: string
      downloadUrl: string
      displayName: string
      dateLabel: string
    }> = []
    for (const entry of entries) {
      const { mediaId, documentName } = entry
      const url = await resolveMediaUrl(prisma, mediaId, { publicOrigin: publicOrigin ?? undefined })
      if (!url) continue
      const row = await prisma.media.findUnique({
        where: { id: mediaId },
        select: { filename: true, createdAt: true },
      })
      if (!row) continue
      const custom = documentName.trim()
      documentItems.push({
        mediaId,
        downloadUrl: url,
        displayName: custom.length > 0 ? custom : row.filename,
        dateLabel: formatDocumentListDateLabel(row.createdAt),
      })
    }
    out.push({
      ...m,
      content: {
        ...c,
        documentMediaIds,
        documentItems,
      },
    })
  }
  return out
}

/**
 * Carrousels / vidéos / documents : URLs résolues pour le client mobile (requête BFF avec `publicOrigin`).
 */
export async function enrichVaultModulesForMobileClient(
  prisma: PrismaClient,
  modules: VaultModulePublic[],
  publicOrigin: string | null | undefined,
): Promise<VaultModulePublic[]> {
  let m = await enrichTitlePageModuleImages(prisma, modules, publicOrigin)
  m = await enrichMediaCarouselModules(prisma, m, publicOrigin)
  m = await enrichVideoBlockArticleModules(prisma, m, publicOrigin)
  m = await enrichDocumentsListModules(prisma, m, publicOrigin)
  return m
}

export type GetExclusiveOfferVaultPayloadOptions = {
  /**
   * Aperçu authentifié CMS : ignore visibilité / statut commercial de l’offre exclusive,
   * et résout le JSON du vault en **priorisant le DRAFT** (brouillon enregistré) plutôt que le publié.
   * À n’activer que si `getSessionFromCookie()` a réussi pour la même requête.
   */
  allowExclusiveOfferAdminPreview?: boolean
}

/**
 * Charge le payload pour une page `template = vault_builder` (offre / landing Vault).
 * Retourne `null` si page absente, pas de contenu publié (ou brouillon pour l’aperçu admin), ou offre exclusive non visible côté public.
 *
 * En **`next dev`** (`NODE_ENV=development`), les contrôles visibilité / statut commercial sur les offres exclusives sont **désactivés** : l’URL sans `?adminDraftPreview=` affiche la même page qu’en aperçu iframe (en production, sans aperçu admin, seules les offres **PUBLIC** et **PUBLISHED** passent — et la galerie peut inclure des brouillons en dev si `ARQUANTIX_DEV_SHOW_DRAFT_EXCLUSIVE_OFFERS=true`).
 */
export async function getExclusiveOfferVaultPayload(
  pageSlug: string,
  localeInput: string,
  options?: GetExclusiveOfferVaultPayloadOptions,
): Promise<ExclusiveOfferVaultPayload | null> {
  const locale = getLocaleOrDefault(localeInput)

  const page = await prisma.page.findUnique({
    where: { slug: pageSlug },
    include: {
      sections: {
        where: { key: VAULT_SECTION_KEY },
        include: {
          contents: true,
        },
        take: 1,
      },
    },
  })

  if (!page || page.template !== VAULT_BUILDER_TEMPLATE) {
    return null
  }

  if (page.urlPath === '/') {
    return null
  }

  const section = page.sections[0]
  if (!section) {
    return null
  }

  const content = resolveVaultSectionContentForExclusiveOfferPayload(section.contents, {
    requestedLocale: locale,
    defaultLocale,
    previewDraftFirst: options?.allowExclusiveOfferAdminPreview === true,
  })

  if (!content) {
    return null
  }

  const packaged = await prisma.packagedProduct.findUnique({
    where: { pageId: page.id },
    include: { lendingPoolProduct: true },
  })

  if (packaged && packaged.productType === PackagedProductType.EXCLUSIVE_OFFER) {
    if (!options?.allowExclusiveOfferAdminPreview) {
      const skipPublicProductGate = process.env.NODE_ENV === 'development'
      if (!skipPublicProductGate) {
        if (packaged.visibility !== PackagedVisibility.PUBLIC) {
          return null
        }
        const okStatus =
          packaged.commercialStatus === PackagedCommercialStatus.PUBLISHED ||
          (devShowDraftExclusiveOffers &&
            packaged.commercialStatus === PackagedCommercialStatus.DRAFT)
        if (!okStatus) {
          return null
        }
      }
    }
  }

  const raw = asRecord(content.data)
  if (!raw) {
    return null
  }

  const { modules: modulesNormalized, warnings: normalizeWarnings } =
    normalizeVaultModulesFromSectionData(raw, page.slug)
  if (process.env.NODE_ENV === 'development' && normalizeWarnings.length > 0) {
    console.warn(`[normalizeVaultModules] page=${page.slug}`, normalizeWarnings)
  }

  let modulesWorking = modulesNormalized as VaultModulePublic[]

  const vaultPageSlugSet = new Set<string>()
  if (typeof page.slug === 'string' && page.slug.trim()) {
    vaultPageSlugSet.add(page.slug.trim().toLowerCase())
  }
  if (typeof packaged?.slug === 'string' && packaged.slug.trim()) {
    vaultPageSlugSet.add(packaged.slug.trim().toLowerCase())
  }

  const relatedArticlePreviews =
    vaultPageSlugSet.size === 0
      ? []
      : await getArticlesLinkedToVaultPageSlugs(
          {
            vaultPageSlugs: [...vaultPageSlugSet],
            locale,
            limit: 48,
          },
          calculateReadingTime,
        )

  if (relatedArticlePreviews.length > 0) {
    const ensured = await ensureBlogALaUneFromDraftWhenRelatedNews(prisma, {
      sectionContents: section.contents,
      vaultData: { ...raw, modules: modulesWorking },
      relatedArticleCount: relatedArticlePreviews.length,
      requestedLocale: locale,
      defaultLocale,
      publicOrigin: null,
      contextSlug: page.slug,
      mergeDraftBlogOnly: true,
    })
    if (ensured?.modules && Array.isArray(ensured.modules)) {
      modulesWorking = ensured.modules as VaultModulePublic[]
    }
  }

  let modules = await enrichMediaCarouselModules(prisma, modulesWorking)
  modules = await enrichVideoBlockArticleModules(prisma, modules)
  modules = await enrichDocumentsListModules(prisma, modules)
  modules = enrichBlogAlaUneVaultModulesForWeb(modules, locale, relatedArticlePreviews)

  /** Image hero : `headerMediaId` (JSON racine vault) > URL `TitlePage.content.imageUrl` si présente. */
  const headerMediaId =
    typeof raw.headerMediaId === 'string' && raw.headerMediaId.length > 0
      ? raw.headerMediaId
      : null
  let headerImageUrl = headerMediaId ? await resolveMediaUrl(prisma, headerMediaId) : null
  if (!headerImageUrl && modules.length > 0) {
    const title = modules.find((x) => x.type === 'TitlePage')
    const c = title?.content
    if (c && typeof c.imageUrl === 'string' && c.imageUrl.length > 0) {
      headerImageUrl = c.imageUrl
    }
  }

  let lending: LendingSnapshot | null = null
  const lpp = packaged?.lendingPoolProduct
  if (lpp) {
    const supplyAprPct = Number(lpp.supplyAprBps) / 100
    const raised = Number(lpp.currentRaised)
    const target = Number(lpp.targetSize)
    const progressPct = target > 0 ? Math.min(100, (raised / target) * 100) : 0
    lending = {
      asset: lpp.asset,
      supplyAprPct,
      raised: Number.isFinite(raised) ? raised.toLocaleString(locale) : '—',
      target: Number.isFinite(target) ? target.toLocaleString(locale) : '—',
      progressPct,
      status: (lpp.status || '').replace(/_/g, ' '),
      minTicket: lpp.minTicket != null ? String(lpp.minTicket) : null,
      maxTicket: lpp.maxTicket != null ? String(lpp.maxTicket) : null,
      keyInformationRows: buildKeyInformationRows(lpp, locale),
    }
  }

  modules = enrichFundingVaultModules(modules, lending, locale)

  /** Titre/sous-titre de repli hero : PageI18n (locale) → PageI18n (défaut) → Page (voir `resolvePageSeoFields`). */
  const seo = await resolvePageSeoFields(page.id, locale)
  const pageTitle = seo.title?.trim() || page.slug
  const pageDescription = seo.description?.trim() || null
  const { heroTitle, heroSubtitle, heroTags, contentModules, heroTitleSource } =
    splitTitlePageHeroFromModules(pageTitle, pageDescription, modules)

  return {
    pageSlug: page.slug,
    pageTitle,
    pageDescription,
    urlPath: page.urlPath,
    locale,
    headerImageUrl,
    packagedProductId: packaged?.id ?? null,
    productType: packaged?.productType ?? null,
    lending,
    heroTitle,
    heroSubtitle,
    tagPills: [],
    heroTags,
    heroTitleSource,
    contentModules,
    modules: contentModules,
  }
}
