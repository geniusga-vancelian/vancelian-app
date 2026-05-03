import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { defaultLocale } from '@/config/locales'

/**
 * Endpoint identique à `/api/admin/help/tag-options` (mêmes 3 types de tags
 * proposés : THEMATIC_CATEGORY, INVESTMENT_TYPE, EXCLUSIVE_OFFER). Cloné pour
 * que l'admin Academy soit isolé de l'admin Help côté front.
 */
type TagOptionType = 'THEMATIC_CATEGORY' | 'INVESTMENT_TYPE' | 'EXCLUSIVE_OFFER'

type TagOption = {
  type: TagOptionType
  id: string
  slug: string
  label: string
  groupLabel: string
}

export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const locale = (searchParams.get('locale') || defaultLocale).toLowerCase()

    const [thematicCategories, investmentTypes, projects] = await Promise.all([
      prisma.investmentCategory.findMany({
        orderBy: [{ sortOrder: 'asc' }, { label: 'asc' }],
        select: { id: true, slug: true, label: true },
      }),
      prisma.investmentTypes.findMany({
        orderBy: [{ sortOrder: 'asc' }, { label: 'asc' }],
        select: { id: true, slug: true, label: true },
      }),
      prisma.project.findMany({
        orderBy: [{ updatedAt: 'desc' }],
        select: {
          id: true,
          slug: true,
          i18n: {
            where: { locale: { in: [locale, defaultLocale] } },
            select: { locale: true, title: true },
            take: 2,
          },
        },
      }),
    ])

    const options: TagOption[] = []

    for (const cat of thematicCategories) {
      options.push({
        type: 'THEMATIC_CATEGORY',
        id: cat.id,
        slug: cat.slug,
        label: cat.label,
        groupLabel: 'Thematic categories',
      })
    }

    for (const invType of investmentTypes) {
      options.push({
        type: 'INVESTMENT_TYPE',
        id: invType.id,
        slug: invType.slug,
        label: invType.label,
        groupLabel: 'Investment types',
      })
    }

    for (const project of projects) {
      const title =
        project.i18n.find((item) => item.locale.toLowerCase() === locale)?.title ||
        project.i18n.find((item) => item.locale.toLowerCase() === defaultLocale)?.title ||
        project.slug

      options.push({
        type: 'EXCLUSIVE_OFFER',
        id: project.id,
        slug: project.slug,
        label: title,
        groupLabel: 'Exclusive offers',
      })
    }

    return NextResponse.json({ options })
  } catch (error) {
    console.error('[Academy Tag Options API] Error:', error)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
