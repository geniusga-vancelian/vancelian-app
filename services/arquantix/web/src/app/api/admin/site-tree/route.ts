import { NextResponse } from 'next/server'
import { prisma } from '@/lib/prisma'
import { getSessionFromCookie } from '@/lib/auth'
import {
  buildAdminSiteDisplayTreeFromPages,
  extractPrimaryMenuPageIdOrder,
  type SiteTreeGlobalCommonModuleRow,
  type SiteTreeNavRightRailRow,
} from '@/lib/cms/buildSiteTree'
import { resolveLabelWithFallback, DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'
import { getLocaleOrDefault } from '@/config/locales'
import {
  ensurePrimaryMenuLanguageSwitcher,
  menuItemTypeEnumHasLanguageSwitcher,
} from '@/lib/menu/ensurePrimaryMenuLanguageSwitcher'
import { injectBlogArticlesUnderArticleGabarit } from '@/lib/cms/injectBlogArticlesInAdminSiteTree'
import type { Page, PackagedProduct } from '@prisma/client'
import {
  aggregateI18nSiteSummary,
  computeNavActionButtonLabelCompleteness,
  computePageLocaleCompleteness,
  type LocaleCompletenessLevel,
  type PageCompletenessInput,
} from '@/lib/admin/pageLocaleCompleteness'
import {
  attachLocaleCompletenessToTree,
  attachRootMenuNavLinkCompleteness,
  type PrimaryMenuItemForNavLinkStrip,
} from '@/lib/admin/enrichSiteTreeI18n'
import type { Locale } from '@/config/locales'
import type { NextRequest } from 'next/server'
import { getAdminFooterLoadPayload } from '@/lib/cms/footerStorage'
import { computeFooterLocalesCompleteness } from '@/lib/admin/footerLocaleCompleteness'
import { parseCommonModulesDocument } from '@/lib/cms/commonModulesStorage'
import { computeCommonModuleLocalesCompleteness } from '@/lib/admin/commonModuleLocaleCompleteness'

type PageRow = Page & {
  packagedProduct: Pick<PackagedProduct, 'id' | 'slug' | 'productType'> | null
}

function isLanguageSwitcherMenuType(type: unknown): boolean {
  return String(type) === 'LANGUAGE_SWITCHER'
}

const primaryMenuForSiteTreeSelect = {
  menuItems: {
    orderBy: { order: 'asc' as const },
    select: {
      id: true,
      label: true,
      type: true,
      enabled: true,
      isRoot: true,
      pageId: true,
      order: true,
      buttonStyle: true,
      buttonAction: true,
      externalUrl: true,
      navigationNodeKind: true,
      openInNewTab: true,
      page: { select: { template: true, slug: true } },
      i18n: { select: { locale: true, label: true, translationStatus: true } },
    },
  },
} as const

/**
 * GET /api/admin/site-tree — arborescence CMS (lecture seule, lot 1).
 * Lot 6 : enrichissement `localeCompleteness` + `i18nSummary` (sans refonte backend).
 *
 * Query `treeOrder=structure` : n’applique pas le tri du menu primaire, pour que l’ordre
 * affiché coïncide avec `sort_order` / fratrie DB (boutons ↑↓ de la structure).
 */
export async function GET(request: NextRequest) {
  try {
    const session = await getSessionFromCookie()
    if (!session) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const [pages, blogArticles, primaryMenuFromTx, globalSettingsRow] = await Promise.all([
      prisma.page.findMany({
        orderBy: [{ parentId: 'asc' }, { sortOrder: 'asc' }, { createdAt: 'asc' }],
        include: {
          packagedProduct: {
            select: { id: true, slug: true, productType: true },
          },
          pageI18n: {
            select: { locale: true, title: true, description: true },
          },
          sections: {
            select: {
              id: true,
              contents: {
                select: { locale: true, status: true },
              },
            },
          },
        },
      }),
      prisma.article.findMany({
        orderBy: [{ publishedAt: 'desc' }, { updatedAt: 'desc' }],
        include: {
          i18n: true,
        },
      }),
      /**
       * Ensure + lecture du menu dans **une** transaction : avec un pooler type Neon,
       * un `ensure` puis un `findUnique` séparé peut lire une réplique qui n’a pas encore
       * la ligne `LANGUAGE_SWITCHER`, d’où bandeau « absent » alors que la migration est OK.
       */
      prisma.$transaction(async (tx) => {
        await ensurePrimaryMenuLanguageSwitcher(tx)
        return tx.menu.findUnique({
          where: { key: 'primary' },
          select: primaryMenuForSiteTreeSelect,
        })
      }),
      prisma.globalSettings.findFirst({ select: { footerJson: true, commonModulesJson: true } }),
    ])

    /**
     * Si l’enum est présent mais qu’aucune ligne LANGUAGE_SWITCHER n’apparaît (ex. ancien
     * contrôle `pg_enum` trop strict, ou ensure dans la tx n’ayant pas créé l’entrée),
     * on ré-exécute ensure **hors** transaction puis on recharge le menu une fois.
     */
    let primaryMenu = primaryMenuFromTx
    if (
      primaryMenu &&
      (await menuItemTypeEnumHasLanguageSwitcher()) &&
      !(primaryMenu.menuItems ?? []).some((i) => isLanguageSwitcherMenuType(i.type))
    ) {
      await ensurePrimaryMenuLanguageSwitcher()
      primaryMenu = await prisma.menu.findUnique({
        where: { key: 'primary' },
        select: primaryMenuForSiteTreeSelect,
      })
    }

    const treeLocale = getLocaleOrDefault(
      request.nextUrl.searchParams.get('locale') ?? DEFAULT_LOCALE,
    )

    const treeOrder = request.nextUrl.searchParams.get('treeOrder')
    const useMenuOrder = treeOrder !== 'structure'
    const homePageId =
      pages.find((p) => p.slug === 'home' || p.pageRole === 'HOME')?.id ?? null
    const blogPageId = pages.find((p) => p.slug === 'blog')?.id ?? null
    const menuItemsEnabled = (primaryMenu?.menuItems ?? []).filter((i) => i.enabled !== false)
    const primaryMenuPageIdOrder = useMenuOrder
      ? extractPrimaryMenuPageIdOrder(menuItemsEnabled, {
          homePageId,
          blogPageId,
        })
      : undefined

    const completenessInputs: PageCompletenessInput[] = pages.map((p) => ({
      id: p.id,
      template: p.template,
      title: p.title,
      description: p.description,
      pageI18n: p.pageI18n,
      sections: p.sections,
    }))

    const byPageId = new Map<string, Record<Locale, LocaleCompletenessLevel>>()
    for (const input of completenessInputs) {
      const { locales } = computePageLocaleCompleteness(input)
      byPageId.set(input.id, locales)
    }

    const i18nSummary = aggregateI18nSiteSummary(completenessInputs)

    const pageRows = pages.map((p) => {
      const { sections: _s, pageI18n: _i, ...row } = p
      return row as PageRow
    })

    const tree = attachRootMenuNavLinkCompleteness(
      injectBlogArticlesUnderArticleGabarit(
        attachLocaleCompletenessToTree(
          buildAdminSiteDisplayTreeFromPages(
            pageRows,
            primaryMenuPageIdOrder && primaryMenuPageIdOrder.length > 0
              ? primaryMenuPageIdOrder
              : undefined,
          ),
          byPageId,
        ),
        blogArticles,
      ),
      (primaryMenu?.menuItems ?? []) as PrimaryMenuItemForNavLinkStrip[],
      homePageId,
    )

    const navRightRail: SiteTreeNavRightRailRow[] = (primaryMenu?.menuItems ?? [])
      .filter((item) => {
        if (isLanguageSwitcherMenuType(item.type)) return true
        return item.type === 'BUTTON' && !(item.buttonAction && String(item.buttonAction).trim())
      })
      .sort((a, b) => a.order - b.order)
      .map((item) => {
        if (isLanguageSwitcherMenuType(item.type)) {
          return {
            kind: 'language_switcher' as const,
            id: item.id,
            order: item.order,
            enabled: item.enabled !== false,
            label: resolveLabelWithFallback({
              requestedLocale: treeLocale,
              baseLabel: item.label || '',
              i18nRows: (item.i18n ?? []).map((r) => ({
                locale: r.locale,
                label: r.label,
              })),
            }),
          }
        }
        return {
          kind: 'button' as const,
          id: item.id,
          order: item.order,
          enabled: item.enabled !== false,
          buttonStyle: item.buttonStyle,
          externalUrl: item.externalUrl,
          label: resolveLabelWithFallback({
            requestedLocale: treeLocale,
            baseLabel: item.label || '',
            i18nRows: (item.i18n ?? []).map((r) => ({
              locale: r.locale,
              label: r.label,
            })),
          }),
          localeCompleteness: computeNavActionButtonLabelCompleteness(item.label || '', [
            ...(item.i18n ?? []).map((r) => ({
              locale: r.locale,
              label: r.label,
              translationStatus: String(r.translationStatus),
            })),
          ]),
        }
      })

    const hasLanguageSwitcherMenuItem = (primaryMenu?.menuItems ?? []).some((i) =>
      isLanguageSwitcherMenuType(i.type),
    )

    const footerPayload = getAdminFooterLoadPayload(globalSettingsRow?.footerJson ?? {})
    const commonDoc = parseCommonModulesDocument(globalSettingsRow?.commonModulesJson ?? null)
    const optionalCommonRows: SiteTreeGlobalCommonModuleRow[] = commonDoc.modules
      .slice()
      .sort((a, b) => a.label.localeCompare(b.label, 'fr'))
      .map((m) => ({
        id: m.id,
        kind: 'common_reusable' as const,
        label: m.label,
        description: `Réutilisable sur les pages (type « ${m.sectionKey} »).`,
        sectionKey: m.sectionKey,
        localeCompleteness: computeCommonModuleLocalesCompleteness(m),
        editHref: `/admin/pages/common-module/${m.id}`,
        systemLocked: false,
      }))

    const globalCommonModules: SiteTreeGlobalCommonModuleRow[] = [
      {
        id: 'footer',
        kind: 'footer',
        label: 'Footer',
        description: 'Pied de page affiché sur tout le site public (liens, newsletter, mentions).',
        localeCompleteness: computeFooterLocalesCompleteness(footerPayload.locales),
        editHref: '/admin/pages/footer',
        systemLocked: true,
      },
      ...optionalCommonRows,
    ]

    return NextResponse.json({
      tree,
      navRightRail,
      globalCommonModules,
      i18nSummary,
      meta: {
        generatedAt: new Date().toISOString(),
        pageCount: pages.length,
        primaryMenuExists: primaryMenu != null,
        hasLanguageSwitcherMenuItem,
      },
    })
  } catch (error) {
    console.error('Error building site tree:', error)
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 },
    )
  }
}
