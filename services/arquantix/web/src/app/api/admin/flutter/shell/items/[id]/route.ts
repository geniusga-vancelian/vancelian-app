import { NextRequest, NextResponse } from 'next/server'
import { type Prisma } from '@prisma/client'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import {
  APP_MAIN_TABS_MENU_KEY,
  APP_MAIN_TABS_PAGE_SLUG,
  APP_MENU_SECTION_KEY,
  appMenuSectionDataSchema,
} from '@/lib/mobile/appShellModel'

/**
 * DELETE /api/admin/flutter/shell/items/[id]
 *
 * Supprime un tab : `MenuItem` (cascade Prisma sur `MenuItemI18n`) **et** son
 * entrée correspondante dans `SectionContent.data.items` pour **toutes** les
 * locales/statuts. Idempotent : 404 si l'item est déjà absent.
 *
 * Garde-fou : refuse de supprimer si le tab cible n'appartient pas au menu
 * `app_main_tabs` (évite tout abus depuis cet endpoint dédié shell).
 */
export async function DELETE(
  _request: NextRequest,
  { params }: { params: { id: string } },
) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const id = (params?.id ?? '').trim()
    if (!id) {
      return NextResponse.json({ error: 'Invalid id' }, { status: 400 })
    }

    const menu = await prisma.menu.findUnique({
      where: { key: APP_MAIN_TABS_MENU_KEY },
      select: { id: true },
    })
    if (!menu) {
      return NextResponse.json({ error: 'App shell not seeded' }, { status: 404 })
    }
    const item = await prisma.menuItem.findUnique({
      where: { id },
      select: { id: true, menuId: true },
    })
    if (!item) {
      return NextResponse.json({ error: 'Item not found' }, { status: 404 })
    }
    if (item.menuId !== menu.id) {
      return NextResponse.json(
        { error: 'Item does not belong to app_main_tabs menu' },
        { status: 403 },
      )
    }

    const page = await prisma.page.findUnique({
      where: { slug: APP_MAIN_TABS_PAGE_SLUG },
      include: {
        sections: {
          where: { key: APP_MENU_SECTION_KEY },
          include: { contents: true },
          take: 1,
        },
      },
    })

    await prisma.$transaction(async (tx) => {
      /// 1) Retire l'item de toutes les rows `SectionContent.data.items`
      ///    (toutes locales × statuts) — préserve les autres entrées.
      const section = page?.sections[0]
      if (section) {
        for (const content of section.contents) {
          const parsed = appMenuSectionDataSchema.safeParse(content.data)
          const baseItems = parsed.success ? parsed.data.items : []
          const filtered = baseItems.filter((b) => b.menuItemId !== id)
          if (filtered.length === baseItems.length) continue
          const dataPayload = { items: filtered } as unknown as Prisma.InputJsonValue
          await tx.sectionContent.update({
            where: { id: content.id },
            data: { data: dataPayload, updatedByUserId: session.userId },
          })
        }
      }

      /// 2) MenuItem (cascade Prisma sur MenuItemI18n via la relation)
      await tx.menuItem.delete({ where: { id } })
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/flutter/shell/items/[id] DELETE]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 },
    )
  }
}
