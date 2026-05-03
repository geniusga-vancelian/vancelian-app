import { NextResponse } from 'next/server'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import {
  scanMenuLanguageDeep,
  type MenuInputForScan,
  type MenuItemInputForScan,
} from '@/lib/admin/menuCheckLanguage'
import { prisma } from '@/lib/prisma'

const bodySchema = z.object({
  targetLocale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
})

/**
 * POST /api/admin/menus/[key]/check-language/scan
 *
 * Scan linguistique deep (local + affinage IA OpenAI batché) du menu et de
 * ses items pour la `targetLocale`. Lecture seule.
 *
 * Endpoint paramétré par `key` (`primary`, …) pour permettre d'étendre
 * trivialement à d'autres menus si on en crée un jour.
 */
export async function POST(
  req: Request,
  { params }: { params: Promise<{ key: string }> | { key: string } },
) {
  try {
    const resolved = await Promise.resolve(params)
    const key = resolved?.key?.trim()
    if (!key) {
      return NextResponse.json({ error: 'Invalid menu key' }, { status: 400 })
    }

    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const body = await req.json().catch(() => ({}))
    const parsed = bodySchema.safeParse(body)
    if (!parsed.success) {
      return NextResponse.json(
        { error: 'Invalid body', details: parsed.error.flatten() },
        { status: 400 },
      )
    }

    const targetLocale = parsed.data.targetLocale as Locale

    const menu = await prisma.menu.findUnique({
      where: { key },
      include: {
        i18n: true,
        menuItems: {
          orderBy: { order: 'asc' },
          include: { i18n: true },
        },
      },
    })

    if (!menu) {
      return NextResponse.json({ error: 'Menu not found' }, { status: 404 })
    }

    const menuInput: MenuInputForScan = {
      id: menu.id,
      name: menu.name ?? '',
      i18n: menu.i18n.map((row) => ({ locale: row.locale, name: row.name })),
    }

    const itemInputs: MenuItemInputForScan[] = menu.menuItems.map((item, index) => ({
      id: item.id,
      index,
      enabled: item.enabled,
      baseLabel: item.label ?? '',
      i18n: item.i18n.map((row) => ({ locale: row.locale, label: row.label })),
    }))

    const result = await scanMenuLanguageDeep(menuInput, itemInputs, targetLocale)

    return NextResponse.json({
      ok: true,
      menuKey: key,
      itemsScanned: itemInputs.filter((i) => i.enabled).length,
      itemsDisabled: itemInputs.filter((i) => !i.enabled).length,
      result,
    })
  } catch (e) {
    console.error('[menus/check-language/scan]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
