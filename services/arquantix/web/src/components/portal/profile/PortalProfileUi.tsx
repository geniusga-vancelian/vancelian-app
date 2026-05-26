'use client'

import type { ReactNode } from 'react'
import { AppSettingsList } from '@/components/design-system/app/AppSettingsList'
import { AppSettingsRow } from '@/components/design-system/app/AppSettingsRow'
import { PortalNavLink } from '@/components/portal/PortalNavLink'

/** @deprecated Utiliser AppSettingsList directement. */
export function PortalSettingsCard({
  children,
  className,
  seamless = true,
}: {
  children: ReactNode
  className?: string
  seamless?: boolean
}) {
  return (
    <AppSettingsList seamless={seamless} className={className}>
      {children}
    </AppSettingsList>
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
  return (
    <AppSettingsRow
      title={title}
      subtitle={subtitle}
      leading={leading}
      trailing={trailing}
      href={href}
      onClick={onClick}
      staticRow={!href && !onClick}
      className={className}
      LinkComponent={href ? PortalNavLink : undefined}
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
