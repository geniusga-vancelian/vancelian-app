'use client'

import { useState } from 'react'
import {
  ACCENT,
  THEME_BG,
  THEME_BORDER,
  THEME_CARD,
  THEME_FG,
  THEME_MUTED,
  extractAlphaPercent,
  pickContrastColor,
  type ThemeMode,
} from './colorUtils'
import type { CursorColorGroup, CursorColorToken } from './tokens/colors'

function CopyHexBadge({ value, theme }: { value: string; theme: ThemeMode }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={async (e) => {
        e.stopPropagation()
        try {
          await navigator.clipboard.writeText(value)
          setCopied(true)
          setTimeout(() => setCopied(false), 1200)
        } catch {
          /* clipboard indisponible */
        }
      }}
      style={{
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: 11,
        letterSpacing: '0.02em',
        padding: '2px 8px',
        borderRadius: 4,
        border: `1px solid ${THEME_BORDER[theme]}`,
        color: THEME_MUTED[theme],
        background: 'transparent',
        cursor: 'pointer',
      }}
      aria-label={`Copier ${value}`}
    >
      {copied ? 'copié' : value}
    </button>
  )
}

function StaticHexBadge({ value, theme }: { value: string; theme: ThemeMode }) {
  return (
    <span
      style={{
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: 11,
        letterSpacing: '0.02em',
        padding: '2px 8px',
        borderRadius: 4,
        border: `1px solid ${THEME_BORDER[theme]}`,
        color: THEME_MUTED[theme],
      }}
    >
      {value}
    </span>
  )
}

export function Swatch({
  token,
  theme,
  interactive = true,
}: {
  token: CursorColorToken
  theme: ThemeMode
  interactive?: boolean
}) {
  const checkerBg =
    theme === 'light'
      ? 'repeating-conic-gradient(#e6e5e0 0% 25%, #f2f1ed 0% 50%) 50% / 12px 12px'
      : 'repeating-conic-gradient(#26241e 0% 25%, #1b1913 0% 50%) 50% / 12px 12px'
  const alpha = extractAlphaPercent(token.value)
  const contrast = pickContrastColor(token.value, THEME_BG[theme])

  return (
    <div
      style={{
        border: `1px solid ${THEME_BORDER[theme]}`,
        borderRadius: 8,
        background: THEME_CARD[theme],
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        breakInside: 'avoid',
      }}
    >
      <div style={{ position: 'relative', height: 88, background: checkerBg }}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundColor: token.value,
          }}
        />
        {alpha !== null ? (
          <span
            style={{
              position: 'absolute',
              top: 8,
              right: 8,
              fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 999,
              color: contrast,
              backgroundColor:
                contrast === '#f7f7f4' ? '#00000033' : '#ffffff66',
            }}
          >
            α {alpha}%
          </span>
        ) : null}
      </div>
      <div style={{ padding: '12px 14px 14px', display: 'grid', gap: 6 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            gap: 8,
          }}
        >
          <strong
            style={{
              fontSize: 13,
              fontWeight: 500,
              color: THEME_FG[theme],
              letterSpacing: '-0.005em',
            }}
          >
            {token.label}
          </strong>
          {interactive ? (
            <CopyHexBadge value={token.value} theme={theme} />
          ) : (
            <StaticHexBadge value={token.value} theme={theme} />
          )}
        </div>
        <code
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 11,
            color: THEME_MUTED[theme],
          }}
        >
          --{token.name}
        </code>
        {token.description ? (
          <p
            style={{
              margin: 0,
              fontSize: 12,
              lineHeight: 1.5,
              color: THEME_MUTED[theme],
            }}
          >
            {token.description}
          </p>
        ) : null}
      </div>
    </div>
  )
}

export function Group({
  group,
  theme,
  interactive = true,
}: {
  group: CursorColorGroup
  theme: ThemeMode
  interactive?: boolean
}) {
  return (
    <section
      id={group.id}
      style={{
        display: 'grid',
        gap: 16,
        padding: '32px 0',
        borderTop: `1px solid ${THEME_BORDER[theme]}`,
        breakInside: 'avoid',
      }}
    >
      <header style={{ display: 'grid', gap: 6 }}>
        <h2
          style={{
            margin: 0,
            fontSize: 20,
            fontWeight: 500,
            letterSpacing: '-0.015em',
            color: THEME_FG[theme],
          }}
        >
          {group.title}
        </h2>
        {group.description ? (
          <p
            style={{
              margin: 0,
              maxWidth: 760,
              fontSize: 14,
              lineHeight: 1.55,
              color: THEME_MUTED[theme],
            }}
          >
            {group.description}
          </p>
        ) : null}
      </header>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 14,
        }}
      >
        {group.tokens.map((t) => (
          <Swatch
            key={t.name}
            token={t}
            theme={theme}
            interactive={interactive}
          />
        ))}
      </div>
    </section>
  )
}

export function ThemeBoard({
  theme,
  groups,
  title,
  subtitle,
}: {
  theme: ThemeMode
  groups: CursorColorGroup[]
  title: string
  subtitle?: string
}) {
  return (
    <section
      style={{
        backgroundColor: THEME_BG[theme],
        color: THEME_FG[theme],
        padding: '48px 32px 64px',
        breakBefore: 'page',
      }}
    >
      <header style={{ maxWidth: 1280, margin: '0 auto', display: 'grid', gap: 8 }}>
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
        <h2
          style={{
            margin: 0,
            fontSize: 36,
            lineHeight: 1.05,
            letterSpacing: '-0.025em',
            fontWeight: 500,
          }}
        >
          {title}
        </h2>
        {subtitle ? (
          <p
            style={{
              margin: 0,
              fontSize: 14,
              lineHeight: 1.55,
              color: THEME_MUTED[theme],
              maxWidth: 760,
            }}
          >
            {subtitle}
          </p>
        ) : null}
      </header>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        {groups.map((g) => (
          <Group key={g.id} group={g} theme={theme} interactive={false} />
        ))}
      </div>
    </section>
  )
}
