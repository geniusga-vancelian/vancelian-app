'use client'

import { useMemo, useState } from 'react'
import {
  ACCENT,
  THEME_BG,
  THEME_BORDER,
  THEME_FG,
  THEME_MUTED,
  type ThemeMode,
} from './colorUtils'
import { Group } from './ColorVisuals'
import { cursorColorGroups } from './tokens/colors'

export function CursorColorsShowcase() {
  const [theme, setTheme] = useState<ThemeMode>('light')
  const [query, setQuery] = useState('')

  const filteredGroups = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return cursorColorGroups
    return cursorColorGroups
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

  const totalTokens = useMemo(
    () => cursorColorGroups.reduce((acc, g) => acc + g.tokens.length, 0),
    [],
  )

  return (
    <div
      style={{
        minHeight: '100vh',
        backgroundColor: THEME_BG[theme],
        color: THEME_FG[theme],
        fontFamily:
          '"Inter", "Avenir Next", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
        transition: 'background-color 200ms ease, color 200ms ease',
      }}
    >
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
          <div style={{ display: 'grid', gap: 10, maxWidth: 720 }}>
            <span
              style={{
                fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
                fontSize: 11,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                color: ACCENT,
              }}
            >
              Design system / Cursor
            </span>
            <h1
              style={{
                margin: 0,
                fontSize: 44,
                lineHeight: 1.05,
                letterSpacing: '-0.025em',
                fontWeight: 500,
              }}
            >
              Couleurs
            </h1>
            <p
              style={{
                margin: 0,
                fontSize: 16,
                lineHeight: 1.55,
                color: THEME_MUTED[theme],
              }}
            >
              Tokens couleur extraits du site{' '}
              <a
                href="https://cursor.com/get-started"
                target="_blank"
                rel="noreferrer"
                style={{ color: ACCENT, textDecoration: 'none' }}
              >
                cursor.com/get-started
              </a>
              . {totalTokens} tokens organisés en {cursorColorGroups.length}{' '}
              groupes (theme light/dark, foregrounds, borders, cartes, texte,
              product, semantic, palettes Tailwind).{' '}
              <a
                href="/cursor-design-system-couleurs.pdf"
                style={{
                  color: ACCENT,
                  textDecoration: 'none',
                  borderBottom: `1px solid ${ACCENT}`,
                }}
              >
                Télécharger le PDF
              </a>
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
                color: THEME_FG[theme],
                background: 'transparent',
                border: `1px solid ${THEME_BORDER[theme]}`,
                borderRadius: 6,
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
                borderRadius: 999,
                border: `1px solid ${THEME_BORDER[theme]}`,
              }}
            >
              {(['light', 'dark'] as const).map((m) => {
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
                      borderRadius: 999,
                      background: active
                        ? m === 'light'
                          ? '#26251e'
                          : '#edecec'
                        : 'transparent',
                      color: active
                        ? m === 'light'
                          ? '#f7f7f4'
                          : '#14120b'
                        : THEME_MUTED[theme],
                      transition: 'all 120ms ease',
                    }}
                  >
                    {m === 'light' ? 'Light' : 'Dark'}
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
          {cursorColorGroups.map((g) => (
            <a
              key={g.id}
              href={`#${g.id}`}
              style={{
                fontSize: 12,
                padding: '4px 10px',
                borderRadius: 999,
                border: `1px solid ${THEME_BORDER[theme]}`,
                color: THEME_MUTED[theme],
                textDecoration: 'none',
              }}
            >
              {g.title}
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
        {filteredGroups.length === 0 ? (
          <p
            style={{
              padding: '48px 0',
              color: THEME_MUTED[theme],
              fontSize: 14,
            }}
          >
            Aucun token ne correspond à « {query} ».
          </p>
        ) : (
          filteredGroups.map((g) => <Group key={g.id} group={g} theme={theme} />)
        )}
      </main>

      <footer
        style={{
          padding: '24px 32px 48px',
          maxWidth: 1280,
          margin: '0 auto',
          borderTop: `1px solid ${THEME_BORDER[theme]}`,
          fontSize: 12,
          color: THEME_MUTED[theme],
        }}
      >
        Source : extraction des bundles CSS{' '}
        <code style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' }}>
          /marketing-static/_next/static/chunks/*.css
        </code>{' '}
        de cursor.com (avril 2026). Design system « Cursor » — couleurs
        uniquement à ce stade.
      </footer>
    </div>
  )
}
