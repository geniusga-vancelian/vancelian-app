import type { Metadata } from 'next'
import { HermesColorBoard } from '@/components/design-system-hermes/ColorVisuals'
import { hermesColorGroups } from '@/components/design-system-hermes/tokens/colors'
import { HermesTypographyShowcase } from '@/components/design-system-hermes/TypographyShowcase'
import { HermesLayoutShowcase } from '@/components/design-system-hermes/LayoutShowcase'
import { HermesComponentsShowcase } from '@/components/design-system-hermes/ComponentsShowcase'
import {
  HERMES_ACCENT,
  HERMES_THEME_BG,
  HERMES_THEME_FG,
  HERMES_THEME_MUTED,
} from '@/components/design-system-hermes/themeUtils'

export const metadata: Metadata = {
  title: 'Hermès — Design system (PDF)',
  robots: { index: false, follow: false },
}

const FONT_PRIMARY = '"Manrope", "Roboto", sans-serif'
const FONT_EDITO =
  '"EB Garamond", "EBGaramond", "Bell MT", "Times New Roman", serif'
const FONT_MONO = '"Overpass Mono", ui-monospace, monospace'

function CoverBoard({
  theme,
  title,
  subtitle,
}: {
  theme: 'beige' | 'dark'
  title: string
  subtitle: string
}) {
  return (
    <section
      style={{
        backgroundColor: HERMES_THEME_BG[theme],
        color: HERMES_THEME_FG[theme],
        padding: '120px 48px 64px',
        breakBefore: 'page',
        minHeight: '100vh',
      }}
    >
      <div style={{ maxWidth: 1280, margin: '0 auto', display: 'grid', gap: 18 }}>
        <span
          style={{
            fontFamily: FONT_MONO,
            fontSize: 12,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            color: HERMES_ACCENT,
          }}
        >
          Design system / Hermès
        </span>
        <h1
          style={{
            margin: 0,
            fontFamily: FONT_EDITO,
            fontSize: 84,
            lineHeight: 1.0,
            letterSpacing: '-0.025em',
            fontWeight: 500,
          }}
        >
          {title}
        </h1>
        <p
          style={{
            margin: 0,
            fontFamily: FONT_PRIMARY,
            fontSize: 16,
            lineHeight: 1.6,
            color: HERMES_THEME_MUTED[theme],
            maxWidth: 720,
          }}
        >
          {subtitle}
        </p>
      </div>
    </section>
  )
}

function FullThemeBoard({ theme }: { theme: 'beige' | 'dark' }) {
  return (
    <>
      <HermesColorBoard
        theme={theme}
        groups={hermesColorGroups}
        title={
          theme === 'beige'
            ? 'Couleurs — palette beige'
            : 'Couleurs — palette dark'
        }
        subtitle={
          theme === 'beige'
            ? 'Palette par défaut visible sur hermes.com. Tokens conservés tels quels (préfixe `--color-…`).'
            : 'Inversion sur fond `dark-level-5` (#2e2d2d). Mêmes tokens, contraste inversé.'
        }
      />
      <section
        style={{
          backgroundColor: HERMES_THEME_BG[theme],
          color: HERMES_THEME_FG[theme],
          padding: '0 48px 64px',
          breakBefore: 'page',
        }}
      >
        <div style={{ maxWidth: 1280, margin: '0 auto' }}>
          <HermesTypographyShowcase theme={theme} />
        </div>
      </section>
      <section
        style={{
          backgroundColor: HERMES_THEME_BG[theme],
          color: HERMES_THEME_FG[theme],
          padding: '0 48px 64px',
          breakBefore: 'page',
        }}
      >
        <div style={{ maxWidth: 1280, margin: '0 auto' }}>
          <HermesLayoutShowcase theme={theme} />
        </div>
      </section>
      <section
        style={{
          backgroundColor: HERMES_THEME_BG[theme],
          color: HERMES_THEME_FG[theme],
          padding: '0 48px 96px',
          breakBefore: 'page',
        }}
      >
        <div style={{ maxWidth: 1280, margin: '0 auto' }}>
          <HermesComponentsShowcase theme={theme} />
        </div>
      </section>
    </>
  )
}

/**
 * Page « print-ready » : DS Hermès complet (couleurs, typo, layout, composants)
 * dans les deux thèmes (beige puis dark), optimisée pour l'export PDF.
 */
export default function HermesDesignSystemPrintPage() {
  return (
    <div style={{ fontFamily: FONT_PRIMARY }}>
      <link rel="preconnect" href="https://fonts.googleapis.com" />
      <link
        rel="preconnect"
        href="https://fonts.gstatic.com"
        crossOrigin="anonymous"
      />
      <link
        href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400..800;1,400..800&family=Manrope:wght@200..800&family=Overpass+Mono:wght@300..700&display=swap"
        rel="stylesheet"
      />

      <CoverBoard
        theme="beige"
        title="Tokens, atomes & composants"
        subtitle="Extraction du Design System Hermès (hermes.com — bundle Angular avril 2026). Couleurs, typographie, layout et composants reproduits fidèlement."
      />
      <FullThemeBoard theme="beige" />

      <CoverBoard
        theme="dark"
        title="Vue inversée — dark"
        subtitle="Mêmes tokens, contraste inversé sur fond `dark-level-5` (#2e2d2d). Utile pour les pages campagne en aplat sombre."
      />
      <FullThemeBoard theme="dark" />
    </div>
  )
}
