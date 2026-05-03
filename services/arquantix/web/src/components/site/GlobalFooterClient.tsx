'use client'

import { usePathname } from 'next/navigation'
import { Footer } from '@/components/sections/Footer'
import type { SiteFooterData } from '@/lib/cms/site-footer'

type Props = {
  data: SiteFooterData
}

/**
 * Affiche le footer global partout sauf sous /admin (édition).
 */
export function GlobalFooterClient({ data }: Props) {
  const pathname = usePathname()
  if (pathname?.startsWith('/admin')) {
    return null
  }

  return <Footer data={data} />
}
