import { NextResponse } from 'next/server'
import type { Prisma } from '@prisma/client'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import {
  buildMenuCopyPlan,
  type MenuCopyMode,
} from '@/lib/admin/menuCopyLocale'
import type {
  MenuInputForScan,
  MenuItemInputForScan,
} from '@/lib/admin/menuCheckLanguage'
import { prisma } from '@/lib/prisma'

const bodySchema = z.object({
  sourceLocale: z.string().refine(isValidLocale, { message: 'Invalid sourceLocale' }),
  targetLocale: z.string().refine(isValidLocale, { message: 'Invalid targetLocale' }),
  /**
   * `'missing'` (défaut) : préserve les traductions cibles déjà présentes
   *   (alignement avec `/api/admin/translate/menu` qui utilise déjà ce mode).
   * `'overwrite'` : remplace tout, équivalent du « Copier depuis FR » Footer.
   */
  mode: z.enum(['missing', 'overwrite']).optional().default('missing'),
})

/**
 * POST /api/admin/menus/[key]/copy-locale
 *
 * Étape 1 du workflow d'édition multilingue du menu — alignée sur Pages
 * (`/api/admin/pages/[slug]/copy-locale-content`) et Footer
 * (`SiteFooterEditor.handleCopyFromDefault`).
 *
 * Comportement :
 *   1. Charge `Menu` + `MenuItem` + `*I18n` rows.
 *   2. Calcule un plan d'upserts via `buildMenuCopyPlan` (pur, testé).
 *   3. Persiste les rows en `translationStatus: ORIGINAL` — sémantique :
 *      « ce sont les libellés FR matérialisés tels quels en EN/IT en attente
 *      de relecture ou de traduction IA », pas une traduction machine.
 *
 * Pas de notion DRAFT/PUBLISHED côté menu (le modèle ne le prévoit pas) :
 * la copie est immédiatement visible côté navigation publique après
 * revalidation Next. C'est exactement le même comportement que Footer.
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

    const sourceLocale = parsed.data.sourceLocale as Locale
    const targetLocale = parsed.data.targetLocale as Locale
    const mode = parsed.data.mode as MenuCopyMode

    if (sourceLocale === targetLocale) {
      return NextResponse.json(
        { error: 'sourceLocale et targetLocale doivent différer' },
        { status: 400 },
      )
    }

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
    const itemInputs: MenuItemInputForScan[] = menu.menuItems.map(
      (item, index) => ({
        id: item.id,
        index,
        enabled: item.enabled,
        baseLabel: item.label ?? '',
        i18n: item.i18n.map((row) => ({ locale: row.locale, label: row.label })),
      }),
    )

    const plan = buildMenuCopyPlan(
      menuInput,
      itemInputs,
      sourceLocale,
      targetLocale,
      mode,
    )

    const upserts: Prisma.PrismaPromise<unknown>[] = []
    if (plan.menuI18nName !== undefined) {
      upserts.push(
        prisma.menuI18n.upsert({
          where: {
            menuId_locale: { menuId: menu.id, locale: targetLocale },
          },
          create: {
            menuId: menu.id,
            locale: targetLocale,
            name: plan.menuI18nName,
            translationStatus: 'ORIGINAL',
          },
          update: {
            name: plan.menuI18nName,
            translationStatus: 'ORIGINAL',
          },
        }),
      )
    }
    for (const [itemId, label] of plan.itemI18nLabelByItemId.entries()) {
      upserts.push(
        prisma.menuItemI18n.upsert({
          where: {
            menuItemId_locale: { menuItemId: itemId, locale: targetLocale },
          },
          create: {
            menuItemId: itemId,
            locale: targetLocale,
            label,
            translationStatus: 'ORIGINAL',
          },
          update: {
            label,
            translationStatus: 'ORIGINAL',
          },
        }),
      )
    }

    if (upserts.length > 0) {
      await prisma.$transaction(upserts)
    }

    return NextResponse.json({
      ok: true,
      menuKey: key,
      sourceLocale,
      targetLocale,
      mode,
      summary: {
        menuName: plan.diagnostics.menuName,
        itemsCopied: plan.diagnostics.copied.length,
        itemsSkippedExisting: plan.diagnostics.skippedExisting.length,
        itemsSkippedEmptySource: plan.diagnostics.skippedEmptySource.length,
        itemsSkippedDisabled: plan.diagnostics.skippedDisabled.length,
      },
    })
  } catch (e) {
    console.error('[menus/copy-locale]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
