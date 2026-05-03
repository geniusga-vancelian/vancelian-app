import type { Metadata } from 'next'
import { AdminDesignSystemShowcase } from '@/components/admin/AdminDesignSystemShowcase'

export const metadata: Metadata = {
  title: 'Design System — Admin',
  description:
    'Couleurs, typographie et composants Figma (extracted) pour le site Arquantix.',
}

export default function AdminDesignSystemPage() {
  return <AdminDesignSystemShowcase />
}
