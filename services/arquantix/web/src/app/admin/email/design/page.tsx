import type { Metadata } from 'next'
import { EmailDesignSystemShowcase } from '@/components/admin/email-ds/EmailDesignSystemShowcase'

export const metadata: Metadata = {
  title: 'Email Design System — Admin',
  description:
    'Tokens, composants et exemple newsletter du DS HTML e-mail Arquantix.',
}

export default function AdminEmailDesignPage() {
  return <EmailDesignSystemShowcase />
}
