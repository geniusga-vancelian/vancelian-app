/**
 * Helpers pour le Product Registry — lecture contenu Vault Builder + mapping API.
 */
import type {
  PackagedCommercialStatus,
  PackagedEngineType,
  PackagedProductType,
  PackagedVisibility,
} from '@prisma/client'

import { ContentStatus } from '@prisma/client'

import { getPresignedUrl } from '@/lib/storage/storageClient'
import type { PrismaClient } from '@prisma/client'

export const VAULT_BUILDER_TEMPLATE = 'vault_builder'
export const VAULT_SECTION_KEY = 'vault_builder_v1'

/** Locale par défaut pour section_contents (aligné vaults/route.ts). */
export const CATALOG_DEFAULT_LOCALE = 'fr'

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
): Promise<string | null> {
  if (!mediaId) return null
  const media = await prisma.media.findUnique({ where: { id: mediaId } })
  if (!media) return null
  try {
    return await getPresignedUrl(media.key, 3600)
  } catch {
    return media.url
  }
}

/**
 * Résout cover + titre + sous-titre depuis page + contenu section publié.
 */
export async function resolveVaultPresentation(args: {
  prisma: PrismaClient
  pageId: string
  locale: string
}): Promise<{ title: string; subtitle: string | null; coverUrl: string | null }> {
  const { prisma, pageId, locale } = args
  const page = await prisma.page.findUnique({
    where: { id: pageId },
    include: {
      sections: {
        where: { key: VAULT_SECTION_KEY },
        include: {
          contents: {
            where: {
              locale,
              status: ContentStatus.PUBLISHED,
            },
            take: 1,
          },
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

  const content = page?.sections[0]?.contents[0]
  const data = content?.data as Record<string, unknown> | null | undefined
  const headerMediaId =
    data && typeof data.headerMediaId === 'string' ? data.headerMediaId : null
  const coverFromMedia = headerMediaId
    ? await resolveMediaUrl(prisma, headerMediaId)
    : null
  const coverFromModules = extractCoverFromVaultData(data)
  const coverUrl = coverFromMedia ?? coverFromModules

  const modules = data && Array.isArray(data.modules) ? data.modules : []
  for (const m of modules) {
    if (m == null || typeof m !== 'object') continue
    const mod = m as Record<string, unknown>
    if (mod.type === 'TitlePage' || mod.module === 'TitlePage') {
      const c = mod.content as Record<string, unknown> | undefined
      if (c && typeof c.subtitle === 'string' && c.subtitle.trim()) {
        subtitle = c.subtitle.trim()
        break
      }
    }
  }

  return { title, subtitle, coverUrl }
}

export async function fetchLendingEngineSnapshot(
  productUuid: string,
): Promise<Record<string, unknown> | null> {
  const base =
    process.env.BACKEND_API_URL?.replace(/\/$/, '') ||
    process.env.MARKET_DATA_API_URL?.replace(/\/$/, '') ||
    ''
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
