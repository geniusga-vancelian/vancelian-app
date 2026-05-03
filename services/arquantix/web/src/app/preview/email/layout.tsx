import type { Metadata } from 'next'
import type { ReactNode } from 'react'

export const metadata: Metadata = {
  title: 'Preview e-mail — Arquantix',
  robots: { index: false, follow: false },
}

/**
 * Wrapper neutre pour les previews e-mail : fond gris clair type client mail,
 * aucun chrome site (le layout racine reconnaît `/preview/email/` et saute `SiteChrome`).
 */
export default function EmailPreviewLayout({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100%',
        background: '#f5f5f7',
        padding: '32px 16px',
        boxSizing: 'border-box',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'flex-start',
      }}
    >
      {children}
    </div>
  )
}
