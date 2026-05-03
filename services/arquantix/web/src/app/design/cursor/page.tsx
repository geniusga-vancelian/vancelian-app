import type { Metadata } from 'next'
import { CursorColorsShowcase } from '@/components/design-system-cursor/CursorColorsShowcase'

export const metadata: Metadata = {
  title: 'Design system — Cursor (couleurs)',
  description:
    'Tokens couleur extraits du site cursor.com (palette light + dark, foregrounds, borders, cartes, product, sémantique).',
}

export default function CursorDesignSystemPage() {
  return <CursorColorsShowcase />
}
