'use client'

import { CircleArrowRightIcon } from '@/components/design-system/extracted/atoms/circle-arrow-right-icon'
import { figmaDsTitleSmallClassName } from '@/components/design-system/extracted/atoms/section-title'
import { figmaDsLinksClassName } from '@/components/design-system/extracted/tokens/typography'
import { cn } from '@/lib/utils'

export type InThisArticleNavItem = {
  id: string
  label: string
  level?: number
  isActive?: boolean
}

export type InThisArticleNavProps = {
  title: string
  items: InThisArticleNavItem[]
  className?: string
  panelClassName?: string
  onItemClick?: (id: string) => void
}

/** Durée et easing communs : transform du texte + opacité de la flèche (même courbe, même durée → synchro navigateur). */
const SHIFT_DURATION_CLASS = 'duration-[420ms] ease-in-out'

function NavItemButton({
  item,
  onItemClick,
}: {
  item: InThisArticleNavItem
  onItemClick?: (id: string) => void
}) {
  const isActive = item.isActive === true
  const levelOffset = ((item.level ?? 2) - 1) * 10

  return (
    <button
      type="button"
      onClick={() => onItemClick?.(item.id)}
      aria-current={isActive ? 'location' : undefined}
      style={{ paddingLeft: levelOffset }}
      className="group relative isolate w-full max-w-full overflow-visible text-left text-[16px] leading-none"
    >
      <span
        className="pointer-events-none absolute z-0 flex w-9 items-center justify-center leading-none text-[16px] top-[calc(0.5lh-11px)]"
        style={{ left: levelOffset }}
        aria-hidden
      >
        <span
          className={cn(
            'flex shrink-0 items-center justify-center text-[#0f1219]',
            'transition-opacity motion-reduce:transition-none',
            SHIFT_DURATION_CLASS,
            isActive ? 'opacity-100' : 'opacity-0',
          )}
        >
          <CircleArrowRightIcon className="block h-[22px] w-[22px] shrink-0" />
        </span>
      </span>
      <span
        className={cn(
          figmaDsLinksClassName,
          'relative z-[1] block min-w-0 max-w-[calc(100%-40px)] bg-[#f3f3f3] text-left',
          'transition-[transform,color] motion-reduce:transition-none',
          SHIFT_DURATION_CLASS,
          isActive
            ? 'translate-x-10 text-[#0f1219]'
            : 'translate-x-0 text-[#62656e] group-hover:text-[#0f1219]',
        )}
      >
        {item.label}
      </span>
    </button>
  )
}

/**
 * Organisme DS - "In this article" navigation card.
 * Flèche z-0, texte z-1 avec fond panneau. Opacité de la flèche et translateX du texte partagent la même
 * transition (420ms ease-in-out) : pas de setTimeout ni transitionend, alignement sur la timeline CSS.
 */
export function InThisArticleNav({
  title,
  items,
  className,
  panelClassName,
  onItemClick,
}: InThisArticleNavProps) {
  return (
    <nav className={cn('w-full max-w-[300px]', className)}>
      <div
        className={cn(
          'rounded-[10px] border border-[#d5dae3] bg-[#f3f3f3] px-10 py-10',
          panelClassName,
        )}
      >
        <h3 className={cn(figmaDsTitleSmallClassName, 'mb-8 text-[#0f1219]')}>{title}</h3>
        <ul className="flex flex-col gap-3">
          {items.map((item) => (
            <li key={item.id}>
              <NavItemButton item={item} onItemClick={onItemClick} />
            </li>
          ))}
        </ul>
      </div>
    </nav>
  )
}
