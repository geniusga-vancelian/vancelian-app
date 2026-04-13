/**
 * Server-side helper to fetch the primary menu with enabled items
 * Used by NavBar component
 */

import { prisma } from '@/lib/prisma'
import { computeMenuItemUrlPath } from './computeUrlPath'
import { resolveLabelWithFallback, DEFAULT_LOCALE } from '@/lib/i18n/resolveLabel'
import { getLocaleOrDefault } from '@/config/locales'

export interface MenuItem {
  id: string
  label: string
  urlPath: string
  order: number
  type: 'LINK' | 'BUTTON'
  isRoot?: boolean
  enabled?: boolean
  buttonStyle?: string | null
  buttonAction?: string | null
  externalUrl?: string | null
}

/**
 * Get primary menu with enabled items ordered
 * Returns empty array if menu not found or no enabled items
 * @param locale - Locale for label resolution (default: 'fr')
 */
export async function getPrimaryMenu(locale?: string): Promise<MenuItem[]> {
  try {
    const requestedLocale = locale ? getLocaleOrDefault(locale) : DEFAULT_LOCALE

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
      // Fallback to a hardcoded Home item if no menu or no items
      return [{ id: 'fallback-home', label: 'Home', urlPath: '/', type: 'LINK', isRoot: true, enabled: true, order: 0 }]
    }

    return menu.menuItems
      .map((item) => {
        // Default type to LINK for existing items that don't have type set
        const itemType = item.type || 'LINK'
        
        // For buttons, compute URL from externalUrl or use a placeholder
        // For links, compute URL from page or root
        const urlPath = itemType === 'BUTTON' 
          ? (item.externalUrl || '#')
          : computeMenuItemUrlPath(item.isRoot, item.page?.slug || null)
        
        // Skip invalid LINK items (not root but no page)
        // Buttons don't need a page, so skip this check for them
        if (itemType === 'LINK' && !item.isRoot && !item.page) {
          console.warn(`MenuItem ${item.id} (${item.label}) is invalid: not root but no page`)
          return null
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
        
        return {
          id: item.id,
          label: resolvedLabel,
          urlPath,
          order: item.order,
          type: itemType as MenuItem['type'],
          isRoot: item.isRoot,
          enabled: item.enabled,
          buttonStyle: item.buttonStyle,
          buttonAction: item.buttonAction,
          externalUrl: item.externalUrl,
        } satisfies MenuItem
      })
      .filter((item): item is NonNullable<typeof item> => item !== null)
  } catch (error) {
    console.error('Error fetching primary menu:', error)
    // Fallback on error
    return [{ id: 'fallback-home', label: 'Home', urlPath: '/', type: 'LINK', isRoot: true, enabled: true, order: 0 }]
  }
}

