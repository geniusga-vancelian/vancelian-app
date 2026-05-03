import * as React from 'react'
import { emailDsColors, emailDsFonts, emailDsRadius, emailDsType } from '@/email-ds/tokens'

export type EmailEyebrowProps = {
  children: React.ReactNode
  /** Bordure / texte foncés (défaut muted) */
  variant?: 'muted' | 'solid' | 'light'
  style?: React.CSSProperties
}

export function EmailEyebrow({ children, variant = 'muted', style }: EmailEyebrowProps) {
  const border =
    variant === 'solid'
      ? emailDsColors.black
      : variant === 'light'
        ? emailDsColors.white
        : emailDsColors.textMuted
  const color =
    variant === 'solid'
      ? emailDsColors.black
      : variant === 'light'
        ? emailDsColors.white
        : emailDsColors.textMuted

  return (
    <span
      style={{
        fontSize: emailDsType.caption.fontSize,
        color,
        fontFamily: emailDsFonts.eyebrow,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        padding: '3px 6px',
        border: `1px solid ${border}`,
        borderRadius: emailDsRadius.chip,
        display: 'inline-block',
        boxSizing: 'border-box',
        ...style,
      }}
    >
      {children}
    </span>
  )
}
