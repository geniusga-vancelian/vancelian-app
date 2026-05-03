import * as React from 'react'
import { emailDsColors, emailDsFonts, emailDsRadius, emailDsType } from '@/email-ds/tokens'

export type EmailPrimaryButtonProps = {
  href: string
  children: React.ReactNode
  /** Fond clair sur panneau sombre */
  dark?: boolean
  fullWidth?: boolean
  style?: React.CSSProperties
}

export function EmailPrimaryButton({
  href,
  children,
  dark = false,
  fullWidth = false,
  style,
}: EmailPrimaryButtonProps) {
  return (
    <a
      href={href}
      style={{
        display: fullWidth ? 'block' : 'inline-block',
        background: dark ? emailDsColors.white : emailDsColors.black,
        color: dark ? emailDsColors.black : emailDsColors.white,
        textDecoration: 'none',
        padding: '14px 22px',
        borderRadius: emailDsRadius.pill,
        fontSize: emailDsType.meta.fontSize,
        fontWeight: 500,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        fontFamily: emailDsFonts.eyebrow,
        textAlign: 'center',
        boxSizing: 'border-box',
        ...style,
      }}
    >
      {children}
    </a>
  )
}

export type EmailSecondaryButtonProps = {
  href: string
  children: React.ReactNode
  onDark?: boolean
  style?: React.CSSProperties
}

export function EmailSecondaryButton({
  href,
  children,
  onDark = false,
  style,
}: EmailSecondaryButtonProps) {
  const border = onDark ? emailDsColors.white : emailDsColors.black
  const color = onDark ? emailDsColors.white : emailDsColors.black
  return (
    <a
      href={href}
      style={{
        display: 'inline-block',
        background: 'transparent',
        color,
        textDecoration: 'none',
        padding: '12px 20px',
        borderRadius: emailDsRadius.pill,
        fontSize: emailDsType.meta.fontSize,
        fontWeight: 500,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        fontFamily: emailDsFonts.eyebrow,
        border: `1.4px solid ${border}`,
        boxSizing: 'border-box',
        ...style,
      }}
    >
      {children}
    </a>
  )
}
