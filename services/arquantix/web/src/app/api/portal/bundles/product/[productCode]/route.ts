import { NextRequest, NextResponse } from 'next/server'

import {
  findTitlePageModule,
  parseVaultModules,
} from '@/lib/portal/bundleProductFormat'
import type {
  PortalBundleAllocationRow,
  PortalBundleProductDetailPayload,
} from '@/lib/portal/bundleProductTypes'
import { portalUpstreamFetch, resolvePortalBffOrigin } from '@/lib/portal/portalUpstream'
import { readPortalAccessToken } from '@/lib/portal/portalSession'

type CatalogRow = {
  id?: string
  product_code?: string
  productCode?: string
  name?: string
  description?: string | null
  risk_label?: string | null
  riskLabel?: string | null
  portfolio_id?: string | null
  portfolioId?: string | null
  entry_asset_default?: string | null
  entryAssetDefault?: string | null
  entry_assets_allowed?: string[] | null
  entryAssetsAllowed?: string[] | null
  allocations?: Array<{
    asset_symbol?: string
    assetSymbol?: string
    name?: string
    target_weight?: number
    targetWeight?: number
  }>
}

function parseAllocations(item: CatalogRow): PortalBundleAllocationRow[] {
  const raw = item.allocations
  if (!Array.isArray(raw)) return []
  return raw
    .map((row) => {
      const assetSymbol = String(row.asset_symbol ?? row.assetSymbol ?? '')
        .trim()
        .toUpperCase()
      const name = String(row.name ?? assetSymbol).trim()
      const targetWeight = Number(row.target_weight ?? row.targetWeight)
      if (!assetSymbol || !Number.isFinite(targetWeight)) return null
      return { assetSymbol, name, targetWeight }
    })
    .filter((r): r is PortalBundleAllocationRow => r != null)
}

export async function GET(
  request: NextRequest,
  { params }: { params: { productCode: string } },
) {
  const token = await readPortalAccessToken()
  if (!token) {
    return NextResponse.json({ error: 'unauthorized' }, { status: 401 })
  }

  const productCode = (params.productCode ?? '').trim().toUpperCase()
  if (!productCode) {
    return NextResponse.json({ error: 'invalid_product_code' }, { status: 400 })
  }

  const bffOrigin = resolvePortalBffOrigin(request.nextUrl.origin)

  const [configRes, catalogRes] = await Promise.all([
    fetch(
      `${bffOrigin}/api/mobile/flutter/portfolio-products/${encodeURIComponent(productCode)}`,
      { cache: 'no-store', signal: AbortSignal.timeout(15000) },
    ),
    portalUpstreamFetch('/api/app/bundle/catalog'),
  ])

  if (!configRes.ok) {
    return NextResponse.json({ error: 'bundle_config_unavailable' }, { status: 502 })
  }

  const configJson = (await configRes.json().catch(() => null)) as {
    vault?: {
      headerMediaUrl?: string | null
      detailMediaUrl?: string | null
      modules?: unknown
    }
  } | null

  const vault = configJson?.vault
  const modules = parseVaultModules(vault?.modules)
  const titlePage = findTitlePageModule(modules)
  const titleContent = titlePage?.content ?? {}

  let catalogItem: CatalogRow | null = null
  if (catalogRes.ok) {
    const catalogJson = await catalogRes.json().catch(() => null)
    const items =
      (catalogJson as { items?: CatalogRow[] })?.items ??
      (catalogJson as { products?: CatalogRow[] })?.products ??
      []
    if (Array.isArray(items)) {
      catalogItem =
        items.find(
          (row) =>
            String(row.product_code ?? row.productCode ?? '')
              .trim()
              .toUpperCase() === productCode,
        ) ?? null
    }
  }

  const title =
    (typeof titleContent.title === 'string' ? titleContent.title.trim() : '') ||
    catalogItem?.name?.trim() ||
    productCode
  const subtitle =
    (typeof titleContent.subtitle === 'string' ? titleContent.subtitle.trim() : '') ||
    catalogItem?.description?.trim() ||
    ''

  const entryAllowedRaw =
    catalogItem?.entry_assets_allowed ?? catalogItem?.entryAssetsAllowed
  const entryAssetsAllowed = Array.isArray(entryAllowedRaw)
    ? entryAllowedRaw.map((a) => String(a).trim().toUpperCase()).filter(Boolean)
    : []

  const payload: PortalBundleProductDetailPayload = {
    productCode,
    title,
    subtitle,
    headerMediaUrl: vault?.headerMediaUrl?.trim() || null,
    detailMediaUrl: vault?.detailMediaUrl?.trim() || null,
    portfolioId:
      (catalogItem?.portfolio_id ?? catalogItem?.portfolioId)?.trim() || null,
    productId: catalogItem?.id?.trim() || null,
    entryAssetDefault:
      (catalogItem?.entry_asset_default ?? catalogItem?.entryAssetDefault)
        ?.trim()
        .toUpperCase() || null,
    entryAssetsAllowed,
    riskLabel: (catalogItem?.risk_label ?? catalogItem?.riskLabel)?.toString?.() ?? null,
    modules,
    allocations: catalogItem ? parseAllocations(catalogItem) : [],
  }

  return NextResponse.json(payload)
}
