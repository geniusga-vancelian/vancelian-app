'use client'

import * as React from 'react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { MenuItem } from '@/lib/menu/getPrimaryMenu'
import type { MegaMenuColumnPayload } from '@/lib/menu/buildMegaMenuColumns'
import { Label } from '@/components/design-system/extracted'
import { Paragraph } from '@/components/design-system/extracted'
import { figmaDsColors } from '@/components/design-system/extracted/tokens/colors'
import { MEGA_MENU_ITEM_TITLE_TYPO, NAV_PRIMARY_LINK_TYPO } from '@/components/design-system/nav-primary-link'
import {
  isPublicHrefExternalNavigation,
  localizePublicInternalHref,
  shouldSkipLocalizePublicHref,
} from '@/lib/i18n/publicLocalizedRouting'
import type { Locale } from '@/config/locales'

const DEFAULT_MEGA_ICON = '/mega-menu-default-icon.png'

function normalizePath(p: string): string {
  const t = p.replace(/\/$/, '')
  return t || '/'
}

function isHrefActive(pathname: string, href: string): boolean {
  const p = normalizePath(pathname)
  const u = normalizePath(href)
  return p === u || p.startsWith(`${u}/`)
}

function isChildInMegaActive(
  pathname: string,
  columns: MegaMenuColumnPayload[] | undefined,
): boolean {
  if (!columns) return false
  for (const col of columns) {
    for (const row of col.items) {
      if (isHrefActive(pathname, row.href)) return true
    }
  }
  return false
}

type MobilePrimaryNavListProps = {
  linkItems: MenuItem[]
  navLocale: Locale
  pathname: string
  isActive: (item: MenuItem) => boolean
  onNavigate: () => void
}

/**
 * Menu mobile : accordéon pour items avec méga-menu (libellés de colonne + cartes
 * titre / description / icône, aligné sur le panneau desktop Figma) ; liens simples
 * en liste alignée à gauche.
 */
export function MobilePrimaryNavList({
  linkItems,
  navLocale,
  pathname,
  isActive,
  onNavigate,
}: MobilePrimaryNavListProps) {
  const [openId, setOpenId] = React.useState<string | null>(null)

  const toggle = (id: string) => {
    setOpenId((prev) => (prev === id ? null : id))
  }

  return (
    <ul className="m-0 list-none p-0" role="list">
      {linkItems.map((item) => {
        const kind = item.navigationNodeKind ?? 'PAGE'
        const cols = item.megaMenu?.columns
        const hasMega = Boolean(cols && cols.length > 0)

        if (kind === 'GROUP' && !hasMega) {
          return (
            <li key={item.id} className="border-b border-black/[0.06]">
              <div
                className={cn(NAV_PRIMARY_LINK_TYPO, 'px-4 py-3 text-left text-[#62656E]')}
                role="presentation"
              >
                {item.label}
              </div>
            </li>
          )
        }

        if (kind === 'EXTERNAL_LINK') {
          const raw = (item.urlPath || '').trim()
          const href = shouldSkipLocalizePublicHref(raw) ? raw : localizePublicInternalHref(raw, navLocale)
          const newTab = item.openInNewTab || isPublicHrefExternalNavigation(href)
          const active = isActive(item)
          return (
            <li key={item.id} className="border-b border-black/[0.06]">
              <a
                href={href}
                target={newTab ? '_blank' : undefined}
                rel={newTab ? 'noopener noreferrer' : undefined}
                onClick={onNavigate}
                className={cn(
                  NAV_PRIMARY_LINK_TYPO,
                  'block px-4 py-3.5 text-left no-underline transition-colors',
                  active
                    ? 'bg-neutral-200/90 text-black'
                    : 'text-[#62656E] hover:bg-[#F3F3F3] hover:text-black',
                )}
              >
                {item.label}
              </a>
            </li>
          )
        }

        if (!hasMega) {
          const active = isActive(item)
          const href = localizePublicInternalHref(item.urlPath, navLocale)
          return (
            <li key={item.id} className="border-b border-black/[0.06]">
              <a
                href={href}
                onClick={onNavigate}
                className={cn(
                  NAV_PRIMARY_LINK_TYPO,
                  'block px-4 py-3.5 text-left no-underline transition-colors',
                  active
                    ? 'bg-neutral-200/90 text-black'
                    : 'text-[#62656E] hover:bg-[#F3F3F3] hover:text-black',
                )}
              >
                {item.label}
              </a>
            </li>
          )
        }

        const open = openId === item.id
        const groupActive = isActive(item) || isChildInMegaActive(pathname, cols)
        return (
          <li key={item.id} className="border-b border-black/[0.06]">
            <button
              type="button"
              aria-expanded={open}
              onClick={() => toggle(item.id)}
              className={cn(
                NAV_PRIMARY_LINK_TYPO,
                'flex w-full items-center justify-between gap-2 px-4 py-3.5 text-left transition-colors',
                open
                  ? 'bg-[#F3F3F3] text-black'
                  : groupActive
                    ? 'bg-[#F3F3F3]/60 text-black'
                    : 'text-[#62656E] hover:bg-[#F3F3F3] hover:text-black',
              )}
            >
              <span className="min-w-0 flex-1">{item.label}</span>
              <ChevronDown
                className={cn('h-4 w-4 shrink-0 text-[#62656E] transition-transform duration-200', open && 'rotate-180')}
                aria-hidden
                strokeWidth={2}
              />
            </button>
            {open && cols ? (
              <div
                className="border-t border-black/[0.04] bg-white px-2 pb-3 pt-1"
                role="region"
                aria-label={item.label}
              >
                {cols.map((col) => (
                  <div key={col.id} className="mb-3 last:mb-0">
                    {col.category ? (
                      <div className="px-2 pb-1.5 pt-2">
                        <Label
                          as="p"
                          className={cn('text-[#62656E]', 'opacity-80')}
                        >
                          {col.category}
                        </Label>
                      </div>
                    ) : null}
                    <ul className="m-0 list-none space-y-1 p-0" role="list">
                      {col.items.map((row) => {
                        const rowActive = isHrefActive(pathname, row.href)
                        const iconSrc = row.iconUrl && row.iconUrl.length > 0 ? row.iconUrl : DEFAULT_MEGA_ICON
                        return (
                          <li key={row.id}>
                            <a
                              href={row.href}
                              onClick={onNavigate}
                              className={cn(
                                'group flex min-h-[4rem] items-start gap-2.5 rounded-[12px] p-2.5 no-underline transition-colors',
                                rowActive
                                  ? 'bg-[#F3F3F3]'
                                  : 'hover:bg-[#F3F3F3]/80 active:bg-[#F3F3F3]',
                              )}
                            >
                              <div className="flex size-10 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-[#eef2f6]">
                                <img src={iconSrc} alt="" className="size-full object-cover" />
                              </div>
                              <div className="min-w-0 flex-1">
                                <p
                                  className={cn(
                                    MEGA_MENU_ITEM_TITLE_TYPO,
                                    'm-0 text-left leading-tight text-[#272727]',
                                    rowActive && 'text-black',
                                  )}
                                >
                                  {row.title}
                                </p>
                                {row.description ? (
                                  <Paragraph
                                    color={figmaDsColors.text.secondary}
                                    as="span"
                                    className="mt-0.5 line-clamp-3 block text-left text-[13px] leading-snug"
                                  >
                                    {row.description}
                                  </Paragraph>
                                ) : null}
                              </div>
                            </a>
                          </li>
                        )
                      })}
                    </ul>
                  </div>
                ))}
              </div>
            ) : null}
          </li>
        )
      })}
    </ul>
  )
}
