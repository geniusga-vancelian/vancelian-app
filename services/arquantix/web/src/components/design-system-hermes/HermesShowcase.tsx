'use client'

import { useMemo, useState } from 'react'
import {
  HERMES_ACCENT,
  HERMES_THEME_BG,
  HERMES_THEME_BORDER,
  HERMES_THEME_FG,
  HERMES_THEME_MUTED,
  type HermesThemeMode,
} from './themeUtils'
import { HermesColorGroupView } from './ColorVisuals'
import { hermesColorGroups } from './tokens/colors'
import { HermesTypographyShowcase } from './TypographyShowcase'
import { HermesLayoutShowcase } from './LayoutShowcase'
import { HermesComponentsShowcase } from './ComponentsShowcase'

const FONT_PRIMARY = '"Manrope", "Roboto", sans-serif'
const FONT_EDITO =
  '"EB Garamond", "EBGaramond", "Bell MT", "Times New Roman", serif'
const FONT_MONO = '"Overpass Mono", ui-monospace, monospace'

const SECTIONS: Array<{ id: string; title: string }> = [
  { id: 'beige', title: 'Beige' },
  { id: 'dark', title: 'Dark' },
  { id: 'misc', title: 'Neutres & sémantiques' },
  { id: 'extended', title: 'Étendues' },
  { id: 'typography', title: 'Typographie' },
  { id: 'layout', title: 'Layout' },
  { id: 'components', title: 'Atomes & composants' },
]

export function HermesShowcase() {
  const [theme, setTheme] = useState<HermesThemeMode>('beige')
  const [query, setQuery] = useState('')

  const filteredColorGroups = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return hermesColorGroups
    return hermesColorGroups
      .map((g) => ({
        ...g,
        tokens: g.tokens.filter(
          (t) =>
            t.name.toLowerCase().includes(q) ||
            t.label.toLowerCase().includes(q) ||
            t.value.toLowerCase().includes(q),
        ),
      }))
      .filter((g) => g.tokens.length > 0)
  }, [query])

  const totalColorTokens = useMemo(
    () => hermesColorGroups.reduce((acc, g) => acc + g.tokens.length, 0),
    [],
  )

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: HERMES_THEME_BG[theme],
        color: HERMES_THEME_FG[theme],
        fontFamily: FONT_PRIMARY,
        transition: 'background-color 200ms ease, color 200ms ease',
      }}
    >
      {/* Inject les Google Fonts (Manrope, EB Garamond, Overpass Mono) */}
      <link
        rel="preconnect"
        href="https://fonts.googleapis.com"
        crossOrigin=""
      />
      <link
        rel="preconnect"
        href="https://fonts.gstatic.com"
        crossOrigin="anonymous"
      />
      <link
        href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400..800;1,400..800&family=Manrope:wght@200..800&family=Overpass+Mono:wght@300..700&display=swap"
        rel="stylesheet"
      />

      <header
        style={{
          padding: '48px 32px 24px',
          maxWidth: 1280,
          margin: '0 auto',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            alignItems: 'flex-end',
            justifyContent: 'space-between',
            gap: 24,
          }}
        >
          <div style={{ display: 'grid', gap: 12, maxWidth: 760 }}>
            <span
              style={{
                fontFamily: FONT_MONO,
                fontSize: 11,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: HERMES_ACCENT,
              }}
            >
              Design system / Hermès
            </span>
            <h1
              style={{
                margin: 0,
                fontSize: 52,
                lineHeight: 1.0,
                letterSpacing: '-0.025em',
                fontWeight: 500,
                fontFamily: FONT_EDITO,
              }}
            >
              Tokens, atomes &amp; composants
            </h1>
            <p
              style={{
                margin: 0,
                fontSize: 16,
                lineHeight: 1.6,
                color: HERMES_THEME_MUTED[theme],
              }}
            >
              Extraction du Design System Hermès depuis{' '}
              <a
                href="https://www.hermes.com/fr/fr/"
                target="_blank"
                rel="noreferrer"
                style={{
                  color: HERMES_ACCENT,
                  textDecoration: 'none',
                  borderBottom: `1px solid ${HERMES_ACCENT}`,
                }}
              >
                hermes.com
              </a>{' '}
              (bundle Angular <code style={{ fontFamily: FONT_MONO }}>main.js</code> +
              feuille <code style={{ fontFamily: FONT_MONO }}>hermes.css</code>).
              {totalColorTokens} tokens couleur, échelle typographique
              parallèle (heading × body), 8 graisses et 5 polices vedettes,
              plus une vitrine d’atomes &amp; composants reproduisant
              fidèlement la maison.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <input
              type="search"
              placeholder="Filtrer (nom, label, hex…)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{
                width: 220,
                padding: '8px 12px',
                fontSize: 13,
                color: HERMES_THEME_FG[theme],
                background: 'transparent',
                border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
                borderRadius: 0,
                outline: 'none',
                fontFamily: 'inherit',
              }}
            />
            <div
              role="tablist"
              aria-label="Mode d'affichage"
              style={{
                display: 'inline-flex',
                padding: 2,
                borderRadius: 0,
                border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
              }}
            >
              {(['beige', 'dark'] as const).map((m) => {
                const active = theme === m
                return (
                  <button
                    key={m}
                    role="tab"
                    aria-selected={active}
                    onClick={() => setTheme(m)}
                    style={{
                      padding: '6px 14px',
                      fontSize: 12,
                      fontFamily: 'inherit',
                      cursor: 'pointer',
                      border: 'none',
                      borderRadius: 0,
                      background: active
                        ? m === 'beige'
                          ? '#000'
                          : '#fcf7f1'
                        : 'transparent',
                      color: active
                        ? m === 'beige'
                          ? '#fcf7f1'
                          : '#2e2d2d'
                        : HERMES_THEME_MUTED[theme],
                      transition: 'all 120ms ease',
                      letterSpacing: '0.06em',
                      textTransform: 'uppercase',
                    }}
                  >
                    {m === 'beige' ? 'Beige' : 'Dark'}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        <nav
          style={{
            marginTop: 28,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
          }}
        >
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              style={{
                fontSize: 12,
                padding: '4px 10px',
                borderRadius: 0,
                border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
                color: HERMES_THEME_MUTED[theme],
                textDecoration: 'none',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
              }}
            >
              {s.title}
            </a>
          ))}
        </nav>
      </header>

      <main
        style={{
          maxWidth: 1280,
          margin: '0 auto',
          padding: '0 32px 64px',
        }}
      >
        {/* === Section Couleurs (filtrables) === */}
        {filteredColorGroups.length === 0 ? (
          <p
            style={{
              padding: '48px 0',
              color: HERMES_THEME_MUTED[theme],
              fontSize: 14,
            }}
          >
            Aucun token ne correspond à « {query} ».
          </p>
        ) : (
          filteredColorGroups.map((g) => (
            <HermesColorGroupView key={g.id} group={g} theme={theme} />
          ))
        )}

        {/* === Atomes / sections fixes (pas filtrés par la recherche) === */}
        <HermesTypographyShowcase theme={theme} />
        <HermesLayoutShowcase theme={theme} />
        <HermesComponentsShowcase theme={theme} />
      </main>

      <footer
        style={{
          padding: '24px 32px 48px',
          maxWidth: 1280,
          margin: '0 auto',
          borderTop: `1px solid ${HERMES_THEME_BORDER[theme]}`,
          fontSize: 12,
          color: HERMES_THEME_MUTED[theme],
        }}
      >
        Source : extraction du bundle Angular de hermes.com (avril 2026) —{' '}
        <code style={{ fontFamily: FONT_MONO }}>
          /fr/fr/hermes.ef2936e76bedc435.css
        </code>{' '}
        +{' '}
        <code style={{ fontFamily: FONT_MONO }}>
          /fr/fr/main.03131fe7703be59e.js
        </code>
        . Design system « Hermès » — couleurs, typographie, layout, composants.
      </footer>
    </div>
  )
}
