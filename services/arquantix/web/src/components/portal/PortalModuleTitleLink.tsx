'use client'

import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { cn } from '@/lib/utils'

type Props = {
  href: string
  title: string
  className?: string
  /** `md` = widgets dashboard (18px), `lg` = titres de section (20px). */
  size?: 'md' | 'lg'
}

/** Titre de module cliquable — flèche → collée au libellé (comme Sign out). */
export function PortalModuleTitleLink({ href, title, className, size = 'md' }: Props) {
  return (
    <PortalNavLink
      href={href}
      className={cn(
        'group inline-flex w-fit max-w-full items-center gap-2 no-underline',
        className,
      )}
    >
      <span
        className={cn(
          'font-ui font-semibold text-v-fg',
          size === 'lg' ? 'text-[20px] tracking-v-tight' : 'text-[18px]',
        )}
      >
        {title}
      </span>
      <span
        className="inline-block shrink-0 font-ui text-[16px] leading-none text-v-fg-muted transition-transform duration-v-base ease-v-out group-hover:translate-x-1 group-hover:text-v-fg"
        aria-hidden
      >
        →
      </span>
    </PortalNavLink>
  )
}
