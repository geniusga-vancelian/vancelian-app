/**
 * Liste les produits Portfolio Engine pour le Vault Builder admin.
 *
 * - Les **crypto bundles** (y compris brouillons / non publiés) viennent de
 *   `GET /api/portfolio-engine/admin/bundles` — nécessaire car `product-catalog`
 *   filtre `is_public == true` et masquait les bundles créés en privé.
 * - Les **autres** types de produits (hors crypto_bundle) restent issus du
 *   catalogue public pour ne pas les perdre dans la colonne « autres produits ».
 */
import { NextRequest, NextResponse } from 'next/server'
import { getSessionFromCookie } from '@/lib/auth'
import { buildBackendUrl } from '@/lib/backend'

/** Évite le Data Cache Next.js 14 sur les fetch serveur → réponses PE obsolètes / vides. */
export const dynamic = 'force-dynamic'

const ADMIN_HEADERS = {
  'X-Actor-Type': 'admin',
  'X-Actor-Roles': 'admin',
} as const

type BundleListJson = {
  items?: Array<{
    id: string
    product_code: string
    name: string
    product_type: string
    is_public: boolean
    allocation_summary?: Array<{ asset_symbol: string; target_weight: string | number }>
    available_rebalance_frequencies?: string[]
  }>
  total?: number
}

type CatalogJson = {
  items?: Array<{
    id: string
    product_code: string
    name: string
    description?: string | null
    product_type: string
    allocations?: Array<{ asset_symbol: string; target_weight: string | number }>
    available_rebalance_frequencies?: string[]
    is_public?: boolean
  }>
  total?: number
}

function mapBundleItem(b: NonNullable<BundleListJson['items']>[number]) {
  return {
    id: b.id,
    product_code: b.product_code,
    name: b.name,
    description: null as string | null,
    product_type: b.product_type,
    allocations: (b.allocation_summary ?? []).map((a) => ({
      asset_symbol: a.asset_symbol,
      target_weight: String(a.target_weight),
    })),
    available_rebalance_frequencies: b.available_rebalance_frequencies ?? [],
    is_public: b.is_public,
  }
}

function mapCatalogItem(
  c: NonNullable<CatalogJson['items']>[number],
) {
  return {
    id: c.id,
    product_code: c.product_code,
    name: c.name,
    description: c.description ?? null,
    product_type: c.product_type,
    allocations: (c.allocations ?? []).map((a) => ({
      asset_symbol: a.asset_symbol,
      target_weight: String(a.target_weight),
    })),
    available_rebalance_frequencies: c.available_rebalance_frequencies ?? [],
    is_public: c.is_public ?? true,
  }
}

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const productTypeFilter = searchParams.get('product_type') ?? undefined

    const bundlesUrl = new URL(buildBackendUrl('/api/portfolio-engine/admin/bundles'))
    bundlesUrl.searchParams.set('limit', '200')

    const bundleRes = await fetch(bundlesUrl.toString(), {
      headers: ADMIN_HEADERS,
      signal: AbortSignal.timeout(15000),
      cache: 'no-store',
    })

    if (!bundleRes.ok) {
      const body = await bundleRes.text()
      return NextResponse.json(
        { error: 'Backend request failed (bundles)', detail: body },
        { status: bundleRes.status },
      )
    }

    const bundleJson = (await bundleRes.json()) as BundleListJson
    let items = (bundleJson.items ?? []).map(mapBundleItem)
    if (productTypeFilter) {
      items = items.filter((p) => p.product_type === productTypeFilter)
    }

    const bundleCodes = new Set(items.map((p) => p.product_code))

    const catalogUrl = new URL(buildBackendUrl('/api/portfolio-engine/product-catalog'))
    if (productTypeFilter) catalogUrl.searchParams.set('product_type', productTypeFilter)

    const catalogRes = await fetch(catalogUrl.toString(), {
      signal: AbortSignal.timeout(15000),
      cache: 'no-store',
    })
    if (catalogRes.ok) {
      const catalogJson = (await catalogRes.json()) as CatalogJson
      const extras = (catalogJson.items ?? []).filter(
        (c) =>
          c.product_type !== 'crypto_bundle' &&
          !bundleCodes.has(c.product_code),
      )
      items = [...items, ...extras.map(mapCatalogItem)]
    }

    if (process.env.NODE_ENV === 'development') {
      console.debug('[BFF GET /api/admin/portfolio-engine/products]', {
        bundleUrl: bundlesUrl.toString(),
        itemCount: items.length,
        productCodes: items.map((p) => p.product_code),
      })
    }

    return NextResponse.json({ items, total: items.length })
  } catch (error: unknown) {
    console.error('Portfolio Engine products fetch error:', error)
    return NextResponse.json(
      { error: 'Internal server error', detail: String(error) },
      { status: 500 },
    )
  }
}
