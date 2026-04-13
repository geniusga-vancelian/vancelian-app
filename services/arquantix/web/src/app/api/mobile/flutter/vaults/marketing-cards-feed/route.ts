import { NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { prisma } from '@/lib/prisma'

const VAULT_TEMPLATE_DB = 'vault_builder'
const VAULT_SECTION_KEY = 'vault_builder_v1'
const VAULT_DEFAULT_LOCALE = 'fr'

const MARKETING_SLIDING_TYPES = [
  'marketingcardssmallslidingcarrousel_portrait',
  'marketingcardssmallslidingcarrousel_paysage',
]

type MarketingCardItem = {
  imageUrl: string
  redirectUrl: string
  title?: string
  description?: string
  logoLabel?: string
  buttonLabel?: string
}

type FeedSection = {
  dbOrder: number
  vaultSlug: string
  vaultTitle: string
  isPortrait: boolean
  title: string
  items: MarketingCardItem[]
}

/**
 * GET /api/mobile/flutter/vaults/marketing-cards-feed
 * Feed des modules Marketing Cards Sliding depuis tous les vaults (saving-vaults).
 * Retourne les sections dans l'ordre des vaults en base.
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url)
    const investmentTypeSlug = searchParams.get('investmentTypeSlug')?.trim() || null

    const pages = await prisma.page.findMany({
      where: { template: VAULT_TEMPLATE_DB },
      include: {
        sections: {
          where: { key: VAULT_SECTION_KEY },
          include: {
            contents: {
              where: {
                locale: VAULT_DEFAULT_LOCALE,
                status: ContentStatus.PUBLISHED,
              },
              take: 1,
            },
          },
          take: 1,
        },
      },
      orderBy: { createdAt: 'asc' },
    })

    const sortedPages = [...pages].sort((a, b) => {
      const dataA = a.sections[0]?.contents[0]?.data as Record<string, unknown> | null
      const dataB = b.sections[0]?.contents[0]?.data as Record<string, unknown> | null
      const orderA = typeof dataA?.sortOrder === 'number' ? dataA.sortOrder : 999
      const orderB = typeof dataB?.sortOrder === 'number' ? dataB.sortOrder : 999
      if (investmentTypeSlug) {
        return orderA - orderB
      }
      const catA =
        (typeof dataA?.investmentTypeSlug === 'string' ? dataA.investmentTypeSlug : null) ??
        '__none__'
      const catB =
        (typeof dataB?.investmentTypeSlug === 'string' ? dataB.investmentTypeSlug : null) ??
        '__none__'
      if (catA !== catB) return String(catA).localeCompare(String(catB))
      return orderA - orderB
    })

    const allSections: FeedSection[] = []

    for (let pageIndex = 0; pageIndex < sortedPages.length; pageIndex++) {
      const page = sortedPages[pageIndex]
      const content = page.sections[0]?.contents[0]
      const data = content?.data as Record<string, unknown> | null
      if (!data) continue

      if (investmentTypeSlug) {
        const pageInvestmentType = typeof data.investmentTypeSlug === 'string' ? data.investmentTypeSlug : null
        if (pageInvestmentType !== investmentTypeSlug) continue
      }

      const pageTitle = (data.pageTitle as Record<string, unknown>)?.text ?? page.title ?? page.slug
      const modules = (data.modules ?? []) as unknown[]

      for (const m of modules) {
        if (m == null || typeof m !== 'object') continue
        const mod = m as Record<string, unknown>
        if (mod.enabled === false) continue

        const type = String(mod.type ?? '').trim().toLowerCase()
        const isPortrait = type === 'marketingcardssmallslidingcarrousel_portrait'

        if (!MARKETING_SLIDING_TYPES.includes(type)) continue

        const modContent = mod.content
        if (modContent == null || typeof modContent !== 'object') continue
        const c = modContent as Record<string, unknown>
        const itemsRaw = Array.isArray(c.items) ? c.items : []
        const title = String(c.title ?? '').trim()

        const items: MarketingCardItem[] = itemsRaw
          .filter((it): it is Record<string, unknown> => it != null && typeof it === 'object')
          .map((it) => {
            const img = String(it.imageUrl ?? '').trim()
            const url = String(it.redirectUrl ?? it.url ?? 'https://arquantix.com').trim()
            return {
              imageUrl: img || (isPortrait ? 'https://picsum.photos/600/800' : 'https://picsum.photos/800/600'),
              redirectUrl: url,
              title: String(it.title ?? '').trim() || undefined,
              description: String(it.description ?? '').trim() || undefined,
              logoLabel: String(it.logoLabel ?? '').trim() || undefined,
              buttonLabel: String(it.buttonLabel ?? '').trim() || undefined,
            }
          })
          .filter((it) => it.redirectUrl.length > 0)

        if (items.length > 0) {
          allSections.push({
            dbOrder: pageIndex,
            vaultSlug: page.slug,
            vaultTitle: String(pageTitle),
            isPortrait,
            title,
            items,
          })
        }
      }
    }

    return NextResponse.json(
      { sections: allSections },
      {
        headers: {
          'Cache-Control': 'public, max-age=60, s-maxage=60',
        },
      }
    )
  } catch (error) {
    console.error('[api/mobile/flutter/vaults/marketing-cards-feed]', error)
    return NextResponse.json({ error: 'Internal server error', message: 'The request could not be completed.' }, { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } })
  }
}
