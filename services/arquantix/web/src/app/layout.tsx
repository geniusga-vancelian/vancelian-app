import type { Metadata } from 'next'
import '../styles/globals.css'
// TODO: Le CSS exporté Figma (Tailwind v4) n'est pas compatible avec Tailwind v3
// Les composants utilisent déjà des classes Tailwind, ils devraient fonctionner sans
// import '../styles/figma-export.css'

export const metadata: Metadata = {
  title: 'Arquantix — Coming Soon',
  description: 'Fractional Real Estate, Institutional Rigor.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  )
}

