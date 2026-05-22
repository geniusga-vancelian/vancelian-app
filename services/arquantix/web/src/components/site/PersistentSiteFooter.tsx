'use client'

import * as React from 'react'
import { usePathname } from 'next/navigation'
import { Footer } from '@/components/sections/Footer'
import type { SiteFooterData } from '@/lib/cms/site-footer'
import { shellLocaleFromPathname } from '@/lib/site/shellLocaleFromPathname'
import type { Locale } from '@/config/locales'

type Props = {
  /** Bootstrap SSR — affiché immédiatement, cache client ensuite. */
  initialData?: SiteFooterData
}

function shouldHideFooter(pathname: string): boolean {
  if (pathname.startsWith('/admin')) return true
  if (pathname.startsWith('/preview/common-module')) return true
  if (pathname.startsWith('/preview/section/')) return true
  if (pathname.startsWith('/preview/email/')) return true
  if (pathname.startsWith('/preview/section-demo/')) return true
  if (pathname.startsWith('/preview/article-block-demo/')) return true
  if (pathname.startsWith('/design/cursor/print')) return true
  return false
}

/**
 * Footer global persistant : monté une fois, données bootstrap SSR ou fetch par locale.
 */
export function PersistentSiteFooter({ initialData }: Props) {
  const pathname = usePathname() ?? ''
  const locale = shellLocaleFromPathname(pathname)
  const cacheRef = React.useRef<Map<Locale, SiteFooterData>>(
    initialData ? new Map([[locale, initialData]]) : new Map(),
  )
  const [footerData, setFooterData] = React.useState<SiteFooterData | null>(
    () => initialData ?? cacheRef.current.get(locale) ?? null,
  )

  React.useEffect(() => {
    if (shouldHideFooter(pathname)) return

    const cached = cacheRef.current.get(locale)
    if (cached) {
      setFooterData(cached)
      return
    }

    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch(`/api/site/footer?locale=${locale}`)
        if (!res.ok || cancelled) return
        const data = (await res.json()) as SiteFooterData
        cacheRef.current.set(locale, data)
        if (!cancelled) setFooterData(data)
      } catch {
        /* garder l’état courant */
      }
    })()

    return () => {
      cancelled = true
    }
  }, [pathname, locale])

  if (shouldHideFooter(pathname) || !footerData) {
    return null
  }

  return <Footer data={footerData} />
}
