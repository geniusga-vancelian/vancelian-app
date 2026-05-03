import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { getLocaleOrDefault } from '@/config/locales'

const updateMenuI18nSchema = z.object({
  locale: z.string().min(1),
  name: z.string().min(1, 'Name is required'),
})

// GET /api/admin/menus/[key]/i18n?locale=xx
export async function GET(
  request: NextRequest,
  { params }: { params: { key: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale')
    const locale = localeParam ? getLocaleOrDefault(localeParam) : null

    const menu = await prisma.menu.findUnique({
      where: { key: params.key },
      include: {
        i18n: locale
          ? {
              where: { locale },
              take: 1,
            }
          : true,
      },
    })

    if (!menu) {
      return NextResponse.json({ error: 'Menu not found' }, { status: 404 })
    }

    return NextResponse.json({ i18n: menu.i18n })
  } catch (error) {
    console.error('Error fetching menu i18n:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

// PUT /api/admin/menus/[key]/i18n
export async function PUT(
  request: NextRequest,
  { params }: { params: { key: string } }
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { locale, name } = updateMenuI18nSchema.parse(body)

    const menu = await prisma.menu.findUnique({
      where: { key: params.key },
    })

    if (!menu) {
      return NextResponse.json({ error: 'Menu not found' }, { status: 404 })
    }

    const i18n = await prisma.menuI18n.upsert({
      where: {
        menuId_locale: {
          menuId: menu.id,
          locale,
        },
      },
      create: {
        menuId: menu.id,
        locale,
        name,
        translationStatus: 'ORIGINAL',
      },
      update: {
        name,
      },
    })

    return NextResponse.json({ i18n })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating menu i18n:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
