import { NextRequest, NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import { z } from 'zod'
import { computeMenuItemUrlPath } from '@/lib/menu/computeUrlPath'
import { resolveLabelWithFallback, DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'
import { getLocaleOrDefault } from '@/config/locales'
import { ensureBlogCmsPresence } from '@/lib/cms/ensureBlogCmsPresence'
import { ensurePrimaryMenuLanguageSwitcher } from '@/lib/menu/ensurePrimaryMenuLanguageSwitcher'

const updateMenuSchema = z.object({
  name: z.string().optional(),
})

// GET /api/admin/menus/primary - Get primary menu with ordered items
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    await ensureBlogCmsPresence()
    await ensurePrimaryMenuLanguageSwitcher()

    // Get locale from query param, default to fr
    const { searchParams } = new URL(request.url)
    const localeParam = searchParams.get('locale') || DEFAULT_LOCALE
    const locale = getLocaleOrDefault(localeParam)

    let menu = await prisma.menu.findUnique({
      where: { key: 'primary' },
      include: {
        menuItems: {
          orderBy: { order: 'asc' },
          include: {
            page: true,
            i18n: true,
          },
        },
        i18n: true,
      },
    })

    // If menu doesn't exist, create it with default root item
    if (!menu) {
      menu = await prisma.menu.create({
        data: {
          key: 'primary',
          name: 'Primary Menu',
          menuItems: {
            create: {
              label: 'Home',
              isRoot: true,
              pageId: null,
              order: 0,
              enabled: true,
            },
          },
        },
        include: {
          menuItems: {
            orderBy: { order: 'asc' },
            include: {
              page: true,
              i18n: true,
            },
          },
          i18n: true,
        },
      })
    }

    // Resolve menu name with i18n
    const resolvedMenuName = resolveLabelWithFallback({
      requestedLocale: locale,
      baseLabel: menu.name || '',
      i18nRows: (menu.i18n || []).map((i18n) => ({
        locale: i18n.locale,
        label: i18n.name,
      })),
    })

    const { menuItems, ...menuRest } = menu

    // Add computedUrlPath, isInvalidTarget flag, and resolved label to each item
    const menuWithComputedUrls = {
      ...menuRest,
      name: resolvedMenuName,
      nameBase: menu.name,
      items: menuItems.map((item) => {
        // Check if item is invalid: not root but page is null (pageId exists but page was deleted)
        const isInvalidTarget = !item.isRoot && item.pageId !== null && item.page === null
        
        // Resolve label with i18n
        const resolvedLabel = resolveLabelWithFallback({
          requestedLocale: locale,
          baseLabel: item.label || '',
          i18nRows: (item.i18n || []).map((i18n) => ({
            locale: i18n.locale,
            label: i18n.label,
          })),
        })
        
        // Default type to LINK for existing items that don't have type set
        const itemType = item.type || 'LINK'
        
        const urlPath =
          itemType === 'LANGUAGE_SWITCHER'
            ? '#'
            : itemType === 'BUTTON'
              ? item.externalUrl || '#'
              : isInvalidTarget
                ? null
                : computeMenuItemUrlPath(
                    item.isRoot,
                    item.page?.slug || null,
                    locale,
                    item.page?.template,
                  )

        return {
          ...item,
          type: itemType, // Ensure type is always set
          label: resolvedLabel, // Override with resolved label
          labelBase: item.label, // Keep base label for reference
          isInvalidTarget:
            itemType === 'LANGUAGE_SWITCHER' || itemType === 'BUTTON' ? false : isInvalidTarget,
          computedUrlPath: urlPath,
          buttonStyle: item.buttonStyle,
          buttonAction: item.buttonAction,
          externalUrl: item.externalUrl,
        }
      }),
    }

    return NextResponse.json({ menu: menuWithComputedUrls })
  } catch (error) {
    console.error('Error fetching primary menu:', error)
    console.error('Error details:', {
      message: error instanceof Error ? error.message : 'Unknown error',
      stack: error instanceof Error ? error.stack : undefined,
    })
    return NextResponse.json(
      { 
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    )
  }
}

// PUT /api/admin/menus/primary - Update menu name
export async function PUT(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await request.json()
    const { name } = updateMenuSchema.parse(body)

    const menu = await prisma.menu.update({
      where: { key: 'primary' },
      data: {
        ...(name !== undefined && { name }),
      },
      include: {
        menuItems: {
          orderBy: { order: 'asc' },
        },
      },
    })

    const { menuItems, ...menuRest } = menu
    return NextResponse.json({ menu: { ...menuRest, items: menuItems } })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid request data', issues: error.issues },
        { status: 400 }
      )
    }
    console.error('Error updating primary menu:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

