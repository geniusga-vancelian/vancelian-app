/**
 * Server-side helper to fetch the primary menu with enabled items
 * Used by NavBar component
 */

import { prisma } from '@/lib/prisma'
import { computeMenuItemUrlPath } from './computeUrlPath'
import { resolveLabelWithFallback, DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'
import { getLocaleOrDefault, type Locale } from '@/config/locales'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'
import { ensurePrimaryMenuLanguageSwitcher } from '@/lib/menu/ensurePrimaryMenuLanguageSwitcher'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { megaMenuPayloadFromChildPages, type MegaMenuPayload } from '@/lib/menu/megaMenuFromChildPages'
import {
  parseNavigationNodeKind,
  type NavigationNodeKind,
} from '@/lib/menu/navigationNodeKind'

const LANGUAGE_SWITCHER_FALLBACK_ID = 'primary-nav-language-switcher-fallback'

/** Toujours exposer la langue dans la zone droite si aucune ligne DB active ne le fait. */
export function injectLanguageSwitcherIfMissing(items: MenuItem[], locale: Locale): MenuItem[] {
  if (items.some((i) => i.type === 'LANGUAGE_SWITCHER')) {
    return items
  }
  const maxOrder = items.reduce((m, i) => Math.max(m, i.order ?? 0), -1)
  return [
    ...items,
    {
      id: LANGUAGE_SWITCHER_FALLBACK_ID,
      label: siteCommonCta(locale, 'fallback_menu_lang'),
      urlPath: '#',
      order: maxOrder + 1,
      type: 'LANGUAGE_SWITCHER' as const,
      enabled: true,
    },
  ]
}

function applyLanguageSwitcherPolicy(
  items: MenuItem[],
  locale: Locale,
  languageSwitcherEnabled: boolean,
): MenuItem[] {
  const stripped = items.filter((i) => i.type !== 'LANGUAGE_SWITCHER')
  if (!languageSwitcherEnabled) {
    return stripped
  }
  return injectLanguageSwitcherIfMissing(stripped, locale)
}

export type GetPrimaryMenuOptions = {
  /** Faux : retire LANGUAGE_SWITCHER (DB + fallback injecté). */
  languageSwitcherEnabled?: boolean
}

/**
 * Pages Vault Builder = détail produit sous `/{locale}/projects/{slug}`.
 * Elles ne doivent pas apparaître comme entrées du menu primaire (hub « Projets » + cartes suffisent).
 */
function isVaultBuilderNavExcludedPage(page: { template: string } | null | undefined): boolean {
  return page != null && page.template === VAULT_BUILDER_TEMPLATE
}

/** Entrée lien vers une page CMS dont le parent n’est pas null : réservée au méga-menu, pas à la barre niveau 1. */
function isNestedCmsPageNavItem(item: {
  type?: string | null
  page: { parentId: string | null } | null
}): boolean {
  const itemType = item.type || 'LINK'
  if (itemType === 'LANGUAGE_SWITCHER') return false
  return item.page != null && item.page.parentId != null
}

export interface MenuItem {
  id: string
  label: string
  urlPath: string
  order: number
  type: 'LINK' | 'BUTTON' | 'LANGUAGE_SWITCHER'
  isRoot?: boolean
  enabled?: boolean
  buttonStyle?: string | null
  buttonAction?: string | null
  externalUrl?: string | null
  /** Sémantique navigation niveau 1 (défaut `PAGE`). */
  navigationNodeKind?: NavigationNodeKind
  openInNewTab?: boolean
  /** Sous-pages directes (≥2) : panneau méga-menu desktop. */
  megaMenu?: MegaMenuPayload | null
}

/**
 * Get primary menu with enabled items ordered
 * Returns empty array if menu not found or no enabled items
 * @param locale - Locale for label resolution (default: site default)
 */
export async function getPrimaryMenu(
  locale?: string,
  options?: GetPrimaryMenuOptions,
): Promise<MenuItem[]> {
  const requestedLocale = (locale ? getLocaleOrDefault(locale) : DEFAULT_LOCALE) as Locale
  const languageSwitcherEnabled = options?.languageSwitcherEnabled !== false

  try {
    try {
      await ensurePrimaryMenuLanguageSwitcher()
    } catch (ensureErr) {
      console.warn('[getPrimaryMenu] ensurePrimaryMenuLanguageSwitcher:', ensureErr)
    }

    const menu = await prisma.menu.findUnique({
      where: { key: 'primary' },
      include: {
        menuItems: {
          where: { enabled: true },
          orderBy: { order: 'asc' },
          include: {
            page: true,
            i18n: true,
          },
        },
      },
    })

    if (!menu || menu.menuItems.length === 0) {
      return applyLanguageSwitcherPolicy(
        [
          {
            id: 'fallback-home',
            label: 'Home',
            urlPath: `/${requestedLocale}`,
            type: 'LINK',
            isRoot: true,
            enabled: true,
            order: 0,
          },
        ],
        requestedLocale,
        languageSwitcherEnabled,
      )
    }

    const topLevelMenuItems = menu.menuItems.filter((item) => {
      if (isVaultBuilderNavExcludedPage(item.page)) return false
      if (isNestedCmsPageNavItem(item)) return false
      return true
    })

    const parentPageIds = topLevelMenuItems
      .map((i) => i.page?.id)
      .filter((id): id is string => Boolean(id))

    const childPages =
      parentPageIds.length > 0
        ? await prisma.page.findMany({
            where: {
              parentId: { in: parentPageIds },
              showInNav: true,
              showInMegaMenu: true,
              NOT: { template: VAULT_BUILDER_TEMPLATE },
            },
            orderBy: [{ parentId: 'asc' }, { sortOrder: 'asc' }, { slug: 'asc' }],
            include: {
              pageI18n: {
                select: {
                  locale: true,
                  title: true,
                  description: true,
                  navMegaCategory: true,
                  navMegaDescription: true,
                },
              },
              navMegaIconMedia: { select: { key: true, url: true } },
            },
          })
        : []

    const childrenByParent = new Map<string, typeof childPages>()
    for (const c of childPages) {
      const pid = c.parentId
      if (!pid) continue
      if (!childrenByParent.has(pid)) childrenByParent.set(pid, [])
      childrenByParent.get(pid)!.push(c)
    }

    const megaByParentId = new Map<string, MegaMenuPayload | null>()
    for (const pid of parentPageIds) {
      const kids = childrenByParent.get(pid) ?? []
      megaByParentId.set(
        pid,
        await megaMenuPayloadFromChildPages(kids, requestedLocale),
      )
    }

    const normalizedItems = topLevelMenuItems
      .map((item) => {
        // Default type to LINK for existing items that don't have type set
        const itemType = item.type || 'LINK'

        if (itemType === 'LANGUAGE_SWITCHER') {
          const resolvedLabel = resolveLabelWithFallback({
            requestedLocale,
            baseLabel: item.label,
            i18nRows: item.i18n.map((i18n) => ({
              locale: i18n.locale,
              label: i18n.label,
            })),
          })
          return {
            id: item.id,
            label: resolvedLabel,
            urlPath: '#',
            order: item.order,
            type: 'LANGUAGE_SWITCHER' as const,
            enabled: item.enabled,
          } satisfies MenuItem
        }

        const buttonStyle = (item.buttonStyle || '').toLowerCase()
        const buttonLooksLikeNavLink =
          itemType === 'BUTTON' &&
          !item.buttonAction &&
          (buttonStyle === '' || buttonStyle === 'text' || buttonStyle === 'ghost' || buttonStyle === 'link') &&
          (!!item.page ||
            !item.externalUrl ||
            item.externalUrl.trim() === '' ||
            item.externalUrl.trim() === '#' ||
            item.externalUrl.trim().startsWith('/'))

        const normalizedType: MenuItem['type'] = buttonLooksLikeNavLink
          ? 'LINK'
          : (itemType as MenuItem['type'])

        const navKind = parseNavigationNodeKind(
          (item as { navigationNodeKind?: string | null }).navigationNodeKind,
        )

        if (navKind === 'GROUP' && item.isRoot) {
          console.warn(
            `MenuItem ${item.id} (${item.label}): GROUP ne peut pas être isRoot — entrée ignorée.`,
          )
          return null
        }

        const computedInternalPath = computeMenuItemUrlPath(
          item.isRoot,
          item.page?.slug || null,
          requestedLocale,
          item.page?.template,
        )

        let urlPath: string
        if (navKind === 'EXTERNAL_LINK') {
          urlPath = (item.externalUrl || '').trim() || '#'
        } else if (navKind === 'GROUP') {
          urlPath = '#'
        } else if (normalizedType === 'BUTTON') {
          urlPath = item.externalUrl || computedInternalPath || '#'
        } else {
          urlPath = computedInternalPath
        }

        if (normalizedType === 'LINK') {
          if (navKind === 'GROUP' && !item.page) {
            console.warn(
              `MenuItem ${item.id} (${item.label}) : GROUP sans page — entrée ignorée.`,
            )
            return null
          }
          if (navKind === 'EXTERNAL_LINK' && !(item.externalUrl || '').trim()) {
            console.warn(
              `MenuItem ${item.id} (${item.label}) : EXTERNAL_LINK sans URL — entrée ignorée.`,
            )
            return null
          }
          if (navKind === 'PAGE' && !item.isRoot && !item.page) {
            console.warn(`MenuItem ${item.id} (${item.label}) is invalid: not root but no page`)
            return null
          }
        }
        
        // Resolve label with i18n
        const resolvedLabel = resolveLabelWithFallback({
          requestedLocale,
          baseLabel: item.label,
          i18nRows: item.i18n.map((i18n) => ({
            locale: i18n.locale,
            label: i18n.label,
          })),
        })
        
        const canAttachMega =
          Boolean(item.page?.id) &&
          normalizedType === 'LINK' &&
          (navKind === 'PAGE' || navKind === 'GROUP' || navKind === 'EXTERNAL_LINK')

        const megaMenu = canAttachMega
          ? megaByParentId.get(item.page!.id) ?? null
          : null

        return {
          id: item.id,
          label: resolvedLabel,
          urlPath,
          order: item.order,
          type: normalizedType,
          isRoot: item.isRoot,
          enabled: item.enabled,
          buttonStyle: item.buttonStyle,
          buttonAction: item.buttonAction,
          externalUrl: item.externalUrl,
          navigationNodeKind: navKind,
          openInNewTab: (item as { openInNewTab?: boolean }).openInNewTab ?? false,
          megaMenu,
        } satisfies MenuItem
      })
      .filter((item): item is NonNullable<typeof item> => item !== null)

    const hasBlogEntry = normalizedItems.some((item) => {
      const path = (item.urlPath || '').toLowerCase()
      return path === '/blog' || path.endsWith('/blog')
    })
    if (hasBlogEntry) {
      return applyLanguageSwitcherPolicy(normalizedItems, requestedLocale, languageSwitcherEnabled)
    }

    const blogPage = await prisma.page.findUnique({
      where: { slug: 'blog' },
      select: { slug: true, parentId: true },
    })
    if (!blogPage || blogPage.parentId !== null) {
      return applyLanguageSwitcherPolicy(normalizedItems, requestedLocale, languageSwitcherEnabled)
    }

    const maxOrder = normalizedItems.reduce((max, item) => Math.max(max, item.order), 0)
    return applyLanguageSwitcherPolicy(
      [
        ...normalizedItems,
        {
          id: 'fallback-blog',
          label: 'Blog',
          urlPath: `/${requestedLocale}/blog`,
          order: maxOrder + 1,
          type: 'LINK',
          isRoot: false,
          enabled: true,
        },
      ],
      requestedLocale,
      languageSwitcherEnabled,
    )
  } catch (error) {
    console.error('Error fetching primary menu:', error)
    return applyLanguageSwitcherPolicy(
      [
        {
          id: 'fallback-home',
          label: 'Home',
          urlPath: `/${requestedLocale}`,
          type: 'LINK',
          isRoot: true,
          enabled: true,
          order: 0,
        },
      ],
      requestedLocale,
      languageSwitcherEnabled,
    )
  }
}

