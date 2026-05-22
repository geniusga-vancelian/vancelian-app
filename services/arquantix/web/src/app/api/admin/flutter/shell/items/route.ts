import { NextRequest, NextResponse } from 'next/server'
import {
  ContentStatus,
  MenuItemType,
  MenuNavigationNodeKind,
  TranslationStatus,
  type Prisma,
} from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'
import {
  APP_MAIN_TABS_MENU_KEY,
  APP_MAIN_TABS_PAGE_SLUG,
  APP_MENU_SECTION_KEY,
  APP_MOBILE_ICON_KEYS,
  appMobileTargetSchema,
  appMenuSectionDataSchema,
} from '@/lib/mobile/appShellModel'

const createItemSchema = z.object({
  label: z.string().min(1).max(80),
  icon: z.enum(APP_MOBILE_ICON_KEYS),
  target: appMobileTargetSchema,
  /// Position d'insertion. Si non fourni → append à la fin (max(order)+1).
  order: z.number().int().nonnegative().optional(),
  enabled: z.boolean().optional(),
})

/**
 * POST /api/admin/flutter/shell/items?status=draft|published
 *
 * Crée un nouveau tab (`MenuItem` + `MenuItemI18n` pour **toutes** les locales
 * activées + entrée dans `SectionContent.data.items` pour la locale d'édition,
 * en DRAFT par défaut, ou DRAFT+PUBLISHED si `status=published`).
 *
 * Le `label` fourni est utilisé tel quel pour la locale d'édition courante et
 * comme libellé pour les autres locales (l'admin affinera ensuite par langue
 * via PATCH `/api/admin/flutter/shell?locale=…`).
 *
 * Précondition : le shell doit avoir été seedé (cf. POST `/seed`).
 */
export async function POST(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (request.nextUrl.searchParams.get('locale') || '').trim() || i18n.defaultLocale
    const writeScope =
      request.nextUrl.searchParams.get('status') === 'published' ? 'published' : 'draft'

    if (
      i18n.multilingualEnabled &&
      !i18n.supportedLocales.includes(requestedLocale as (typeof i18n.supportedLocales)[number])
    ) {
      return NextResponse.json(
        { error: `Locale "${requestedLocale}" not enabled` },
        { status: 400 },
      )
    }

    const body = createItemSchema.parse(await request.json())

    const [page, menu] = await Promise.all([
      prisma.page.findUnique({
        where: { slug: APP_MAIN_TABS_PAGE_SLUG },
        include: { sections: { where: { key: APP_MENU_SECTION_KEY }, take: 1 } },
      }),
      prisma.menu.findUnique({
        where: { key: APP_MAIN_TABS_MENU_KEY },
        include: { menuItems: { select: { order: true } } },
      }),
    ])
    if (!page || !menu) {
      return NextResponse.json(
        { error: 'App shell not seeded — POST /api/admin/flutter/shell/seed first' },
        { status: 404 },
      )
    }
    const section = page.sections[0]
    if (!section) {
      return NextResponse.json({ error: 'Section missing' }, { status: 500 })
    }

    /// Calcul de l'ordre par défaut : append à la fin (évite de bouleverser les
    /// indices existants si l'admin clique simplement sur "+ Ajouter").
    const maxOrder = menu.menuItems.reduce((m, it) => (it.order > m ? it.order : m), -1)
    const insertOrder = body.order ?? maxOrder + 1
    const enabled = body.enabled ?? true

    const locales = i18n.supportedLocales.length > 0 ? i18n.supportedLocales : [i18n.defaultLocale]

    const created = await prisma.$transaction(async (tx) => {
      /// 1) MenuItem (label "base" = celui en locale d'édition pour cohérence
      ///    avec le reste du CMS web).
      const item = await tx.menuItem.create({
        data: {
          menuId: menu.id,
          label: body.label,
          order: insertOrder,
          enabled,
          isRoot: false,
          type: MenuItemType.LINK,
          navigationNodeKind: MenuNavigationNodeKind.PAGE,
        },
      })

      /// 2) MenuItemI18n (toutes les locales activées — placeholder = label fourni)
      for (const loc of locales) {
        await tx.menuItemI18n.create({
          data: {
            menuItemId: item.id,
            locale: loc,
            label: body.label,
            translationStatus:
              loc === requestedLocale
                ? TranslationStatus.ORIGINAL
                : TranslationStatus.MACHINE,
          },
        })
      }

      /// 3) SectionContent.data : on insère l'entrée pour **toutes** les
      ///    locales (icon/target identiques pour toutes — non localisés), en
      ///    DRAFT toujours, et en PUBLISHED si writeScope=published.
      ///    On part du `data` existant pour chaque (locale, status) et on y
      ///    pousse l'entrée de l'item — sans toucher aux autres entrées.
      const newDataItem = {
        menuItemId: item.id,
        target: body.target,
        icon: body.icon,
      }
      const targetStatuses: ContentStatus[] =
        writeScope === 'published'
          ? [ContentStatus.DRAFT, ContentStatus.PUBLISHED]
          : [ContentStatus.DRAFT]
      for (const loc of locales) {
        for (const status of targetStatuses) {
          const existing = await tx.sectionContent.findUnique({
            where: {
              sectionId_locale_status: { sectionId: section.id, locale: loc, status },
            },
          })
          const baseItems = existing
            ? (() => {
                const parsed = appMenuSectionDataSchema.safeParse(existing.data)
                return parsed.success ? parsed.data.items : []
              })()
            : []
          /// Idempotence : si l'item est déjà présent (cas réessai), on ne
          /// duplique pas — on remplace par la nouvelle config.
          const filtered = baseItems.filter((b) => b.menuItemId !== item.id)
          const merged = [...filtered, newDataItem]
          const dataPayload = { items: merged } as unknown as Prisma.InputJsonValue
          if (existing) {
            await tx.sectionContent.update({
              where: { id: existing.id },
              data: {
                data: dataPayload,
                updatedByUserId: session.userId,
              },
            })
          } else {
            await tx.sectionContent.create({
              data: {
                sectionId: section.id,
                locale: loc,
                status,
                data: dataPayload,
                updatedByUserId: session.userId,
                translationStatus:
                  loc === i18n.defaultLocale
                    ? TranslationStatus.ORIGINAL
                    : TranslationStatus.MACHINE,
              },
            })
          }
        }
      }

      return item
    })

    return NextResponse.json(
      {
        success: true,
        item: {
          id: created.id,
          order: created.order,
          enabled: created.enabled,
          label: created.label,
        },
        meta: { requestedLocale, writeScope },
      },
      { status: 201 },
    )
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid payload', issues: error.issues },
        { status: 400 },
      )
    }
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/flutter/shell/items POST]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 },
    )
  }
}
