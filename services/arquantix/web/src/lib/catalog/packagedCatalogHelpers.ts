/**
 * Helpers pour le Product Registry — lecture contenu Vault Builder + mapping API.
 */
import type {
  PackagedCommercialStatus,
  PackagedEngineType,
  PackagedProductType,
  PackagedVisibility,
} from '@prisma/client'

import { getBackendBaseUrl } from '@/lib/backend'
import { getSiteOrigin } from '@/lib/metadata/siteOrigin'
import { resolveVaultSectionContentForCatalog } from '@/lib/cms/resolveVaultSectionContent'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import type { PrismaClient } from '@prisma/client'

/**
 * Le client mobile (Flutter) ne peut pas charger une URL relative (`/media/...`) :
 * il faut une URL absolue. Utilise l’origine de la requête API (ex. `http://192.168.x.x:3000`)
 * quand le média en base est stocké en chemin relatif ou si le fallback Prisma renvoie une URL sans host.
 */
export function absolutizeMediaUrlForApiClient(
  url: string | null | undefined,
  requestOrigin: string | null | undefined,
): string | null {
  if (url == null) return null
  const s = String(url).trim()
  if (!s) return null
  if (/^https?:\/\//i.test(s)) return s
  if (s.startsWith('//')) return `https:${s}`
  const base = (requestOrigin && requestOrigin.trim()) || getSiteOrigin()
  const path = s.startsWith('/') ? s : `/${s}`
  if (!base) {
    return `http://127.0.0.1:3000${path}`
  }
  return `${base.replace(/\/$/, '')}${path}`
}

export const VAULT_BUILDER_TEMPLATE = 'vault_builder'
export const VAULT_SECTION_KEY = 'vault_builder_v1'

/** Page CMS gabarit détail offre exclusive (slug réservé — pas une offre publique). */
export const EXCLUSIVE_OFFER_GABARIT_SLUG = 'exclusive-offer'
export const EXCLUSIVE_OFFER_GABARIT_TEMPLATE = 'exclusive_offer'

/** Locale par défaut pour section_contents (contenu CMS unique EN pour l'instant). */
export const CATALOG_DEFAULT_LOCALE = 'en'

export function parseProductTypeParam(
  raw: string | null,
): PackagedProductType | undefined {
  if (!raw?.trim()) return undefined
  const m: Record<string, PackagedProductType> = {
    vault_simple: 'VAULT_SIMPLE',
    exclusive_offer: 'EXCLUSIVE_OFFER',
    managed_mandate: 'MANAGED_MANDATE',
    crypto_bundle: 'CRYPTO_BUNDLE',
  }
  return m[raw.trim().toLowerCase()]
}

export function parseVisibilityParam(
  raw: string | null,
): PackagedVisibility | undefined {
  if (!raw?.trim()) return undefined
  const m: Record<string, PackagedVisibility> = {
    public: 'PUBLIC',
    private: 'PRIVATE',
    hidden: 'HIDDEN',
  }
  return m[raw.trim().toLowerCase()]
}

export function parseCommercialStatusParam(
  raw: string | null,
): PackagedCommercialStatus | undefined {
  if (!raw?.trim()) return undefined
  const m: Record<string, PackagedCommercialStatus> = {
    draft: 'DRAFT',
    published: 'PUBLISHED',
    archived: 'ARCHIVED',
  }
  return m[raw.trim().toLowerCase()]
}

export function productTypeToApi(t: PackagedProductType): string {
  switch (t) {
    case 'VAULT_SIMPLE':
      return 'vault_simple'
    case 'EXCLUSIVE_OFFER':
      return 'exclusive_offer'
    case 'MANAGED_MANDATE':
      return 'managed_mandate'
    case 'CRYPTO_BUNDLE':
      return 'crypto_bundle'
    default:
      return String(t).toLowerCase()
  }
}

export function engineTypeToApi(t: PackagedEngineType | null): string | null {
  if (!t) return null
  switch (t) {
    case 'LENDING':
      return 'lending'
    case 'BUNDLE':
      return 'bundle'
    case 'MANAGED_PORTFOLIO':
      return 'managed_portfolio'
    case 'VAULT_ENGINE':
      return 'vault_engine'
    default:
      return String(t).toLowerCase()
  }
}

export function visibilityToApi(v: PackagedVisibility): string {
  switch (v) {
    case 'PUBLIC':
      return 'public'
    case 'PRIVATE':
      return 'private'
    case 'HIDDEN':
      return 'hidden'
    default:
      return 'public'
  }
}

export function commercialStatusToApi(s: PackagedCommercialStatus): string {
  switch (s) {
    case 'DRAFT':
      return 'draft'
    case 'PUBLISHED':
      return 'published'
    case 'ARCHIVED':
      return 'archived'
    default:
      return 'draft'
  }
}

/** Extrait une URL de couverture depuis le JSON module vault (comme vaults/route). */
export function extractCoverFromVaultData(data: unknown): string | null {
  if (data == null || typeof data !== 'object') return null
  const obj = data as Record<string, unknown>
  const modules = obj.modules
  if (!Array.isArray(modules)) return null
  for (const m of modules) {
    if (m == null || typeof m !== 'object') continue
    const content = (m as Record<string, unknown>).content
    if (content == null || typeof content !== 'object') continue
    const c = content as Record<string, unknown>
    if (typeof c.imageUrl === 'string' && c.imageUrl.length > 0) return c.imageUrl
    if (Array.isArray(c.items) && c.items.length > 0) {
      const first = c.items[0]
      if (
        first != null &&
        typeof first === 'object' &&
        typeof (first as Record<string, unknown>).imageUrl === 'string'
      ) {
        return (first as Record<string, unknown>).imageUrl as string
      }
    }
  }
  return null
}

export async function resolveMediaUrl(
  prisma: PrismaClient,
  mediaId: string | null | undefined,
  opts?: { publicOrigin?: string | null },
): Promise<string | null> {
  if (!mediaId) return null
  const media = await prisma.media.findUnique({ where: { id: mediaId } })
  if (!media) return null
  let out: string | null = null
  try {
    out = await getPresignedUrl(media.key, 3600)
  } catch {
    out = media.url
  }
  return absolutizeMediaUrlForApiClient(out, opts?.publicOrigin ?? null)
}

/**
 * Cover catalogue / mobile : aligné sur la logique page offre (header racine + modules),
 * avec résolution des IDs médiathèque dans TitlePage et carrousels.
 */
async function resolveCoverFromVaultSectionData(
  prisma: PrismaClient,
  data: Record<string, unknown> | null | undefined,
  publicOrigin: string | null | undefined,
): Promise<string | null> {
  if (!data) return null

  const headerRaw = data.headerMediaId
  const headerMediaId =
    typeof headerRaw === 'string' && headerRaw.trim().length > 0 ? headerRaw.trim() : null
  if (headerMediaId) {
    const u = await resolveMediaUrl(prisma, headerMediaId, { publicOrigin })
    if (u) return u
  }

  const fromSync = extractCoverFromVaultData(data)
  if (fromSync) {
    return absolutizeMediaUrlForApiClient(fromSync, publicOrigin ?? null)
  }

  const modules = Array.isArray(data.modules) ? data.modules : []
  for (const raw of modules) {
    if (raw == null || typeof raw !== 'object') continue
    const mod = raw as Record<string, unknown>
    if (mod.enabled === false) continue
    const typ = String(mod.type ?? mod.module ?? '')
    const content = mod.content
    if (content == null || typeof content !== 'object' || Array.isArray(content)) continue
    const c = content as Record<string, unknown>

    if (typ === 'TitlePage') {
      const singleId =
        typeof c.imageMediaId === 'string' && c.imageMediaId.trim().length > 0
          ? c.imageMediaId.trim()
          : null
      if (singleId) {
        const u = await resolveMediaUrl(prisma, singleId, { publicOrigin })
        if (u) return u
      }
      const ids = c.imageMediaIds
      if (Array.isArray(ids)) {
        for (const id of ids) {
          if (typeof id === 'string' && id.trim().length > 0) {
            const u = await resolveMediaUrl(prisma, id.trim(), { publicOrigin })
            if (u) return u
            break
          }
        }
      }
    }

    const mediaCarouselIds = c.imageMediaIds
    if (Array.isArray(mediaCarouselIds) && mediaCarouselIds.length > 0 && typ === 'MediaImageCarouselModule') {
      const first = mediaCarouselIds[0]
      if (typeof first === 'string' && first.trim().length > 0) {
        const u = await resolveMediaUrl(prisma, first.trim(), { publicOrigin })
        if (u) return u
      }
    }
  }

  return null
}

/**
 * Résout cover + titre + sous-titre depuis page + contenu section vault (catalogue / mobile).
 *
 * @param publicOrigin — ex. `new NextRequest(...).nextUrl.origin` pour absolutiser les URLs
 *                       relatives destinées au client mobile (`Config.apiBaseUrl`).
 */
export async function resolveVaultPresentation(args: {
  prisma: PrismaClient
  pageId: string
  locale: string
  /** Origine HTTP du client qui consomme le JSON (BFF mobile). */
  publicOrigin?: string | null
}): Promise<{ title: string; subtitle: string | null; coverUrl: string | null }> {
  const { prisma, pageId } = args
  const publicOrigin = args.publicOrigin ?? null
  const requestedLocale = (args.locale || '').trim() || CATALOG_DEFAULT_LOCALE
  // Fallback locale : on charge **toutes** les locales du SectionContent
  // pour permettre à `resolveVaultSectionContentForCatalog` de retomber sur
  // EN (ou n’importe quelle locale) quand l’EO n’est saisie qu’en EN.
  // Sinon Flutter (locale=fr) recevait `vault.data = null` → cover, sous-titre
  // et modules absents (cf. articles non traduits).
  const page = await prisma.page.findUnique({
    where: { id: pageId },
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

  const title = page?.title?.trim() || page?.slug || ''
  let subtitle: string | null =
    typeof page?.description === 'string' && page.description.trim()
      ? page.description.trim()
      : null

  const sectionContents = page?.sections[0]?.contents ?? []
  const effectiveContent = resolveVaultSectionContentForCatalog(sectionContents, {
    requestedLocale,
    defaultLocale: CATALOG_DEFAULT_LOCALE,
  })
  const effectiveData = effectiveContent?.data as Record<string, unknown> | null | undefined

  const preferredRow = sectionContents.find((c) => c.locale === requestedLocale) ?? null
  const defaultRow =
    sectionContents.find((c) => c.locale === CATALOG_DEFAULT_LOCALE) ?? null
  const preferredData = preferredRow?.data as Record<string, unknown> | null | undefined
  const defaultData = defaultRow?.data as Record<string, unknown> | null | undefined

  /**
   * Cover : priorité données « ligne effective » (pub/brouillon + repli brouillon si pub vide),
   * puis même logique SEO inter-locales qu’avant (carte catalogue).
   */
  const coverUrl =
    (await resolveCoverFromVaultSectionData(prisma, effectiveData, publicOrigin)) ??
    (await resolveCoverFromVaultSectionData(prisma, preferredData, publicOrigin)) ??
    (requestedLocale !== CATALOG_DEFAULT_LOCALE
      ? await resolveCoverFromVaultSectionData(prisma, defaultData, publicOrigin)
      : null)

  const pickSubtitleFromModules = (data: Record<string, unknown> | null | undefined) => {
    const modules = data && Array.isArray(data.modules) ? data.modules : []
    for (const m of modules) {
      if (m == null || typeof m !== 'object') continue
      const mod = m as Record<string, unknown>
      if (mod.type === 'TitlePage' || mod.module === 'TitlePage') {
        const c = mod.content as Record<string, unknown> | undefined
        if (c && typeof c.subtitle === 'string' && c.subtitle.trim()) {
          return c.subtitle.trim()
        }
      }
    }
    return null
  }

  subtitle =
    pickSubtitleFromModules(effectiveData) ??
    pickSubtitleFromModules(preferredData) ??
    (requestedLocale !== CATALOG_DEFAULT_LOCALE ? pickSubtitleFromModules(defaultData) : null) ??
    subtitle

  return { title, subtitle, coverUrl }
}

export async function fetchLendingEngineSnapshot(
  productUuid: string,
): Promise<Record<string, unknown> | null> {
  const base = getBackendBaseUrl()
  if (!base) return null
  try {
    const res = await fetch(`${base}/api/lending/products/${productUuid}`, {
      next: { revalidate: 15 },
      signal: AbortSignal.timeout(8000),
    })
    if (!res.ok) return null
    const json = (await res.json()) as Record<string, unknown>
    return json
  } catch {
    return null
  }
}
