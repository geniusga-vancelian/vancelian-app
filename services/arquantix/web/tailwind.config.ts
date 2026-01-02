import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'var(--background)',
        foreground: 'var(--foreground)',
        brand: {
          bronze: '#742232',
          beige: '#C6A47C',
        },
        neutral: {
          black: '#0B0D10',
          light: '#E6E6E6',
          white: '#FFFFFF',
        },
      },
    },
  },
  plugins: [],
}
export default config
