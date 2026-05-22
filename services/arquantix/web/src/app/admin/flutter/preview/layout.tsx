import type { ReactNode } from 'react'

/**
 * Layout iframe-isolé pour la preview DS Flutter.
 *
 * Sert dans `<iframe>` côté admin/flutter (split-screen) — ne doit donc rendre
 * **ni sidebar admin, ni provider de locale d'édition**. Le layout admin parent
 * (`src/app/admin/layout.tsx`) détecte le préfixe `/admin/flutter/preview` et
 * passe les enfants en clair → ce layout est la véritable racine d'UI pour
 * la preview.
 */
export default function FlutterPreviewLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <div
      className="min-h-screen w-full"
      style={{ backgroundColor: '#F5F5F5' }}
    >
      {children}
    </div>
  )
}
