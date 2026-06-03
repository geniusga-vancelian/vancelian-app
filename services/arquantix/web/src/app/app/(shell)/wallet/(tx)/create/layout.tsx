import type { Metadata } from 'next'
import '@/styles/portal-auth.css'

export const metadata: Metadata = {
  title: 'Vancelian — Create wallet',
  robots: { index: false, follow: false },
}

export default function PortalWalletCreateLayout({ children }: { children: React.ReactNode }) {
  return children
}
