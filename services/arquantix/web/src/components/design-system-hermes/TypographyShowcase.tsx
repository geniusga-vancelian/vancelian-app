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
  hermesBodySizes,
  hermesFontFamilies,
  hermesFontWeights,
  hermesHeadingSizes,
  hermesLetterSpacings,
  type HermesFontSizeToken,
  type HermesFontToken,
  type HermesFontWeightToken,
} from './tokens/typography'

const SAMPLE_HEADING = 'L’audace, naturellement.'
const SAMPLE_BODY =
  'Hermès, maison française fondée en 1837 à Paris, perpétue depuis six générations un savoir-faire artisanal au service de la création.'

function FamilyCard({
  font,
  theme,
}: {
  font: HermesFontToken
  theme: HermesThemeMode
}) {
  return (
    <article
      style={{
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        background: HERMES_THEME_CARD[theme],
        padding: '24px 24px 28px',
        display: 'grid',
        gap: 14,
        breakInside: 'avoid',
      }}
    >
      <header style={{ display: 'grid', gap: 6 }}>
        <span
          style={{
            fontFamily: '"Overpass Mono", ui-monospace, monospace',
            fontSize: 10,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: HERMES_ACCENT,
          }}
        >
          --{font.name}
        </span>
        <h3
          style={{
            margin: 0,
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
            letterSpacing: '-0.005em',
          }}
        >
          {font.label}
        </h3>
        <p
          style={{
            margin: 0,
            fontSize: 12,
            lineHeight: 1.55,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          {font.role}
        </p>
      </header>

      <div
        style={{
          display: 'grid',
          gap: 4,
          paddingTop: 8,
          borderTop: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        }}
      >
        <div
          style={{
            fontFamily: font.stack,
            fontSize: 36,
            lineHeight: 1.1,
            fontWeight: 400,
            color: HERMES_THEME_FG[theme],
          }}
        >
          {font.sample ?? 'Hh — 0123456789'}
        </div>
        <div
          style={{
            fontFamily: font.stack,
            fontSize: 14,
            lineHeight: 1.6,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          {SAMPLE_BODY}
        </div>
      </div>

      <code
        style={{
          fontFamily: '"Overpass Mono", ui-monospace, monospace',
          fontSize: 11,
          color: HERMES_THEME_MUTED[theme],
          wordBreak: 'break-all',
        }}
      >
        {font.stack}
      </code>
    </article>
  )
}

function SizeRow({
  token,
  theme,
  family,
  scale,
}: {
  token: HermesFontSizeToken
  theme: HermesThemeMode
  family: string
  scale: 'heading' | 'body'
}) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '180px 1fr 96px',
        alignItems: 'baseline',
        gap: 16,
        padding: '14px 0',
        borderTop: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        breakInside: 'avoid',
      }}
    >
      <div style={{ display: 'grid', gap: 2 }}>
        <code
          style={{
            fontFamily: '"Overpass Mono", ui-monospace, monospace',
            fontSize: 11,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          --{token.name}
        </code>
        <span
          style={{
            fontFamily: '"Overpass Mono", ui-monospace, monospace',
            fontSize: 10,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          {token.value} • {token.px}px
        </span>
      </div>
      <div
        style={{
          fontFamily: family,
          fontSize: token.value,
          lineHeight: scale === 'heading' ? 1.15 : 1.5,
          color: HERMES_THEME_FG[theme],
          fontWeight: scale === 'heading' ? 500 : 400,
        }}
      >
        {scale === 'heading'
          ? `${token.label} — ${SAMPLE_HEADING}`
          : `${token.label} — ${SAMPLE_BODY}`}
      </div>
      <span
        style={{
          fontSize: 11,
          color: HERMES_THEME_MUTED[theme],
          textAlign: 'right',
        }}
      >
        {token.label}
      </span>
    </div>
  )
}

function WeightCard({
  weight,
  theme,
  family,
}: {
  weight: HermesFontWeightToken
  theme: HermesThemeMode
  family: string
}) {
  return (
    <div
      style={{
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        background: HERMES_THEME_CARD[theme],
        padding: '18px 18px 20px',
        display: 'grid',
        gap: 8,
        breakInside: 'avoid',
      }}
    >
      <span
        style={{
          fontFamily: '"Overpass Mono", ui-monospace, monospace',
          fontSize: 10,
          color: HERMES_THEME_MUTED[theme],
        }}
      >
        --{weight.name}
      </span>
      <div
        style={{
          fontFamily: family,
          fontSize: 32,
          fontWeight: weight.value,
          color: HERMES_THEME_FG[theme],
          lineHeight: 1.1,
        }}
      >
        Aa
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
        <span
          style={{ fontSize: 12, color: HERMES_THEME_FG[theme], fontWeight: 500 }}
        >
          {weight.label}
        </span>
        <span
          style={{
            fontFamily: '"Overpass Mono", ui-monospace, monospace',
            fontSize: 11,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          {weight.value}
        </span>
      </div>
    </div>
  )
}

export function HermesTypographyShowcase({ theme }: { theme: HermesThemeMode }) {
  return (
    <section
      id="typography"
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
          Typographie
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
          Trois familles principales (Manrope, Overpass Mono, EB Garamond) +
          cinq familles vedettes utilisées pour les pages campagne. Échelle
          parallèle « heading » et « body », plus 8 graisses.
        </p>
      </header>

      <div>
        <h3
          style={{
            margin: '0 0 14px',
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
          }}
        >
          Familles
        </h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: 16,
          }}
        >
          {hermesFontFamilies.map((f) => (
            <FamilyCard key={f.name} font={f} theme={theme} />
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
          Échelle « heading » (font-edito — EB Garamond)
        </h3>
        <p
          style={{
            margin: '0 0 4px',
            fontSize: 12,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          Valeurs « default desktop ». Sur ja/ko/zh-Hans/zh-Hant les tailles
          sont réduites (voir <code>fontMaps</code>).
        </p>
        <div>
          {hermesHeadingSizes.map((t) => (
            <SizeRow
              key={t.name}
              token={t}
              theme={theme}
              family='"EB Garamond", "EBGaramond", "Bell MT", "Times New Roman", serif'
              scale="heading"
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
          Échelle « body » (font-primary — Manrope)
        </h3>
        <div>
          {hermesBodySizes.map((t) => (
            <SizeRow
              key={t.name}
              token={t}
              theme={theme}
              family='"Manrope", "Roboto", sans-serif'
              scale="body"
            />
          ))}
        </div>
      </div>

      <div>
        <h3
          style={{
            margin: '0 0 14px',
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
          }}
        >
          Graisses
        </h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
            gap: 12,
          }}
        >
          {hermesFontWeights.map((w) => (
            <WeightCard
              key={w.name}
              weight={w}
              theme={theme}
              family='"Manrope", "Roboto", sans-serif'
            />
          ))}
        </div>
      </div>

      <div>
        <h3
          style={{
            margin: '0 0 14px',
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
          }}
        >
          Letter-spacing
        </h3>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 12,
          }}
        >
          {hermesLetterSpacings.map((ls) => (
            <div
              key={ls.name}
              style={{
                border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
                background: HERMES_THEME_CARD[theme],
                padding: '16px 18px',
                display: 'grid',
                gap: 8,
              }}
            >
              <div
                style={{
                  fontFamily: '"Manrope", "Roboto", sans-serif',
                  fontSize: 14,
                  textTransform: 'uppercase',
                  letterSpacing: ls.value,
                  color: HERMES_THEME_FG[theme],
                }}
              >
                Hermès Paris
              </div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  fontSize: 11,
                  color: HERMES_THEME_MUTED[theme],
                  fontFamily: '"Overpass Mono", ui-monospace, monospace',
                }}
              >
                <span>--{ls.name}</span>
                <span>{ls.value}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
