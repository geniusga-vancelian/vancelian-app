import type { Metadata } from 'next'
import { HermesShowcase } from '@/components/design-system-hermes/HermesShowcase'

export const metadata: Metadata = {
  title: 'Design system — Hermès',
  description:
    'Tokens couleurs, typographie, layout et composants extraits du site hermes.com (palette beige + dark, EB Garamond, Manrope, Overpass Mono).',
}

export default function HermesDesignSystemPage() {
  return <HermesShowcase />
}
