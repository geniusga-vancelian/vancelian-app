/**
 * Garantit la présence des entités CMS pour la **tab bar de l'app Flutter** :
 * - `Menu(key='app_main_tabs')` + `MenuI18n` (un par locale activée)
 * - `MenuItem` (un par tab) + `MenuItemI18n` (label par locale activée)
 * - `Page(slug='app:main-tabs', template='app_menu', isSystemPage=true)`
 * - `Section(key='app_menu_v1')` + `SectionContent` (status PUBLISHED + DRAFT
 *   par locale activée) avec `data = { items: [{ menuItemId, target, icon }] }`
 *
 * **Idempotent** : un second appel ne crée rien de nouveau et ne supprime rien.
 * Si l'admin a déjà personnalisé les libellés/cibles, on **ne les écrase pas**.
 *
 * Cette fonction n'introduit **aucune migration Prisma** — elle réutilise les
 * tables existantes (cf. `services/arquantix/web/prisma/schema.prisma`).
 */
import {
  ContentStatus,
  MenuItemType,
  MenuNavigationNodeKind,
  PageRole,
  TranslationStatus,
  type Prisma,
} from '@prisma/client'

import { prisma } from '@/lib/prisma'
import { calculateUrlPath } from '@/lib/utils/slugify'
import { getSiteI18nSettingsUncached } from '@/lib/i18n/siteI18nSettings'
import {
  APP_MAIN_TABS_MENU_KEY,
  APP_MAIN_TABS_PAGE_SLUG,
  APP_MENU_SCHEMA_VERSION,
  APP_MENU_SECTION_KEY,
  APP_MENU_TEMPLATE,
  DEFAULT_APP_MAIN_TABS,
} from './appShellModel'

export type EnsureAppMainTabsResult = {
  menuId: string
  pageId: string
  sectionId: string
  createdMenu: boolean
  createdPage: boolean
  createdItems: number
  createdContents: number
}

export async function ensureAppMainTabs(): Promise<EnsureAppMainTabsResult> {
  const i18n = await getSiteI18nSettingsUncached()
  const locales = i18n.supportedLocales.length > 0 ? i18n.supportedLocales : [i18n.defaultLocale]
  const defaultLocale = i18n.defaultLocale

  let createdMenu = false
  let createdPage = false
  let createdItems = 0
  let createdContents = 0

  // 1) Menu + MenuI18n
  let menu = await prisma.menu.findUnique({
    where: { key: APP_MAIN_TABS_MENU_KEY },
    include: { i18n: true, menuItems: true },
  })
  if (!menu) {
    menu = await prisma.menu.create({
      data: {
        key: APP_MAIN_TABS_MENU_KEY,
        name: 'App — Onglets principaux',
      },
      include: { i18n: true, menuItems: true },
    })
    createdMenu = true
  }
  for (const loc of locales) {
    const exists = menu.i18n.find((r) => r.locale === loc)
    if (exists) continue
    await prisma.menuI18n.create({
      data: {
        menuId: menu.id,
        locale: loc,
        name:
          loc === defaultLocale
            ? 'App — Onglets principaux'
            : 'App — Main tabs',
        translationStatus: loc === defaultLocale
          ? TranslationStatus.ORIGINAL
          : TranslationStatus.MACHINE,
      },
    })
  }

  // 2) Page système porteuse de la cible/icône (non localisée — mais une row par locale par cohérence i18n)
  let page = await prisma.page.findUnique({
    where: { slug: APP_MAIN_TABS_PAGE_SLUG },
    include: { sections: { include: { contents: true } } },
  })
  if (!page) {
    page = await prisma.page.create({
      data: {
        slug: APP_MAIN_TABS_PAGE_SLUG,
        urlPath: calculateUrlPath(APP_MAIN_TABS_PAGE_SLUG),
        title: 'App — Onglets principaux',
        description: 'Configuration des onglets principaux de l’app Flutter.',
        template: APP_MENU_TEMPLATE,
        themeColor: 'dark',
        pageRole: PageRole.STANDARD,
        showInNav: false,
        showInMegaMenu: false,
        isSystemPage: true,
      },
      include: { sections: { include: { contents: true } } },
    })
    createdPage = true
  }

  // 3) Section
  let section = page.sections.find((s) => s.key === APP_MENU_SECTION_KEY)
  if (!section) {
    section = await prisma.section.create({
      data: {
        pageId: page.id,
        key: APP_MENU_SECTION_KEY,
        order: 0,
        schemaVersion: APP_MENU_SCHEMA_VERSION,
      },
      include: { contents: true },
    })
  }

  // 4) MenuItems + i18n
  /// Une réconciliation par `(menu, order)` : on n'écrase pas un libellé déjà
  /// modifié par l'admin, on ne crée que les items absents et leurs i18n
  /// manquants pour les locales activées.
  const existingItems = await prisma.menuItem.findMany({
    where: { menuId: menu.id },
    include: { i18n: true },
    orderBy: { order: 'asc' },
  })

  const itemByOrder = new Map<number, (typeof existingItems)[number]>()
  for (const it of existingItems) itemByOrder.set(it.order, it)

  const seededItems: { id: string; key: string; order: number }[] = []
  for (const tab of DEFAULT_APP_MAIN_TABS) {
    let item = itemByOrder.get(tab.order)
    if (!item) {
      item = await prisma.menuItem.create({
        data: {
          menuId: menu.id,
          label: tab.labels[defaultLocale] ?? tab.labels.en ?? tab.key,
          order: tab.order,
          enabled: true,
          isRoot: false,
          type: MenuItemType.LINK,
          navigationNodeKind: MenuNavigationNodeKind.PAGE,
        },
        include: { i18n: true },
      })
      createdItems += 1
    }
    /// MenuItemI18n manquants
    for (const loc of locales) {
      const has = item.i18n.find((r) => r.locale === loc)
      if (has) continue
      const label = tab.labels[loc] ?? tab.labels[defaultLocale] ?? tab.labels.en ?? tab.key
      await prisma.menuItemI18n.create({
        data: {
          menuItemId: item.id,
          locale: loc,
          label,
          translationStatus: loc === defaultLocale
            ? TranslationStatus.ORIGINAL
            : TranslationStatus.MACHINE,
        },
      })
    }
    seededItems.push({ id: item.id, key: tab.key, order: tab.order })
  }

  // 5) SectionContent : data = { items: [{ menuItemId, target, icon }] }
  /// On préserve toute personnalisation existante : si une ligne existe pour
  /// `(section, locale, status)` avec des items, on ne la touche pas.
  /// Sinon on construit une donnée par défaut alignée sur `DEFAULT_APP_MAIN_TABS`.
  const sortedSeed = [...DEFAULT_APP_MAIN_TABS].sort((a, b) => a.order - b.order)
  const dataItems = sortedSeed
    .map((tab) => {
      const seeded = seededItems.find((s) => s.order === tab.order)
      if (!seeded) return null
      return {
        menuItemId: seeded.id,
        target: tab.target,
        icon: tab.icon,
      }
    })
    .filter((x): x is { menuItemId: string; target: typeof sortedSeed[number]['target']; icon: typeof sortedSeed[number]['icon'] } => x != null)

  const dataPayload = { items: dataItems } as unknown as Prisma.InputJsonValue
  const targetStatuses: ContentStatus[] = [ContentStatus.DRAFT, ContentStatus.PUBLISHED]
  for (const loc of locales) {
    for (const status of targetStatuses) {
      const existing = await prisma.sectionContent.findUnique({
        where: {
          sectionId_locale_status: { sectionId: section.id, locale: loc, status },
        },
      })
      if (existing) continue
      await prisma.sectionContent.create({
        data: {
          sectionId: section.id,
          locale: loc,
          status,
          data: dataPayload,
          translationStatus: loc === defaultLocale
            ? TranslationStatus.ORIGINAL
            : TranslationStatus.MACHINE,
        },
      })
      createdContents += 1
    }
  }

  return {
    menuId: menu.id,
    pageId: page.id,
    sectionId: section.id,
    createdMenu,
    createdPage,
    createdItems,
    createdContents,
  }
}
