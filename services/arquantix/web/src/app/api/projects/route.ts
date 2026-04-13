import { NextRequest, NextResponse } from 'next/server'
import { getLatestProjects } from '@/lib/cms/projects'
import { getLocaleOrDefault, defaultLocale } from '@/config/locales'
import { getBackendBaseUrl } from '@/lib/backend'

/** Catégories d'investissement reconnues pour les tags (offres exclusives). */
const INVESTMENT_CATEGORIES = [
  'Real estate',
  'Energy',
  'Commodity',
  'Art',
  'Infrastructure',
  'Private equity',
  'Crypto',
] as const
const DEFAULT_CATEGORY = 'Real estate'

function normalizeInvestmentCategory(value: string | null | undefined): string {
  if (!value || !value.trim()) return DEFAULT_CATEGORY
  const normalized = value.trim()
  const found = INVESTMENT_CATEGORIES.find(
    (c) => c.toLowerCase() === normalized.toLowerCase()
  )
  return found ?? DEFAULT_CATEGORY
}

/**
 * Fetch lending data for projects from the Python backend.
 * Returns a map of project_id → lending enrichment data.
 * Silently returns empty on failure (backward compatible).
 */
async function fetchLendingDataForProjects(): Promise<Record<string, any>> {
  try {
    const market = process.env.MARKET_DATA_API_URL?.trim()
    const base = (market || getBackendBaseUrl()).replace(/\/$/, '')
    const res = await fetch(`${base}/api/lending/products/projects/lending-data`, {
      next: { revalidate: 30 },
    })
    if (!res.ok) return {}
    return await res.json()
  } catch {
    return {}
  }
}

/**
 * GET /api/projects — Liste des projets publiés (API publique pour l'app mobile Offres).
 * Query: locale (optionnel), limit (optionnel, défaut 50).
 *
 * Phase 2A.11: enrichit chaque projet avec les données lending si un
 * lending_pool_product est lié (apy, raised, target, progress, investorsCount).
 * Backward compatible — les champs lending sont null si pas de lien.
 *
 * Phase 8 — **Legacy pour les Exclusive Offers** : la source canonique app mobile est
 * `GET /api/mobile/flutter/catalog/products` (Product Registry). Cet endpoint reste
 * pour repli, contenus non migrés et autres consommateurs tant qu’ils existent.
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || defaultLocale
    const locale = getLocaleOrDefault(localeParam)
    const limit = Math.min(
      Math.max(parseInt(searchParams.get('limit') || '50', 10), 1),
      100
    )

    const [projects, lendingData] = await Promise.all([
      getLatestProjects(limit, locale),
      fetchLendingDataForProjects(),
    ])

    const body = {
      projects: projects.map((p) => {
        const lending = lendingData[p.id] ?? null
        return {
          id: p.id,
          slug: p.slug,
          title: p.title,
          coverUrl: p.coverUrl ?? '',
          category: normalizeInvestmentCategory(p.investmentCategory),
          description: p.description ?? null,
          descriptionLinks: p.descriptionLinks ?? null,
          shortDescription: p.shortDescription ?? null,
          howItWorks: p.howItWorks ?? null,
          keyInformation: p.keyInformation ?? null,
          teaserVideoUrl: p.teaserVideoUrl ?? null,
          hasGallery: p.hasGallery ?? false,
          competitiveAdvantages: p.competitiveAdvantages ?? null,
          faq: p.faq ?? null,
          // Phase 2A.11 — lending enrichment (null if no linked product)
          apy: lending?.apy ?? null,
          raised: lending?.raised ?? null,
          target: lending?.target ?? null,
          progress: lending?.progress ?? null,
          investorsCount: lending?.investorsCount ?? null,
          durationMonths: lending?.durationMonths ?? null,
          lendingAsset: lending?.asset ?? null,
          lendingStatus: lending?.status ?? null,
          isInvestable: lending?.isInvestable ?? false,
          lendingProductId: lending?.lending_product_id ?? null,
          entryAssetDefault: lending?.entry_asset_default ?? null,
          entryAssetsAllowed: lending?.entry_assets_allowed ?? null,
        }
      }),
    }

    const res = NextResponse.json(body)
    res.headers.set(
      'X-Arquantix-Deprecated-Use-Instead',
      '/api/mobile/flutter/catalog/products?type=exclusive_offer',
    )
    res.headers.set(
      'Warning',
      '299 - "Deprecated for Exclusive Offers app listing; prefer Catalog API"',
    )
    return res
  } catch (error) {
    console.error('Error fetching projects:', error)
    return NextResponse.json({ projects: [] })
  }
}
