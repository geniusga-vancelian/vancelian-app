import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus, TranslationStatus, type Prisma } from '@prisma/client'
import { z } from 'zod'

import { getSessionFromCookie } from '@/lib/auth'
import { prisma } from '@/lib/prisma'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'
import { resolveVaultSectionContent } from '@/lib/cms/resolveVaultSectionContent'
import {
  APP_MAIN_TABS_MENU_KEY,
  APP_MAIN_TABS_PAGE_SLUG,
  APP_MENU_SECTION_KEY,
  APP_MOBILE_ICON_KEYS,
  appMobileTargetSchema,
  appMenuSectionDataSchema,
} from '@/lib/mobile/appShellModel'

/**
 * GET /api/admin/flutter/shell?locale=…
 *
 * Renvoie l'état **éditable** du shell pour la locale demandée, avec fallback
 * standard `requested → defaultLocale → any` (cf. résolveur Vault).
 *
 * Retourne, par item :
 * - `id` (`MenuItem.id`), `order`, `enabled`
 * - `label` localisé (DRAFT-prio pour l'admin, fallback compris)
 * - `icon` + `target` (lus depuis le `SectionContent.data` du `Page` système)
 *
 * `meta` : couverture des locales, locale servie, isFallback.
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (request.nextUrl.searchParams.get('locale') || '').trim() || i18n.defaultLocale

    const [page, menu] = await Promise.all([
      prisma.page.findUnique({
        where: { slug: APP_MAIN_TABS_PAGE_SLUG },
        include: {
          sections: {
            where: { key: APP_MENU_SECTION_KEY },
            include: { contents: true },
            take: 1,
          },
        },
      }),
      prisma.menu.findUnique({
        where: { key: APP_MAIN_TABS_MENU_KEY },
        include: {
          menuItems: { include: { i18n: true }, orderBy: { order: 'asc' } },
          i18n: true,
        },
      }),
    ])

    if (!page || !menu) {
      return NextResponse.json(
        {
          error: 'App shell not seeded',
          meta: { requestedLocale, defaultLocale: i18n.defaultLocale },
        },
        { status: 404 },
      )
    }

    const allContents = page.sections[0]?.contents ?? []
    const picked = resolveVaultSectionContent(allContents, {
      requestedLocale,
      defaultLocale: i18n.defaultLocale,
      mode: 'either_draft_first',
    })
    const parsed = picked ? appMenuSectionDataSchema.safeParse(picked.data) : null
    const dataItems = parsed?.success ? parsed.data.items : []

    const items = menu.menuItems.map((mi) => {
      const cfg = dataItems.find((d) => d.menuItemId === mi.id)
      const labelI18n =
        mi.i18n.find((r) => r.locale === requestedLocale) ??
        mi.i18n.find((r) => r.locale === i18n.defaultLocale) ??
        mi.i18n[0] ??
        null
      return {
        id: mi.id,
        order: mi.order,
        enabled: mi.enabled,
        label: labelI18n?.label ?? mi.label ?? '',
        labelLocale: labelI18n?.locale ?? null,
        icon: cfg?.icon ?? null,
        target: cfg?.target ?? null,
      }
    })

    return NextResponse.json({
      menu: { id: menu.id, key: menu.key, name: menu.name },
      items,
      meta: {
        requestedLocale,
        defaultLocale: i18n.defaultLocale,
        supportedLocales: i18n.supportedLocales,
        contentLocale: picked?.locale ?? null,
        contentStatus: picked?.status ?? null,
        localeCoverage: Array.from(new Set(allContents.map((c) => c.locale))),
        isFallback: picked != null && picked.locale !== requestedLocale,
        availableIcons: APP_MOBILE_ICON_KEYS,
      },
    })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/flutter/shell GET]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 },
    )
  }
}

const patchSchema = z.object({
  items: z
    .array(
      z.object({
        id: z.string().min(1),
        label: z.string().optional(),
        icon: z.enum(APP_MOBILE_ICON_KEYS).optional(),
        target: appMobileTargetSchema.optional(),
        enabled: z.boolean().optional(),
        order: z.number().int().nonnegative().optional(),
      }),
    )
    .min(1),
})

/**
 * PATCH /api/admin/flutter/shell?locale=…&status=draft|published
 *
 * Met à jour pour la locale demandée :
 * - `MenuItem.{enabled, order, label}` (label = champ "base")
 * - `MenuItemI18n.{label}` (locale)
 * - `SectionContent.data.items[*].{icon, target}` (DRAFT par défaut, ou DRAFT+PUBLISHED si `status=published`)
 *
 * **Atomique** : tout passe dans une `prisma.$transaction`. Si l'app shell n'a
 * pas été seedé (`POST /seed`) la requête renvoie 404.
 */
export async function PATCH(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }
    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (request.nextUrl.searchParams.get('locale') || '').trim() || i18n.defaultLocale
    const writeScope = request.nextUrl.searchParams.get('status') === 'published' ? 'published' : 'draft'

    if (
      i18n.multilingualEnabled &&
      !i18n.supportedLocales.includes(requestedLocale as (typeof i18n.supportedLocales)[number])
    ) {
      return NextResponse.json(
        { error: `Locale "${requestedLocale}" not enabled` },
        { status: 400 },
      )
    }

    const body = patchSchema.parse(await request.json())

    const [page, menu] = await Promise.all([
      prisma.page.findUnique({
        where: { slug: APP_MAIN_TABS_PAGE_SLUG },
        include: { sections: { where: { key: APP_MENU_SECTION_KEY }, take: 1 } },
      }),
      prisma.menu.findUnique({ where: { key: APP_MAIN_TABS_MENU_KEY } }),
    ])
    if (!page || !menu) {
      return NextResponse.json(
        { error: 'App shell not seeded — call POST /api/admin/flutter/shell/seed first' },
        { status: 404 },
      )
    }
    const section = page.sections[0]
    if (!section) {
      return NextResponse.json({ error: 'Section missing' }, { status: 500 })
    }

    /// Lecture du DRAFT existant (point de départ pour la mise à jour data).
    const draftContent = await prisma.sectionContent.findUnique({
      where: {
        sectionId_locale_status: {
          sectionId: section.id,
          locale: requestedLocale,
          status: ContentStatus.DRAFT,
        },
      },
    })
    const baseDataParsed = draftContent
      ? appMenuSectionDataSchema.safeParse(draftContent.data)
      : null
    const baseItems = baseDataParsed?.success ? baseDataParsed.data.items : []

    /// Réconciliation `data.items` : on conserve les entrées existantes pour les
    /// items non touchés ; on remplace target/icon pour les items présents dans
    /// le payload.
    const itemUpdatesById = new Map(body.items.map((u) => [u.id, u]))
    const mergedDataMap = new Map<
      string,
      { menuItemId: string; target: NonNullable<(typeof body.items)[number]['target']>; icon: NonNullable<(typeof body.items)[number]['icon']> }
    >()
    for (const it of baseItems) mergedDataMap.set(it.menuItemId, it)
    for (const upd of body.items) {
      const prev = mergedDataMap.get(upd.id)
      const target = upd.target ?? prev?.target
      const icon = upd.icon ?? prev?.icon
      if (!target || !icon) {
        return NextResponse.json(
          {
            error: `Item ${upd.id} missing target/icon (no previous draft found). Pass full target+icon for new items.`,
          },
          { status: 400 },
        )
      }
      mergedDataMap.set(upd.id, { menuItemId: upd.id, target, icon })
    }
    const mergedItems = Array.from(mergedDataMap.values())

    await prisma.$transaction(async (tx) => {
      /// 1) MenuItem (label base, enabled, order)
      for (const upd of body.items) {
        const data: Prisma.MenuItemUpdateInput = {}
        if (upd.label !== undefined && requestedLocale === i18n.defaultLocale) {
          /// Le `label` "base" colle au libellé en locale par défaut, pour
          /// rester cohérent avec le reste du CMS web (admin/pages/menu).
          data.label = upd.label
        }
        if (upd.enabled !== undefined) data.enabled = upd.enabled
        if (upd.order !== undefined) data.order = upd.order
        if (Object.keys(data).length > 0) {
          await tx.menuItem.update({ where: { id: upd.id }, data })
        }
      }

      /// 2) MenuItemI18n (label par locale)
      for (const upd of body.items) {
        if (upd.label === undefined) continue
        await tx.menuItemI18n.upsert({
          where: {
            menuItemId_locale: {
              menuItemId: upd.id,
              locale: requestedLocale,
            },
          },
          update: {
            label: upd.label,
            translationStatus:
              requestedLocale === i18n.defaultLocale
                ? TranslationStatus.ORIGINAL
                : TranslationStatus.APPROVED,
          },
          create: {
            menuItemId: upd.id,
            locale: requestedLocale,
            label: upd.label,
            translationStatus:
              requestedLocale === i18n.defaultLocale
                ? TranslationStatus.ORIGINAL
                : TranslationStatus.APPROVED,
          },
        })
      }

      /// 3) SectionContent.data.items (icon/target par locale + statut)
      const dataPayload = { items: mergedItems } as unknown as Prisma.InputJsonValue
      const targetStatuses: ContentStatus[] =
        writeScope === 'published'
          ? [ContentStatus.DRAFT, ContentStatus.PUBLISHED]
          : [ContentStatus.DRAFT]
      for (const status of targetStatuses) {
        await tx.sectionContent.upsert({
          where: {
            sectionId_locale_status: {
              sectionId: section.id,
              locale: requestedLocale,
              status,
            },
          },
          update: {
            data: dataPayload,
            updatedByUserId: session.userId,
            translationStatus:
              requestedLocale === i18n.defaultLocale
                ? TranslationStatus.ORIGINAL
                : TranslationStatus.APPROVED,
          },
          create: {
            sectionId: section.id,
            locale: requestedLocale,
            status,
            data: dataPayload,
            updatedByUserId: session.userId,
            translationStatus:
              requestedLocale === i18n.defaultLocale
                ? TranslationStatus.ORIGINAL
                : TranslationStatus.APPROVED,
          },
        })
      }
    })

    return NextResponse.json({
      success: true,
      meta: { requestedLocale, writeScope },
    })
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: 'Invalid payload', issues: error.issues },
        { status: 400 },
      )
    }
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/admin/flutter/shell PATCH]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', detail: err.message },
      { status: 500 },
    )
  }
}
