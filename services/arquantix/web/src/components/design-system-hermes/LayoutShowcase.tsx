'use client'

import {
  HERMES_ACCENT,
  HERMES_THEME_BORDER,
  HERMES_THEME_CARD,
  HERMES_THEME_FG,
  HERMES_THEME_MUTED,
  type HermesThemeMode,
} from './themeUtils'
import {
  hermesBreakpoints,
  hermesHeaderHeights,
  hermesLayoutGutters,
  hermesZIndex,
  type HermesLayoutToken,
} from './tokens/layout'

function TokenLine({
  token,
  theme,
  trailing,
}: {
  token: HermesLayoutToken
  theme: HermesThemeMode
  trailing?: React.ReactNode
}) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(220px, 1fr) 110px auto',
        alignItems: 'center',
        gap: 16,
        padding: '14px 16px',
        borderTop: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        breakInside: 'avoid',
      }}
    >
      <div style={{ display: 'grid', gap: 2 }}>
        <span
          style={{
            fontSize: 13,
            color: HERMES_THEME_FG[theme],
            fontWeight: 500,
          }}
        >
          {token.label}
        </span>
        <code
          style={{
            fontFamily: '"Overpass Mono", ui-monospace, monospace',
            fontSize: 11,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          --{token.name}
        </code>
        {token.description ? (
          <span
            style={{
              fontSize: 12,
              color: HERMES_THEME_MUTED[theme],
              lineHeight: 1.55,
            }}
          >
            {token.description}
          </span>
        ) : null}
      </div>
      <code
        style={{
          fontFamily: '"Overpass Mono", ui-monospace, monospace',
          fontSize: 12,
          color: HERMES_ACCENT,
          textAlign: 'right',
        }}
      >
        {token.value}
      </code>
      <div style={{ minWidth: 220, justifySelf: 'end' }}>{trailing}</div>
    </div>
  )
}

function HeaderVisual({
  height,
  theme,
}: {
  height: string
  theme: HermesThemeMode
}) {
  const px = parseInt(height, 10)
  return (
    <div
      style={{
        width: 220,
        height: Math.min(120, px * 1.4),
        position: 'relative',
        background: HERMES_THEME_CARD[theme],
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: Math.min(80, px),
          background: '#000',
          color: '#fcf7f1',
          fontFamily: '"EB Garamond", "EBGaramond", serif',
          fontSize: 14,
          letterSpacing: '0.06em',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        HERMÈS
      </div>
      <span
        style={{
          position: 'absolute',
          right: 6,
          top: Math.min(80, px) + 4,
          fontFamily: '"Overpass Mono", ui-monospace, monospace',
          fontSize: 10,
          color: HERMES_THEME_MUTED[theme],
        }}
      >
        {height}
      </span>
    </div>
  )
}

function GutterVisual({ value, theme }: { value: string; theme: HermesThemeMode }) {
  const px = Math.min(160, parseInt(value, 10) * 4)
  return (
    <div
      style={{
        width: 220,
        height: 40,
        position: 'relative',
        background:
          'repeating-linear-gradient(45deg, transparent 0 4px, ' +
          HERMES_THEME_BORDER[theme] +
          ' 4px 5px)',
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          width: Math.max(6, px),
          background: HERMES_ACCENT,
          opacity: 0.5,
        }}
      />
    </div>
  )
}

function ZIndexVisual({ value, theme }: { value: string; theme: HermesThemeMode }) {
  const v = parseInt(value, 10)
  const layers = Math.min(6, Math.max(1, Math.round(Math.log10(v + 1) * 1.4)))
  return (
    <div style={{ position: 'relative', width: 90, height: 40 }}>
      {Array.from({ length: layers }).map((_, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            top: i * 5,
            left: i * 8,
            width: 60,
            height: 24,
            background: HERMES_THEME_CARD[theme],
            border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
          }}
        />
      ))}
    </div>
  )
}

export function HermesLayoutShowcase({ theme }: { theme: HermesThemeMode }) {
  return (
    <section
      id="layout"
      style={{
        display: 'grid',
        gap: 28,
        padding: '40px 0',
        borderTop: `1px solid ${HERMES_THEME_BORDER[theme]}`,
      }}
    >
      <header style={{ display: 'grid', gap: 6 }}>
        <h2
          style={{
            margin: 0,
            fontSize: 26,
            fontWeight: 500,
            letterSpacing: '-0.02em',
            color: HERMES_THEME_FG[theme],
            fontFamily:
              '"EB Garamond", "EBGaramond", "Bell MT", "Times New Roman", serif',
          }}
        >
          Layout & élévation
        </h2>
        <p
          style={{
            margin: 0,
            maxWidth: 760,
            fontSize: 14,
            lineHeight: 1.6,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          Trois familles de containers (adaptive, narrow, fixe), trois
          breakpoints, des hauteurs de header différenciées et une échelle
          d’élévation très resserrée (header 300, livechat 999).
        </p>
      </header>

      <div>
        <h3
          style={{
            margin: '0 0 8px',
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
          }}
        >
          Breakpoints
        </h3>
        <div>
          {hermesBreakpoints.map((t) => (
            <TokenLine key={t.name} token={t} theme={theme} />
          ))}
        </div>
      </div>

      <div>
        <h3
          style={{
            margin: '0 0 8px',
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
          }}
        >
          Header heights
        </h3>
        <div>
          {hermesHeaderHeights.map((t) => (
            <TokenLine
              key={t.name}
              token={t}
              theme={theme}
              trailing={<HeaderVisual height={t.value} theme={theme} />}
            />
          ))}
        </div>
      </div>

      <div>
        <h3
          style={{
            margin: '0 0 8px',
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
          }}
        >
          Gouttières & largeurs max
        </h3>
        <div>
          {hermesLayoutGutters.map((t) => (
            <TokenLine
              key={t.name}
              token={t}
              theme={theme}
              trailing={
                t.value.endsWith('px') && parseInt(t.value, 10) < 200 ? (
                  <GutterVisual value={t.value} theme={theme} />
                ) : (
                  <code
                    style={{
                      fontFamily: '"Overpass Mono", ui-monospace, monospace',
                      fontSize: 11,
                      color: HERMES_THEME_MUTED[theme],
                    }}
                  >
                    container max
                  </code>
                )
              }
            />
          ))}
        </div>
      </div>

      <div>
        <h3
          style={{
            margin: '0 0 8px',
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
          }}
        >
          Z-index
        </h3>
        <div>
          {hermesZIndex.map((t) => (
            <TokenLine
              key={t.name}
              token={t}
              theme={theme}
              trailing={<ZIndexVisual value={t.value} theme={theme} />}
            />
          ))}
        </div>
      </div>
    </section>
  )
}
