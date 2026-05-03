import * as React from 'react'
import { emailDsAssetUrl } from '@/email-ds/resolveAssetUrl'

const DEFAULT_FILE = 'logo-wordmark-black.svg'

export type EmailWordmarkProps = {
  heightPx?: number
  /** Logo clair (fond sombre) */
  invert?: boolean
  alt?: string
  /** Origine absolue pour clients mail */
  assetOrigin?: string
  style?: React.CSSProperties
}

export function EmailWordmark({
  heightPx = 22,
  invert = false,
  alt = 'Arquantix',
  assetOrigin,
  style,
}: EmailWordmarkProps) {
  return (
    <img
      src={emailDsAssetUrl(DEFAULT_FILE, assetOrigin)}
      alt={alt}
      height={heightPx}
      style={{
        height: heightPx,
        width: 'auto',
        display: 'block',
        border: 0,
        outline: 'none',
        filter: invert ? 'invert(1)' : 'none',
        ...style,
      }}
    />
  )
}
