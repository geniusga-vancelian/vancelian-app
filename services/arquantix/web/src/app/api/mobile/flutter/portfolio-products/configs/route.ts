import { NextResponse } from 'next/server'

import { buildBackendUrl } from '@/lib/backend'
import { prisma } from '@/lib/prisma'
import { getPresignedUrl } from '@/lib/storage/storageClient'

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

async function fetchCatalogMap(): Promise<Map<string, string>> {
  try {
    const res = await fetch(buildBackendUrl('/api/portfolio-engine/product-catalog'), {
      signal: AbortSignal.timeout(5000),
      cache: 'no-store',
    })
    if (!res.ok) return new Map()
    const data = (await res.json()) as {
      items?: Array<{ id: string; product_code: string }>
    }
    const map = new Map<string, string>()
    for (const item of data.items ?? []) {
      map.set(item.product_code.toUpperCase(), item.id)
    }
    return map
  } catch {
    return new Map()
  }
}

async function fetchPerformance1d(productUuid: string): Promise<number | null> {
  try {
    const u = new URL(
      buildBackendUrl(`/api/portfolio-engine/products/${productUuid}/chart-history`),
    )
    u.searchParams.set('period', '1j')
    const res = await fetch(u.toString(), {
      signal: AbortSignal.timeout(10000),
      cache: 'no-store',
    })
    if (!res.ok) return null
    const data = (await res.json()) as { performance_pct?: number }
    return typeof data.performance_pct === 'number'
      ? Math.round(data.performance_pct * 100) / 100
      : null
  } catch {
    return null
  }
}

interface ModuleEntry {
  type?: string
  enabled?: boolean
  content?: Record<string, unknown>
}

function extractCardTitle(modules: unknown): string | null {
  if (!Array.isArray(modules)) return null
  const titleModule = modules.find(
    (m: ModuleEntry) => m?.type === 'TitlePage' && m?.enabled !== false,
  )
  if (!titleModule) return null
  const content = (titleModule as ModuleEntry).content
  if (!content || typeof content !== 'object') return null
  const title = (content as Record<string, unknown>).title
  return typeof title === 'string' && title.trim().length > 0 ? title.trim() : null
}

/**
 * GET /api/mobile/flutter/portfolio-products/configs
 *
 * Retourne la config d'affichage (image header + titre card) pour chaque produit
 * Portfolio Engine, indexée par product_code.
 *
 * Visibility is NOT filtered here: the FastAPI public catalog
 * (ProductDefinition.is_public) is the single source of truth.
 * Flutter intersects catalog items with these configs, so only
 * products present in both will be displayed.
 *
 * Réponse : { configs: { [productCode]: { headerMediaUrl, detailMediaUrl, cardTitle, sortOrder, performance1d } } }
 */
export async function GET() {
  try {
    const [rows, catalogMap] = await Promise.all([
      prisma.portfolioProductConfig.findMany({ orderBy: { sortOrder: 'asc' } }),
      fetchCatalogMap(),
    ])

    const entries = await Promise.all(
      rows.map(async (row) => {
        const productUuid = catalogMap.get(row.productCode.toUpperCase())
        const [headerMediaUrl, detailMediaUrl, performance1d] = await Promise.all([
          resolveMediaUrl(row.headerMediaId),
          resolveMediaUrl(row.detailMediaId),
          productUuid ? fetchPerformance1d(productUuid) : Promise.resolve(null),
        ])
        const cardTitle = extractCardTitle(row.modules)
        return [
          row.productCode,
          { headerMediaUrl, detailMediaUrl, cardTitle, sortOrder: row.sortOrder ?? 999, performance1d },
        ] as const
      }),
    )

    const configs: Record<
      string,
      {
        headerMediaUrl: string | null
        detailMediaUrl: string | null
        cardTitle: string | null
        sortOrder: number
        performance1d: number | null
      }
    > = Object.fromEntries(entries)

    return NextResponse.json({ configs })
  } catch (error) {
    console.error('[api/mobile/flutter/portfolio-products/configs]', error)
    return NextResponse.json({ configs: {} })
  }
}
