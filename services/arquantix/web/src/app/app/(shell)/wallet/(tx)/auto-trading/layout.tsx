import type { Metadata } from 'next'
import '@/styles/portal-auth.css'

export const metadata: Metadata = {
  title: 'Vancelian — Exécution automatique',
  robots: { index: false, follow: false },
}

export default function PortalWalletAutoTradingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
