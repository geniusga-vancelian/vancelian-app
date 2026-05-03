'use client'

import { useState } from 'react'
import {
  HERMES_ACCENT,
  HERMES_THEME_BG,
  HERMES_THEME_BORDER,
  HERMES_THEME_CARD,
  HERMES_THEME_FG,
  HERMES_THEME_MUTED,
  extractAlphaPercent,
  pickContrastColor,
  type HermesThemeMode,
} from './themeUtils'
import type { HermesColorGroup, HermesColorToken } from './tokens/colors'

function CopyHexBadge({
  value,
  theme,
}: {
  value: string
  theme: HermesThemeMode
}) {
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
        fontFamily: '"Overpass Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: 11,
        letterSpacing: '0.02em',
        padding: '2px 8px',
        borderRadius: 0,
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        color: HERMES_THEME_MUTED[theme],
        background: 'transparent',
        cursor: 'pointer',
      }}
      aria-label={`Copier ${value}`}
    >
      {copied ? 'copié' : value}
    </button>
  )
}

function StaticHexBadge({
  value,
  theme,
}: {
  value: string
  theme: HermesThemeMode
}) {
  return (
    <span
      style={{
        fontFamily: '"Overpass Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
        fontSize: 11,
        letterSpacing: '0.02em',
        padding: '2px 8px',
        borderRadius: 0,
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        color: HERMES_THEME_MUTED[theme],
      }}
    >
      {value}
    </span>
  )
}

export function HermesSwatch({
  token,
  theme,
  interactive = true,
}: {
  token: HermesColorToken
  theme: HermesThemeMode
  interactive?: boolean
}) {
  const checkerBg =
    theme === 'beige'
      ? 'repeating-conic-gradient(#e2d8ce 0% 25%, #f6f1eb 0% 50%) 50% / 12px 12px'
      : 'repeating-conic-gradient(#1f1e1e 0% 25%, #2e2d2d 0% 50%) 50% / 12px 12px'
  const alpha = extractAlphaPercent(token.value)
  const contrast = pickContrastColor(token.value, HERMES_THEME_BG[theme])

  return (
    <div
      style={{
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        borderRadius: 0,
        background: HERMES_THEME_CARD[theme],
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        breakInside: 'avoid',
      }}
    >
      <div style={{ position: 'relative', height: 96, background: checkerBg }}>
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
              fontFamily:
                '"Overpass Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 0,
              color: contrast,
              backgroundColor:
                contrast === '#fcf7f1' ? '#00000033' : '#ffffff80',
            }}
          >
            α {alpha}%
          </span>
        ) : null}
      </div>
      <div style={{ padding: '14px 14px 16px', display: 'grid', gap: 6 }}>
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
              color: HERMES_THEME_FG[theme],
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
            fontFamily:
              '"Overpass Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 11,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          --{token.name}
        </code>
        {token.description ? (
          <p
            style={{
              margin: 0,
              fontSize: 12,
              lineHeight: 1.55,
              color: HERMES_THEME_MUTED[theme],
            }}
          >
            {token.description}
          </p>
        ) : null}
      </div>
    </div>
  )
}

export function HermesColorGroupView({
  group,
  theme,
  interactive = true,
}: {
  group: HermesColorGroup
  theme: HermesThemeMode
  interactive?: boolean
}) {
  return (
    <section
      id={group.id}
      style={{
        display: 'grid',
        gap: 16,
        padding: '32px 0',
        borderTop: `1px solid ${HERMES_THEME_BORDER[theme]}`,
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
            color: HERMES_THEME_FG[theme],
            fontFamily:
              '"EB Garamond", "EBGaramond", "Bell MT", "Times New Roman", serif',
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
              lineHeight: 1.6,
              color: HERMES_THEME_MUTED[theme],
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
          gap: 16,
        }}
      >
        {group.tokens.map((t) => (
          <HermesSwatch
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

export function HermesColorBoard({
  theme,
  groups,
  title,
  subtitle,
}: {
  theme: HermesThemeMode
  groups: HermesColorGroup[]
  title: string
  subtitle?: string
}) {
  return (
    <section
      style={{
        backgroundColor: HERMES_THEME_BG[theme],
        color: HERMES_THEME_FG[theme],
        padding: '48px 32px 64px',
        breakBefore: 'page',
      }}
    >
      <header
        style={{ maxWidth: 1280, margin: '0 auto', display: 'grid', gap: 8 }}
      >
        <span
          style={{
            fontFamily:
              '"Overpass Mono", ui-monospace, SFMono-Regular, Menlo, monospace',
            fontSize: 11,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: HERMES_ACCENT,
          }}
        >
          Design system / Hermès
        </span>
        <h2
          style={{
            margin: 0,
            fontSize: 36,
            lineHeight: 1.05,
            letterSpacing: '-0.025em',
            fontWeight: 500,
            fontFamily:
              '"EB Garamond", "EBGaramond", "Bell MT", "Times New Roman", serif',
          }}
        >
          {title}
        </h2>
        {subtitle ? (
          <p
            style={{
              margin: 0,
              fontSize: 14,
              lineHeight: 1.6,
              color: HERMES_THEME_MUTED[theme],
              maxWidth: 760,
            }}
          >
            {subtitle}
          </p>
        ) : null}
      </header>
      <div style={{ maxWidth: 1280, margin: '0 auto' }}>
        {groups.map((g) => (
          <HermesColorGroupView
            key={g.id}
            group={g}
            theme={theme}
            interactive={false}
          />
        ))}
      </div>
    </section>
  )
}
