import { NextRequest, NextResponse } from 'next/server'
import { ContentStatus } from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'
import { resolveVaultSectionContent } from '@/lib/cms/resolveVaultSectionContent'
import {
  APP_MAIN_TABS_MENU_KEY,
  APP_MAIN_TABS_PAGE_SLUG,
  APP_MENU_SECTION_KEY,
  appMenuSectionDataSchema,
  type AppShellPayload,
  type AppShellTabPayload,
} from '@/lib/mobile/appShellModel'

/**
 * GET /api/mobile/flutter/shell?locale=…
 *
 * Renvoie la **tab bar de l'app Flutter** (et structure du shell) pour la
 * locale demandée, avec fallback locale standard.
 *
 * Contrat :
 * ```
 * { tabs: [{ id, order, enabled, label, icon, target }], meta: { … } }
 * ```
 *
 * Comportement :
 * - Status par défaut : PUBLISHED uniquement (mobile public).
 * - Fallback locale : `requested → defaultLocale → any` (cf. résolveur Vault).
 * - Si aucun contenu n'est trouvé (cas avant 1er seed), renvoie 404 — l'app
 *   tombe alors sur son fallback Dart compilé sans dégrader l'UX.
 */
export async function GET(request: NextRequest) {
  try {
    const i18n = await getSiteI18nSettingsUncached()
    const requestedLocale =
      (request.nextUrl.searchParams.get('locale') || '').trim() || i18n.defaultLocale

    /// On charge en parallèle :
    /// (1) le `Page` système porteur des cibles/icônes (via `Section` + `SectionContent` toutes locales)
    /// (2) le `Menu` de la tab bar avec ses items + i18n labels
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
          menuItems: {
            include: { i18n: true },
            orderBy: { order: 'asc' },
          },
        },
      }),
    ])

    if (!page || !menu) {
      return NextResponse.json(
        {
          error: 'App shell not configured',
          meta: {
            requestedLocale,
            defaultLocale: i18n.defaultLocale,
          },
        },
        { status: 404 },
      )
    }

    const allContents = page.sections[0]?.contents ?? []
    const picked = resolveVaultSectionContent(allContents, {
      requestedLocale,
      defaultLocale: i18n.defaultLocale,
      mode: ContentStatus.PUBLISHED,
    })
    if (!picked) {
      return NextResponse.json(
        {
          error: 'No published shell content',
          meta: {
            requestedLocale,
            defaultLocale: i18n.defaultLocale,
          },
        },
        { status: 404 },
      )
    }

    const parsed = appMenuSectionDataSchema.safeParse(picked.data)
    const items = parsed.success ? parsed.data.items : []

    /// Map item Prisma → tab payload, avec fallback de label requested → default → label « base ».
    const itemById = new Map(menu.menuItems.map((it) => [it.id, it]))

    const tabs: AppShellTabPayload[] = []
    for (const cfg of items) {
      const mi = itemById.get(cfg.menuItemId)
      if (!mi) continue
      if (mi.enabled === false) continue
      const i18nRow =
        mi.i18n.find((r) => r.locale === requestedLocale) ??
        mi.i18n.find((r) => r.locale === i18n.defaultLocale) ??
        mi.i18n[0] ??
        null
      const label = (i18nRow?.label ?? mi.label ?? '').trim()
      tabs.push({
        id: mi.id,
        order: mi.order,
        enabled: mi.enabled,
        label,
        icon: cfg.icon,
        target: cfg.target,
      })
    }

    tabs.sort((a, b) => a.order - b.order)

    const payload: AppShellPayload & { meta: Record<string, unknown> } = {
      tabs,
      meta: {
        requestedLocale,
        contentLocale: picked.locale,
        defaultLocale: i18n.defaultLocale,
        supportedLocales: i18n.supportedLocales,
      },
    }

    return NextResponse.json(payload, {
      headers: {
        'Cache-Control': 'public, s-maxage=30, stale-while-revalidate=120',
      },
    })
  } catch (error) {
    const err = error instanceof Error ? error : new Error(String(error))
    console.error('[api/mobile/flutter/shell]', err.message, err.stack)
    return NextResponse.json(
      { error: 'Internal server error', message: 'The request could not be completed.' },
      { status: 500, headers: { 'Content-Type': 'application/json; charset=utf-8' } },
    )
  }
}
