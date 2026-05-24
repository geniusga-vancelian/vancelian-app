'use client'

import type { ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { cn } from '@/lib/utils'

export function PortalSettingsCard({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        'overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle',
        className,
      )}
    >
      {children}
    </div>
  )
}

type SettingsRowProps = {
  title: string
  subtitle?: string
  href?: string
  onClick?: () => void
  trailing?: ReactNode
  leading?: ReactNode
  className?: string
}

export function PortalSettingsRow({
  title,
  subtitle,
  href,
  onClick,
  trailing,
  leading,
  className,
}: SettingsRowProps) {
  const content = (
    <>
      {leading ? <span className="shrink-0">{leading}</span> : null}
      <span className="min-w-0 flex-1">
        <span className="block font-ui text-[16px] font-medium text-v-fg">{title}</span>
        {subtitle ? (
          <span className="mt-0.5 block font-ui text-[13px] leading-snug text-v-fg-muted">{subtitle}</span>
        ) : null}
      </span>
      {trailing ?? (href || onClick ? <ChevronRight className="h-5 w-5 shrink-0 text-v-fg-muted" /> : null)}
    </>
  )

  const rowClass = cn(
    'flex w-full items-center gap-3 border-0 bg-transparent px-4 py-4 text-left sm:px-5',
    'border-b border-v-fg-05 last:border-b-0',
    (href || onClick) && 'cursor-pointer transition-colors duration-v-fast hover:bg-v-fg-02',
    className,
  )

  if (href) {
    return (
      <PortalNavLink href={href} className={cn(rowClass, 'no-underline')}>
        {content}
      </PortalNavLink>
    )
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={rowClass}>
        {content}
      </button>
    )
  }

  return <div className={rowClass}>{content}</div>
}

export function PortalSectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="m-0 font-ui text-[13px] font-semibold uppercase tracking-v-wide text-v-fg-muted">
      {children}
    </h2>
  )
}
