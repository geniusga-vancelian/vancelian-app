import * as React from 'react'
import { emailDsColors, emailDsFonts, emailDsLayout } from '@/email-ds/tokens'

export type EmailShellProps = {
  children: React.ReactNode
  /** Largeur en px (défaut 600) */
  widthPx?: number
  className?: string
  style?: React.CSSProperties
}

/**
 * Conteneur racine type « carte » centrée pour HTML e-mail (preview React ou rendu statique).
 */
export function EmailShell({
  children,
  widthPx = emailDsLayout.contentWidthPx,
  className,
  style,
}: EmailShellProps) {
  return (
    <div
      className={className}
      style={{
        width: widthPx,
        maxWidth: '100%',
        margin: '0 auto',
        background: emailDsColors.white,
        fontFamily: emailDsFonts.body,
        color: emailDsColors.black,
        overflow: 'hidden',
        boxSizing: 'border-box',
        ...style,
      }}
    >
      {children}
    </div>
  )
}
