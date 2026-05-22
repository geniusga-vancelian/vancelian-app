import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Vancelian — Espace client',
  robots: { index: false, follow: false },
}

/** Layout portail authentifié — sans Privy (session JWT cookies après login). */
export default function PortalAppLayout({ children }: { children: React.ReactNode }) {
  return children
}
