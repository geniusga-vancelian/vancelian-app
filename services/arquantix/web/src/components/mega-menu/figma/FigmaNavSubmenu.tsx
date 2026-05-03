'use client'

/**
 * UI méga-menu dérivée du export Figma Make (`NavSubmenu.tsx`).
 * Adaptations : liens réels, icône par défaut locale, types partagés CMS.
 */
import * as React from 'react'

import { cn } from '@/lib/utils'
import { Paragraph } from '@/components/design-system/extracted'
import { figmaDsColors } from '@/components/design-system/extracted/tokens'
import { MEGA_MENU_ITEM_TITLE_TYPO } from '@/components/design-system/nav-primary-link'
import type { MegaMenuColumnPayload, MegaMenuItemPayload } from '@/lib/menu/buildMegaMenuColumns'

const DEFAULT_ICON_SRC = '/mega-menu-default-icon.png'

export type FigmaNavSubmenuProps = {
  columns: MegaMenuColumnPayload[]
  className?: string
}

function FigmaMegaMenuItem({
  item,
  iconSrc,
}: {
  item: MegaMenuItemPayload
  iconSrc: string
}) {
  return (
    <a
      href={item.href}
      className="group bg-white relative rounded-[12px] shrink-0 w-full hover:bg-gray-50 transition-colors cursor-pointer block no-underline text-inherit"
    >
      <div className="content-stretch flex gap-[8px] items-start p-[16px] relative size-full">
        <div className="flex items-center justify-center relative rounded-[8px] shrink-0 size-[40px] bg-[#eef2f6] overflow-hidden">
          <img
            alt=""
            className="size-full object-cover"
            src={iconSrc}
          />
        </div>
        <div className="content-stretch flex flex-[1_0_0] flex-col gap-[4px] items-start min-w-px not-italic relative">
          <p
            className={cn(
              MEGA_MENU_ITEM_TITLE_TYPO,
              'relative shrink-0 w-full text-[#272727]',
            )}
          >
            {item.title}
          </p>
          {item.description ? (
            <Paragraph
              color={figmaDsColors.text.secondary}
              className="relative shrink-0"
            >
              {item.description}
            </Paragraph>
          ) : null}
        </div>
      </div>
    </a>
  )
}

function FigmaMenuCategory({ label }: { label: string }) {
  return (
    <div className="bg-white relative rounded-[12px] shrink-0 w-full">
      <div className="content-stretch flex items-start pt-[16px] px-[16px] relative size-full">
        <Paragraph
          color={figmaDsColors.text.secondary}
          className="relative min-w-px flex-[1_0_0]"
        >
          {label}
        </Paragraph>
      </div>
    </div>
  )
}

function FigmaMenuColumn({ column }: { column: MegaMenuColumnPayload }) {
  return (
    <div className="content-stretch flex flex-col gap-[16px] items-start relative shrink-0 w-[min(100%,368px)] flex-1 min-w-0">
      {column.category ? <FigmaMenuCategory label={column.category} /> : null}
      {column.items.map((item) => (
        <FigmaMegaMenuItem
          key={item.id}
          item={item}
          iconSrc={item.iconUrl && item.iconUrl.length > 0 ? item.iconUrl : DEFAULT_ICON_SRC}
        />
      ))}
    </div>
  )
}

/**
 * Panneau blanc Figma (contenu uniquement — positionnement géré par le parent).
 */
export function FigmaNavSubmenu({ columns, className = '' }: FigmaNavSubmenuProps) {
  if (!columns.length) {
    return null
  }
  return (
    <div
      className={cn(
        'bg-white content-stretch flex flex-wrap justify-center gap-x-[40px] gap-y-[20px] items-start p-[8px] relative rounded-[24px] shadow-[0_24px_48px_-12px_rgba(0,0,0,0.12)] border border-neutral-100/90',
        'max-w-[920px] w-full mx-auto',
        className,
      )}
    >
      {columns.map((column) => (
        <FigmaMenuColumn key={column.id} column={column} />
      ))}
    </div>
  )
}
