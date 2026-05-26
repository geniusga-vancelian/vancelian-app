'use client'

import type { ReactNode } from 'react'
import { AppSettingsList } from '@/components/design-system/app/AppSettingsList'
import { AppSettingsRow } from '@/components/design-system/app/AppSettingsRow'
import { AppSectionHeader } from '@/components/design-system/app/AppSectionHeader'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { cn } from '@/lib/utils'

/** @deprecated Utiliser AppSettingsList directement. */
export function PortalSettingsCard({ children, className }: { children: ReactNode; className?: string }) {
  return <AppSettingsList className={className}>{children}</AppSettingsList>
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
  if (href) {
    return (
      <PortalNavLink href={href} className={cn('stg-row no-underline', className)}>
        {leading ? <span className="stg-row__lead">{leading}</span> : null}
        <span className="stg-row__body">
          <span className="stg-row__title">{title}</span>
          {subtitle ? <span className="stg-row__sub">{subtitle}</span> : null}
        </span>
        <span className="stg-row__trail">{trailing}</span>
      </PortalNavLink>
    )
  }

  return (
    <AppSettingsRow
      title={title}
      subtitle={subtitle}
      leading={leading}
      trailing={trailing}
      onClick={onClick}
      staticRow={!href && !onClick}
      className={className}
    />
  )
}

export function PortalSectionTitle({ children }: { children: ReactNode }) {
  return (
    <div className="sh-app w-full max-w-none">
      <span className="sh-app__dot" aria-hidden />
      <h2 className="sh-app__title m-0">{children}</h2>
    </div>
  )
}
