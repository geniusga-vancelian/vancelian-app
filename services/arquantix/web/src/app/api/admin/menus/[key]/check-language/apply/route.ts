import { NextResponse } from 'next/server'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import {
  applyMenuLanguageFixes,
  type MenuInputForScan,
  type MenuItemInputForScan,
} from '@/lib/admin/menuCheckLanguage'
import { prisma } from '@/lib/prisma'

const bodySchema = z.object({
  targetLocale: z.string().refine(isValidLocale, { message: 'Invalid locale' }),
})

/**
 * POST /api/admin/menus/[key]/check-language/apply
 *
 * Applique les corrections linguistiques (OpenAI) au menu et à ses items
 * pour la `targetLocale` :
 *   - upsert `MenuI18n` (name)
 *   - upsert `MenuItemI18n` (label) par item
 *
 * Pas de notion DRAFT/PUBLISHED côté menu : l'écriture est immédiatement
 * visible côté navigation publique après revalidation Next.
 *
 * Le `translationStatus` des upserts est forcé à `MACHINE` (cohérent avec
 * le reste du flux i18n menu : un opérateur peut ensuite « Approve » via
 * l'écran admin existant).
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

    const { upsertPlan, apply, scan } = await applyMenuLanguageFixes(
      menuInput,
      itemInputs,
      targetLocale,
    )

    if (apply.fixedHintKeys.length === 0) {
      return NextResponse.json({
        ok: true,
        applied: false,
        fixedFieldPaths: [],
        skippedFields: apply.skippedFields,
        tokensUsedApprox: apply.tokensUsedApprox,
        llmRefinement: scan.llmRefinement,
      })
    }

    // Persistance : upserts MenuI18n + MenuItemI18n.
    const upserts: Promise<unknown>[] = []
    if (upsertPlan.menuI18nName !== undefined) {
      upserts.push(
        prisma.menuI18n.upsert({
          where: {
            menuId_locale: { menuId: menu.id, locale: targetLocale },
          },
          create: {
            menuId: menu.id,
            locale: targetLocale,
            name: upsertPlan.menuI18nName,
            translationStatus: 'MACHINE',
          },
          update: {
            name: upsertPlan.menuI18nName,
            translationStatus: 'MACHINE',
          },
        }),
      )
    }
    for (const [itemId, label] of upsertPlan.itemI18nLabelByItemId.entries()) {
      upserts.push(
        prisma.menuItemI18n.upsert({
          where: {
            menuItemId_locale: { menuItemId: itemId, locale: targetLocale },
          },
          create: {
            menuItemId: itemId,
            locale: targetLocale,
            label,
            translationStatus: 'MACHINE',
          },
          update: {
            label,
            translationStatus: 'MACHINE',
          },
        }),
      )
    }
    await Promise.all(upserts)

    return NextResponse.json({
      ok: true,
      applied: true,
      fixedFieldPaths: apply.fixedHintKeys,
      skippedFields: apply.skippedFields,
      tokensUsedApprox: apply.tokensUsedApprox,
      llmRefinement: scan.llmRefinement,
    })
  } catch (e) {
    console.error('[menus/check-language/apply]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
