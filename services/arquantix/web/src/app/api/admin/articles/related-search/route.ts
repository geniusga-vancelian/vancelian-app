import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { defaultLocale } from '@/config/locales'
import { ASSET_LABELS } from '@/lib/admin/asset-labels'

const ASSET_TICKERS = Object.keys(ASSET_LABELS)

type RelatedOption = 
  | { type: 'project'; id: string; label: string; slug?: string }
  | { type: 'asset'; symbol: string; label: string }
  | { type: 'vault'; slug: string; label: string }

/**
 * GET /api/admin/articles/related-search?q=xxx
 * Recherche unifiée parmi projets, assets (crypto), et vaults (pages template vault_builder).
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const q = (searchParams.get('q') || '').trim().toLowerCase()
    const limit = Math.min(parseInt(searchParams.get('limit') || '15', 10), 30)

    const options: RelatedOption[] = []

    // 1. Projets (titre ou slug)
    if (q) {
      const projects = await prisma.project.findMany({
        where: {
          OR: [
            { slug: { contains: q, mode: 'insensitive' } },
            {
              i18n: {
                some: {
                  title: { contains: q, mode: 'insensitive' },
                  locale: defaultLocale,
                },
              },
            },
          ],
        },
        include: {
          i18n: { where: { locale: defaultLocale }, take: 1 },
        },
        take: limit,
      })
      for (const p of projects) {
        const label = p.i18n[0]?.title || p.slug
        options.push({ type: 'project', id: p.id, label, slug: p.slug })
      }
    }

    // 2. Assets (crypto) : filtre sur le tableau statique
    const assetMatches = !q
      ? ASSET_TICKERS.slice(0, 10)
      : ASSET_TICKERS.filter(
          (t) => t.includes(q) || ASSET_LABELS[t].toLowerCase().includes(q)
        ).slice(0, limit)
    for (const symbol of assetMatches) {
      options.push({
        type: 'asset',
        symbol,
        label: ASSET_LABELS[symbol] || `${symbol.toUpperCase()} (${symbol})`,
      })
    }

    // 3. Vaults = pages avec template vault_builder
    if (q) {
      const pages = await prisma.page.findMany({
        where: {
          template: 'vault_builder',
          OR: [
            { slug: { contains: q, mode: 'insensitive' } },
            { title: { contains: q, mode: 'insensitive' } },
          ],
        },
        take: limit,
      })
      for (const page of pages) {
        const label = page.title || page.slug
        options.push({ type: 'vault', slug: page.slug, label })
      }
    } else {
      const pages = await prisma.page.findMany({
        where: { template: 'vault_builder' },
        orderBy: { title: 'asc' },
        take: 10,
      })
      for (const page of pages) {
        options.push({
          type: 'vault',
          slug: page.slug,
          label: page.title || page.slug,
        })
      }
    }

    return NextResponse.json({ options })
  } catch (error) {
    console.error('related-search:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
