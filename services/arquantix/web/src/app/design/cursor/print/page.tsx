import type { Metadata } from 'next'
import { ThemeBoard } from '@/components/design-system-cursor/ColorVisuals'
import { cursorColorGroups } from '@/components/design-system-cursor/tokens/colors'

export const metadata: Metadata = {
  title: 'Cursor — Design system couleurs (PDF)',
  robots: { index: false, follow: false },
}

/**
 * Page « print-ready » : affiche les deux thèmes (light puis dark) à la suite,
 * sans interactivité, optimisée pour l'export PDF via Playwright.
 *
 * Voir : `scripts/generate-cursor-ds-pdf.ts`.
 */
export default function CursorDesignSystemPrintPage() {
  return (
    <div
      style={{
        fontFamily:
          '"Inter", "Avenir Next", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
      }}
    >
      <ThemeBoard
        theme="light"
        groups={cursorColorGroups}
        title="Couleurs — mode clair"
        subtitle="Palette par défaut visible sur cursor.com. Tokens conservés tels quels (préfixe `--color-…`)."
      />
      <ThemeBoard
        theme="dark"
        groups={cursorColorGroups}
        title="Couleurs — mode sombre"
        subtitle="Overrides activés via `[data-theme=&quot;dark&quot;]`. Mêmes tokens, valeurs adaptées."
      />
    </div>
  )
}
