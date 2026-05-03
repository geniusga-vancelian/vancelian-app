import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Guide local — Arquantix',
  description:
    'Fiche pratique pour utiliser la stack locale (recovery) : commandes sûres, diagnostic, sans jargon.',
}

export default function GuideLayout({ children }: { children: React.ReactNode }) {
  return children
}
