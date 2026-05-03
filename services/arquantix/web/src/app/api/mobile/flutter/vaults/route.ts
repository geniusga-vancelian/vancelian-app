import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { defaultLocale, getLocaleOrDefault } from '@/config/locales'
import { prisma } from '@/lib/prisma'
import { resolvePageSeoFields } from '@/lib/cms/resolvePageI18nMetadata'
import { resolveVaultSectionContent } from '@/lib/cms/resolveVaultSectionContent'
import { getPresignedUrl } from '@/lib/storage/storageClient'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'

async function resolveMediaUrl(mediaId: string | null | undefined): Promise<string | null> {
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
 * Extrait une URL d'image de couverture depuis les modules du config.
 */
function extractCoverImage(data: unknown): string | null {
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
      if (first != null && typeof first === 'object' && typeof (first as Record<string, unknown>).imageUrl === 'string') {
        return (first as Record<string, unknown>).imageUrl as string
      }
    }
  }
  return null
}

/**
 * GET /api/mobile/flutter/vaults?locale=fr
 * Liste publique des vaults pour l'app mobile.
 * Contenu éditorial : même résolution de locale que le détail (`resolveVaultSectionContent`, PUBLISHED uniquement).
 * Sans param `locale` : `defaultLocale` du site (comportement historique ~ FR).
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const requestedLocale = getLocaleOrDefault(searchParams.get('locale') ?? undefined)

    const pages = await prisma.page.findMany({
      where: { template: VAULT_TEMPLATE_DB },
      include: {
        sections: {
          where: { key: VAULT_SECTION_KEY },
          include: {
            contents: true,
          },
          take: 1,
        },
      },
      orderBy: { updatedAt: 'desc' },
    })

    const vaultsRaw = await Promise.all(
      pages.map(async (page) => {
        const contents = page.sections[0]?.contents ?? []
        const content = resolveVaultSectionContent(contents, {
          requestedLocale,
          defaultLocale,
          mode: ContentStatus.PUBLISHED,
        })
        const data = content?.data as Record<string, unknown> | null
        const headerMediaId = typeof data?.headerMediaId === 'string' ? data.headerMediaId : null
        const coverFromMedia = headerMediaId ? await resolveMediaUrl(headerMediaId) : null
        const coverFromModules = extractCoverImage(data)
        const coverImage =
          coverFromMedia ?? coverFromModules ?? `https://picsum.photos/seed/vault-${page.slug}/600/400`
        const investmentTypeSlug = typeof data?.investmentTypeSlug === 'string' ? data.investmentTypeSlug : null
        const sortOrder = typeof data?.sortOrder === 'number' ? data.sortOrder : 999
        const seo = await resolvePageSeoFields(page.id, requestedLocale)
        return {
          id: page.id,
          slug: page.slug,
          title: seo.title?.trim() || page.slug,
          description: seo.description ?? null,
          urlPath: page.urlPath,
          coverImage,
          investmentTypeSlug,
          sortOrder,
        }
      })
    )
    const vaults = vaultsRaw.sort((a, b) => {
      const catA = a.investmentTypeSlug ?? '__none__'
      const catB = b.investmentTypeSlug ?? '__none__'
      if (catA !== catB) return catA.localeCompare(catB)
      return a.sortOrder - b.sortOrder
    })

    return NextResponse.json({ vaults })
  } catch (error) {
    console.error('[api/mobile/flutter/vaults]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
