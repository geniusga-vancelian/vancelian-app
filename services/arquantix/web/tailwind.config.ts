import type { Config } from 'tailwindcss'

/**
 * Tailwind aligné sur le Design System Vancelian (`src/styles/vancelian-tokens.css`).
 *
 * - Surfaces : papier off-white (`bg-v-bg` = #F7F7F4), cartes #F2F1ED.
 * - Anthracite (`text-v-fg` = #1A1815) pour tout le texte.
 * - Terracotta (`text-v-terracotta` = #C0512E) réservée aux text-links / accents.
 * - Triade : terracotta · vert anglais · bleu de Prusse — jamais simultanées en aplat.
 * - Fonts : Inter (UI) / Newsreader (éditorial) / Newsreader Display (60pt+).
 * - Radius DS : 4 / 6 / 8 / 12 / 16 / 20 / 24 / 999.
 *
 * Les couleurs shadcn historiques (`primary`, `background`, `muted`, …) restent
 * exposées via les variables CSS remappées dans `design-system-theme.css`.
 */
const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      fontFamily: {
        ui: ['var(--v-font-ui)'],
        inter: ['var(--v-font-ui)'],
        editorial: ['var(--v-font-editorial)'],
        display: ['var(--v-font-display)'],
        newsreader: ['var(--v-font-editorial)'],
      },
      letterSpacing: {
        'v-tight': '-0.03em',
        'v-wide': '0.05em',
        'v-extrawide': '0.4em',
      },
      borderRadius: {
        // shadcn classique (mappé sur le palier DS card = 8px)
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
        xl: 'calc(var(--radius) + 4px)',
        // Échelle Vancelian — 5 paliers stricts + 3 alias marketing
        'v-tag': 'var(--v-radius-tag)',
        'v-input': 'var(--v-radius-input)',
        'v-card': 'var(--v-radius-card)',
        'v-modal': 'var(--v-radius-modal)',
        'v-lg': 'var(--v-radius-lg)',
        'v-xl': 'var(--v-radius-xl)',
        'v-2xl': 'var(--v-radius-2xl)',
        'v-pill': 'var(--v-radius-pill)',
      },
      boxShadow: {
        'v-flat': 'none',
        'v-subtle': 'var(--v-elev-subtle)',
        'v-medium': 'var(--v-elev-medium)',
      },
      transitionTimingFunction: {
        'v-out': 'cubic-bezier(0.22, 1, 0.36, 1)',
        'v-in-out': 'cubic-bezier(0.65, 0, 0.35, 1)',
      },
      transitionDuration: {
        'v-fast': '120ms',
        'v-base': '200ms',
        'v-slow': '320ms',
      },
      ringOffsetColor: {
        background: 'var(--background)',
      },
      colors: {
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        card: {
          DEFAULT: 'var(--card)',
          foreground: 'var(--card-foreground)',
        },
        popover: {
          DEFAULT: 'var(--popover)',
          foreground: 'var(--popover-foreground)',
        },
        primary: {
          DEFAULT: 'var(--primary)',
          foreground: 'var(--primary-foreground)',
        },
        secondary: {
          DEFAULT: 'var(--secondary)',
          foreground: 'var(--secondary-foreground)',
        },
        muted: {
          DEFAULT: 'var(--muted)',
          foreground: 'var(--muted-foreground)',
        },
        accent: {
          DEFAULT: 'var(--accent)',
          foreground: 'var(--accent-foreground)',
        },
        destructive: {
          DEFAULT: 'var(--destructive)',
          foreground: 'var(--destructive-foreground)',
        },
        border: 'var(--border)',
        input: 'var(--input)',
        ring: 'var(--ring)',
        'input-background': 'var(--input-background)',
        'switch-background': 'var(--switch-background)',
        chart: {
          1: 'var(--chart-1)',
          2: 'var(--chart-2)',
          3: 'var(--chart-3)',
          4: 'var(--chart-4)',
          5: 'var(--chart-5)',
        },
        sidebar: {
          DEFAULT: 'var(--sidebar)',
          foreground: 'var(--sidebar-foreground)',
          primary: 'var(--sidebar-primary)',
          'primary-foreground': 'var(--sidebar-primary-foreground)',
          accent: 'var(--sidebar-accent)',
          'accent-foreground': 'var(--sidebar-accent-foreground)',
          border: 'var(--sidebar-border)',
          ring: 'var(--sidebar-ring)',
        },
        // Palette Vancelian — préfixée `v-` pour rester explicite.
        v: {
          // Surfaces
          bg: 'var(--v-bg)',
          'bg-photo': 'var(--v-bg-photo)',
          card: 'var(--v-card)',
          'card-warm': 'var(--v-card-warm)',
          'card-hover': 'var(--v-card-hover)',
          'dark-bg': 'var(--v-dark-bg)',
          // Texte
          fg: 'var(--v-fg)',
          'fg-body': 'var(--v-fg-body)',
          'fg-muted': 'var(--v-fg-muted)',
          'fg-light': 'var(--v-fg-light)',
          'fg-20': 'var(--v-fg-20)',
          'fg-10': 'var(--v-fg-10)',
          'fg-05': 'var(--v-fg-05)',
          'dark-fg': 'var(--v-dark-fg)',
          // Triade identitaire
          terracotta: 'var(--v-terracotta)',
          'terracotta-pressed': 'var(--v-terracotta-pressed)',
          'terracotta-bg': 'var(--v-terracotta-bg)',
          'terracotta-bg-strong': 'var(--v-terracotta-bg-strong)',
          green: 'var(--v-green)',
          'green-bg': 'var(--v-green-bg)',
          blue: 'var(--v-blue)',
          'blue-bg': 'var(--v-blue-bg)',
          // Sémantiques
          success: 'var(--v-success)',
          'success-bg': 'var(--v-success-bg)',
          warning: 'var(--v-warning)',
          'warning-bg': 'var(--v-warning-bg)',
          info: 'var(--v-info)',
          'info-bg': 'var(--v-info-bg)',
          error: 'var(--v-error)',
          'error-bg': 'var(--v-error-bg)',
        },
        // Ponts historiques — remappés vers la triade Vancelian pour la
        // compatibilité ascendante des classes existantes (`bg-brand-bronze`…).
        brand: {
          bronze: 'var(--v-terracotta)',      // historique #742232 → terracotta DS
          beige: 'var(--v-card-warm)',        // historique #C6A47C → card warm
          terracotta: 'var(--v-terracotta)',
          green: 'var(--v-green)',
          blue: 'var(--v-blue)',
        },
        neutral: {
          black: 'var(--v-fg)',               // historique #0B0D10 → anthracite DS
          light: 'var(--v-fg-10)',
          white: '#FFFFFF',
        },
      },
      spacing: {
        // Échelle Vancelian — 8 paliers stricts (4 / 8 / 12 / 16 / 24 / 32 / 48 / 64)
        'v-xs': 'var(--v-space-xs)',
        'v-sm': 'var(--v-space-sm)',
        'v-md': 'var(--v-space-md)',
        'v-lg': 'var(--v-space-lg)',
        'v-xl': 'var(--v-space-xl)',
        'v-2xl': 'var(--v-space-2xl)',
        'v-3xl': 'var(--v-space-3xl)',
        'v-4xl': 'var(--v-space-4xl)',
      },
      maxWidth: {
        'v-container': 'var(--v-container-desktop)',
      },
    },
  },
  plugins: [],
}
export default config
