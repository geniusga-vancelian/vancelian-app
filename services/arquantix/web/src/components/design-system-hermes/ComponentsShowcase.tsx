'use client'

import {
  HERMES_ACCENT,
  HERMES_THEME_BORDER,
  HERMES_THEME_CARD,
  HERMES_THEME_FG,
  HERMES_THEME_MUTED,
  type HermesThemeMode,
} from './themeUtils'

const FONT_PRIMARY = '"Manrope", "Roboto", sans-serif'
const FONT_EDITO =
  '"EB Garamond", "EBGaramond", "Bell MT", "Times New Roman", serif'
const FONT_MONO = '"Overpass Mono", ui-monospace, monospace'

/* -------------------------------------------------------------------------- */
/*  Section utilitaire                                                         */
/* -------------------------------------------------------------------------- */

function Subsection({
  title,
  description,
  children,
  theme,
}: {
  title: string
  description?: string
  children: React.ReactNode
  theme: HermesThemeMode
}) {
  return (
    <div style={{ display: 'grid', gap: 14 }}>
      <header style={{ display: 'grid', gap: 4 }}>
        <h3
          style={{
            margin: 0,
            fontSize: 16,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
          }}
        >
          {title}
        </h3>
        {description ? (
          <p
            style={{
              margin: 0,
              fontSize: 12,
              lineHeight: 1.55,
              color: HERMES_THEME_MUTED[theme],
              maxWidth: 720,
            }}
          >
            {description}
          </p>
        ) : null}
      </header>
      {children}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Atomes : Logo, Lockup                                                      */
/* -------------------------------------------------------------------------- */

function HermesWordmark({
  size = 26,
  color = '#000',
}: {
  size?: number
  color?: string
}) {
  return (
    <span
      style={{
        fontFamily: FONT_EDITO,
        fontSize: size,
        letterSpacing: '0.06em',
        fontWeight: 500,
        color,
        whiteSpace: 'nowrap',
      }}
    >
      HERMÈS
    </span>
  )
}

function HermesLockup({ theme }: { theme: HermesThemeMode }) {
  return (
    <div
      style={{
        display: 'grid',
        placeItems: 'center',
        gap: 4,
        padding: '32px 48px',
        background: HERMES_THEME_CARD[theme],
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        textAlign: 'center',
      }}
    >
      <HermesWordmark size={28} color={HERMES_THEME_FG[theme]} />
      <span
        style={{
          fontFamily: FONT_PRIMARY,
          fontSize: 9,
          letterSpacing: '0.32em',
          textTransform: 'uppercase',
          color: HERMES_THEME_MUTED[theme],
        }}
      >
        Paris
      </span>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Boutons                                                                    */
/* -------------------------------------------------------------------------- */

function PrimaryButton({
  children,
  invert = false,
}: {
  children: React.ReactNode
  invert?: boolean
}) {
  return (
    <button
      type="button"
      style={{
        fontFamily: FONT_PRIMARY,
        fontSize: 13,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        background: invert ? '#fcf7f1' : '#000',
        color: invert ? '#000' : '#fcf7f1',
        border: 'none',
        padding: '14px 26px',
        borderRadius: 0,
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
  )
}

function OutlineButton({
  children,
  theme,
}: {
  children: React.ReactNode
  theme: HermesThemeMode
}) {
  return (
    <button
      type="button"
      style={{
        fontFamily: FONT_PRIMARY,
        fontSize: 13,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        background: 'transparent',
        color: HERMES_THEME_FG[theme],
        border: `1px solid ${HERMES_THEME_FG[theme]}`,
        padding: '13px 25px',
        borderRadius: 0,
        cursor: 'pointer',
      }}
    >
      {children}
    </button>
  )
}

function GhostLink({
  children,
  theme,
}: {
  children: React.ReactNode
  theme: HermesThemeMode
}) {
  return (
    <a
      href="#"
      onClick={(e) => e.preventDefault()}
      style={{
        fontFamily: FONT_PRIMARY,
        fontSize: 13,
        letterSpacing: '0.04em',
        textTransform: 'uppercase',
        color: HERMES_THEME_FG[theme],
        textDecoration: 'none',
        borderBottom: `1px solid ${HERMES_THEME_FG[theme]}`,
        paddingBottom: 2,
      }}
    >
      {children}
    </a>
  )
}

/* -------------------------------------------------------------------------- */
/*  Inputs                                                                     */
/* -------------------------------------------------------------------------- */

function TextField({
  label,
  state = 'default',
  value,
  theme,
}: {
  label: string
  state?: 'default' | 'focus' | 'error' | 'success' | 'disabled'
  value?: string
  theme: HermesThemeMode
}) {
  const colorByState: Record<typeof state, string> = {
    default: HERMES_THEME_BORDER[theme],
    focus: HERMES_THEME_FG[theme],
    error: '#9d2a1e',
    success: '#34784a',
    disabled: HERMES_THEME_BORDER[theme],
  }
  const fg = state === 'disabled' ? HERMES_THEME_MUTED[theme] : HERMES_THEME_FG[theme]
  return (
    <div style={{ display: 'grid', gap: 6 }}>
      <label
        style={{
          fontFamily: FONT_PRIMARY,
          fontSize: 11,
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
          color: HERMES_THEME_MUTED[theme],
        }}
      >
        {label}
      </label>
      <div
        style={{
          borderBottom: `1px solid ${colorByState[state]}`,
          paddingBottom: 8,
          opacity: state === 'disabled' ? 0.55 : 1,
          background: 'transparent',
        }}
      >
        <input
          type="text"
          defaultValue={value ?? ''}
          placeholder="Saisissez…"
          disabled={state === 'disabled'}
          style={{
            width: '100%',
            border: 'none',
            background: 'transparent',
            outline: 'none',
            fontFamily: FONT_PRIMARY,
            fontSize: 14,
            color: fg,
          }}
        />
      </div>
      {state === 'error' ? (
        <span style={{ fontSize: 11, color: '#9d2a1e' }}>
          Ce champ est requis.
        </span>
      ) : null}
      {state === 'success' ? (
        <span style={{ fontSize: 11, color: '#34784a' }}>
          Adresse valide.
        </span>
      ) : null}
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Header (mockup)                                                            */
/* -------------------------------------------------------------------------- */

function HeaderMockup({ theme }: { theme: HermesThemeMode }) {
  return (
    <div
      style={{
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        background: HERMES_THEME_CARD[theme],
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          height: 64,
          background: '#000',
          color: '#fcf7f1',
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          alignItems: 'center',
          padding: '0 24px',
        }}
      >
        <span
          style={{
            fontFamily: FONT_PRIMARY,
            fontSize: 11,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            opacity: 0.75,
          }}
        >
          Femme · Homme · Carrés · Maroquinerie
        </span>
        <HermesWordmark size={20} color="#fcf7f1" />
        <span
          style={{
            justifySelf: 'end',
            fontFamily: FONT_PRIMARY,
            fontSize: 11,
            letterSpacing: '0.12em',
            textTransform: 'uppercase',
            opacity: 0.75,
          }}
        >
          Recherche · Compte · Panier
        </span>
      </div>
      <div
        style={{
          height: 46,
          background: '#fcf7f1',
          color: '#2e2d2d',
          display: 'flex',
          gap: 28,
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: FONT_PRIMARY,
          fontSize: 12,
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
        }}
      >
        <span>Nouveautés</span>
        <span>Sacs &amp; pochettes</span>
        <span>Soieries</span>
        <span>Bijoux</span>
        <span style={{ color: HERMES_ACCENT }}>Cadeaux Hermès</span>
      </div>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Carte produit (mockup)                                                     */
/* -------------------------------------------------------------------------- */

function ProductCard({ theme }: { theme: HermesThemeMode }) {
  return (
    <article
      style={{
        background: HERMES_THEME_CARD[theme],
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        display: 'grid',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          aspectRatio: '4 / 5',
          background:
            'radial-gradient(circle at 50% 35%, #b75a18 0%, #9d2a1e 60%, #5e1d18 100%)',
          position: 'relative',
        }}
      >
        <span
          style={{
            position: 'absolute',
            top: 12,
            left: 12,
            fontFamily: FONT_PRIMARY,
            fontSize: 10,
            letterSpacing: '0.18em',
            textTransform: 'uppercase',
            color: '#fcf7f1',
            background: '#00000080',
            padding: '4px 8px',
          }}
        >
          Nouveau
        </span>
      </div>
      <div style={{ padding: '20px 22px 24px', display: 'grid', gap: 10 }}>
        <h4
          style={{
            margin: 0,
            fontFamily: FONT_EDITO,
            fontSize: 18,
            fontWeight: 500,
            color: HERMES_THEME_FG[theme],
            letterSpacing: '-0.005em',
          }}
        >
          Carré 90 « Brides de Gala »
        </h4>
        <p
          style={{
            margin: 0,
            fontFamily: FONT_PRIMARY,
            fontSize: 12,
            lineHeight: 1.55,
            color: HERMES_THEME_MUTED[theme],
          }}
        >
          Carré en twill de soie · 90 × 90 cm
        </p>
        <div
          style={{
            display: 'flex',
            alignItems: 'baseline',
            justifyContent: 'space-between',
            marginTop: 4,
          }}
        >
          <span
            style={{
              fontFamily: FONT_MONO,
              fontSize: 13,
              color: HERMES_THEME_FG[theme],
            }}
          >
            505,00 €
          </span>
          <span
            style={{
              fontFamily: FONT_PRIMARY,
              fontSize: 11,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: HERMES_THEME_MUTED[theme],
            }}
          >
            12 coloris
          </span>
        </div>
      </div>
    </article>
  )
}

/* -------------------------------------------------------------------------- */
/*  Surface (atom)                                                             */
/* -------------------------------------------------------------------------- */

function SurfaceTile({
  bg,
  fg,
  label,
  description,
  theme,
}: {
  bg: string
  fg: string
  label: string
  description: string
  theme: HermesThemeMode
}) {
  return (
    <div
      style={{
        background: bg,
        color: fg,
        padding: '28px 24px',
        border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
        display: 'grid',
        gap: 6,
        minHeight: 120,
      }}
    >
      <span
        style={{
          fontFamily: FONT_PRIMARY,
          fontSize: 11,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          opacity: 0.75,
        }}
      >
        Surface
      </span>
      <h4
        style={{
          margin: 0,
          fontFamily: FONT_EDITO,
          fontSize: 20,
          fontWeight: 500,
        }}
      >
        {label}
      </h4>
      <p
        style={{
          margin: 0,
          fontFamily: FONT_PRIMARY,
          fontSize: 12,
          lineHeight: 1.55,
          opacity: 0.85,
        }}
      >
        {description}
      </p>
    </div>
  )
}

/* -------------------------------------------------------------------------- */
/*  Vitrine principale                                                         */
/* -------------------------------------------------------------------------- */

export function HermesComponentsShowcase({ theme }: { theme: HermesThemeMode }) {
  return (
    <section
      id="components"
      style={{
        display: 'grid',
        gap: 32,
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
            fontFamily: FONT_EDITO,
          }}
        >
          Atomes &amp; composants
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
          Reproductions fidèles à hermes.com : wordmark, header bicolore, CTAs
          plats sans rayon, formulaires à liserés, carte produit en aplat
          beige. Tous les composants sont composés à partir des tokens couleur,
          typographie et layout listés plus haut.
        </p>
      </header>

      <Subsection
        title="Logo & lockup"
        description="Wordmark Hermès composé en EB Garamond, suivi de la mention « Paris » en Manrope tracking large."
        theme={theme}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
            gap: 16,
          }}
        >
          <HermesLockup theme={theme} />
          <div
            style={{
              background: '#000',
              padding: '32px 48px',
              border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
              display: 'grid',
              placeItems: 'center',
              gap: 4,
            }}
          >
            <HermesWordmark size={28} color="#fcf7f1" />
            <span
              style={{
                fontFamily: FONT_PRIMARY,
                fontSize: 9,
                letterSpacing: '0.32em',
                textTransform: 'uppercase',
                color: '#fcf7f1',
                opacity: 0.7,
              }}
            >
              Paris
            </span>
          </div>
          <div
            style={{
              background: HERMES_ACCENT,
              padding: '32px 48px',
              border: `1px solid ${HERMES_THEME_BORDER[theme]}`,
              display: 'grid',
              placeItems: 'center',
              gap: 4,
            }}
          >
            <HermesWordmark size={28} color="#fcf7f1" />
            <span
              style={{
                fontFamily: FONT_PRIMARY,
                fontSize: 9,
                letterSpacing: '0.32em',
                textTransform: 'uppercase',
                color: '#fcf7f1',
                opacity: 0.85,
              }}
            >
              Sur Rouge H
            </span>
          </div>
        </div>
      </Subsection>

      <Subsection
        title="Header bicolore"
        description="Bandeau noir 64 px (top desktop) + barre de catégories beige 46 px = 110 px (--header-height-desktop-with-menu)."
        theme={theme}
      >
        <HeaderMockup theme={theme} />
      </Subsection>

      <Subsection
        title="Boutons & liens"
        description="Trois variantes : primaire (full noir), outline (1 px de liseré), ghost (souligné). Toujours en uppercase Manrope, jamais arrondis."
        theme={theme}
      >
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: 14,
            alignItems: 'center',
          }}
        >
          <PrimaryButton>Ajouter au panier</PrimaryButton>
          <PrimaryButton invert>Sur fond noir</PrimaryButton>
          <OutlineButton theme={theme}>Découvrir</OutlineButton>
          <GhostLink theme={theme}>Voir la collection</GhostLink>
        </div>
      </Subsection>

      <Subsection
        title="Champs de formulaire"
        description="Inputs sans bordure, simple liseré bas. Etats focus (encre noire), error (Rouge H), success (vert)."
        theme={theme}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 24,
          }}
        >
          <TextField label="Prénom" theme={theme} />
          <TextField label="Email" state="focus" value="moi@hermes.com" theme={theme} />
          <TextField label="Code postal" state="error" value="" theme={theme} />
          <TextField label="Adresse" state="success" value="24 rue du Faubourg Saint-Honoré" theme={theme} />
          <TextField label="Téléphone" state="disabled" value="—" theme={theme} />
        </div>
      </Subsection>

      <Subsection
        title="Carte produit"
        description="Image carrée 4:5, badge de statut en surimpression, prix en Overpass Mono, titre en EB Garamond."
        theme={theme}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
            gap: 16,
            maxWidth: 760,
          }}
        >
          <ProductCard theme={theme} />
          <ProductCard theme={theme} />
        </div>
      </Subsection>

      <Subsection
        title="Surfaces (atom)"
        description="Combinaisons typiques de fond / encre. Le contraste reste toujours dans la palette beige × dark, sans ombre."
        theme={theme}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
            gap: 16,
          }}
        >
          <SurfaceTile
            bg="#fcf7f1"
            fg="#2e2d2d"
            label="Beige sur encre"
            description="Surface par défaut du site (page background)."
            theme={theme}
          />
          <SurfaceTile
            bg="#fffcf7"
            fg="#2e2d2d"
            label="Papyrus"
            description="Surface card posée sur beige."
            theme={theme}
          />
          <SurfaceTile
            bg="#000"
            fg="#fcf7f1"
            label="Encre pleine"
            description="CTAs, header, sections de contraste."
            theme={theme}
          />
          <SurfaceTile
            bg="#9d2a1e"
            fg="#fcf7f1"
            label="Rouge H"
            description="Accent éditorial : campagne, push spécifique."
            theme={theme}
          />
        </div>
      </Subsection>
    </section>
  )
}
