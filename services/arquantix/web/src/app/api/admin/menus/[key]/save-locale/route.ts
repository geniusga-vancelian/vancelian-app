import { NextResponse } from 'next/server'
import type { Prisma } from '@prisma/client'
import { z } from 'zod'

import { isValidLocale, type Locale } from '@/config/locales'
import { getSessionFromCookie } from '@/lib/auth'
import {
  buildMenuSaveLocalePlan,
  type MenuSaveLocaleInput,
} from '@/lib/admin/menuSaveLocale'
import { prisma } from '@/lib/prisma'

const bodySchema = z.object({
  /** Locale active de l'éditeur admin (= cible des upserts MenuI18n). */
  activeLocale: z
    .string()
    .refine(isValidLocale, { message: 'Invalid activeLocale' }),
  /**
   * Locale par défaut du site. Doit matcher `defaultLocale` exporté par
   * `@/config/locales` ; sert à arbitrer si on autorise l'écriture de
   * `Menu.name` (base partagée) ou non.
   */
  defaultLocale: z
    .string()
    .refine(isValidLocale, { message: 'Invalid defaultLocale' }),
  /**
   * Valeur de l'input « Menu Name » du form admin. Prise en compte
   * uniquement si `activeLocale === defaultLocale` (cf. plan).
   */
  menuNameInput: z.string().optional(),
  /** Valeur saisie pour `MenuI18n[activeLocale].name`. */
  menuI18nName: z.string().optional(),
  /**
   * Map `menuItemId → label` pour `MenuItemI18n[activeLocale].label`.
   * Les valeurs vides sont ignorées (pas d'écrasement).
   */
  itemLabels: z.record(z.string(), z.string()).optional(),
})

/**
 * POST /api/admin/menus/[key]/save-locale
 *
 * « Tout enregistrer pour cette locale » — équivalent fonctionnel du bouton
 * « Enregistrer » du `SiteFooterEditor`. Persiste en une seule transaction
 * Prisma toutes les éditions inline en mémoire de la page admin pour la
 * locale active :
 *   - `Menu.name` (base) si `activeLocale === defaultLocale` ;
 *   - `MenuI18n[activeLocale].name` ;
 *   - chaque `MenuItemI18n[activeLocale].label` non vide fourni.
 *
 * Toujours `translationStatus: ORIGINAL` car c'est une édition humaine
 * volontaire (à distinguer du `MACHINE` posé par la correction IA).
 *
 * Pas de notion DRAFT/PUBLISHED côté menu (le modèle ne le prévoit pas) :
 * les modifs sont immédiatement visibles côté navigation publique.
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

    const activeLocale = parsed.data.activeLocale as Locale
    const defaultLocaleParam = parsed.data.defaultLocale as Locale

    const menu = await prisma.menu.findUnique({
      where: { key },
      include: { menuItems: { select: { id: true } } },
    })

    if (!menu) {
      return NextResponse.json({ error: 'Menu not found' }, { status: 404 })
    }

    // Garde-fou : on n'upsert que des MenuItemI18n liés à des items de CE
    // menu (évite qu'un caller malveillant écrase des labels d'un autre menu).
    const ownedItemIds = new Set(menu.menuItems.map((it) => it.id))
    const filteredItemLabels: Record<string, string> = {}
    let droppedUnknownItems = 0
    for (const [itemId, label] of Object.entries(parsed.data.itemLabels ?? {})) {
      if (ownedItemIds.has(itemId)) {
        filteredItemLabels[itemId] = label
      } else {
        droppedUnknownItems += 1
      }
    }

    const planInput: MenuSaveLocaleInput = {
      activeLocale,
      defaultLocale: defaultLocaleParam,
      menuNameInput: parsed.data.menuNameInput,
      menuI18nName: parsed.data.menuI18nName,
      itemLabels: filteredItemLabels,
    }
    const plan = buildMenuSaveLocalePlan(planInput)

    const upserts: Prisma.PrismaPromise<unknown>[] = []

    if (plan.menuNameToWrite !== undefined) {
      upserts.push(
        prisma.menu.update({
          where: { id: menu.id },
          data: { name: plan.menuNameToWrite },
        }),
      )
    }

    if (plan.menuI18nNameToWrite !== undefined) {
      upserts.push(
        prisma.menuI18n.upsert({
          where: {
            menuId_locale: { menuId: menu.id, locale: activeLocale },
          },
          create: {
            menuId: menu.id,
            locale: activeLocale,
            name: plan.menuI18nNameToWrite,
            translationStatus: 'ORIGINAL',
          },
          update: {
            name: plan.menuI18nNameToWrite,
            translationStatus: 'ORIGINAL',
          },
        }),
      )
    }

    for (const [itemId, label] of plan.itemLabelsToWrite.entries()) {
      upserts.push(
        prisma.menuItemI18n.upsert({
          where: {
            menuItemId_locale: { menuItemId: itemId, locale: activeLocale },
          },
          create: {
            menuItemId: itemId,
            locale: activeLocale,
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
      activeLocale,
      summary: {
        menuNameUpdated: plan.diagnostics.didWriteMenuNameBase,
        menuI18nNameUpdated: plan.diagnostics.didWriteMenuI18nName,
        itemsWritten: plan.diagnostics.itemsWritten.length,
        itemsSkippedEmpty: plan.diagnostics.itemsSkippedEmpty.length,
        droppedUnknownItems,
      },
    })
  } catch (e) {
    console.error('[menus/save-locale]', e)
    return NextResponse.json({ error: 'Internal server error' }, { status: 500 })
  }
}
