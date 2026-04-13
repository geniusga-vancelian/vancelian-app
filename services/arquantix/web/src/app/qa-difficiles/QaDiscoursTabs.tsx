'use client'

import Link from 'next/link'
import { useEffect, useMemo, useState } from 'react'
import { usePathname, useSearchParams } from 'next/navigation'

type Tab = 'qa' | 'discours'

function tabFromSearchParams(
  sp: { get: (name: string) => string | null } | null,
): Tab {
  if (!sp) return 'qa'
  return sp.get('v') === 'discours' ? 'discours' : 'qa'
}

export function QaDiscoursTabs({
  qa,
  discours,
}: {
  qa: React.ReactNode
  discours: React.ReactNode
}) {
  const searchParams = useSearchParams()
  const pathname = usePathname() ?? '/qa-difficiles'

  const hrefQa = useMemo(() => {
    const raw = searchParams?.toString() ?? ''
    const p = new URLSearchParams(raw)
    p.delete('v')
    const q = p.toString()
    return q ? `${pathname}?${q}` : pathname
  }, [pathname, searchParams])

  const hrefDiscours = useMemo(() => {
    const raw = searchParams?.toString() ?? ''
    const p = new URLSearchParams(raw)
    p.set('v', 'discours')
    return `${pathname}?${p.toString()}`
  }, [pathname, searchParams])

  const tabFromUrl = useMemo(
    () => tabFromSearchParams(searchParams),
    [searchParams],
  )

  const [tab, setTab] = useState<Tab>(tabFromUrl)

  useEffect(() => {
    setTab(tabFromUrl)
  }, [tabFromUrl])

  return (
    <div className="min-h-screen bg-neutral-100 text-neutral-900">
      <div className="sticky top-0 z-[100] border-b border-neutral-200/90 bg-neutral-50/95 px-3 py-2 backdrop-blur supports-[backdrop-filter]:bg-neutral-50/85">
        <div className="mx-auto flex max-w-[1800px] flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="hidden text-[11px] font-medium text-neutral-500 sm:inline">
              Réunion
            </span>
            <div
              role="tablist"
              aria-label="Choisir l’onglet"
              className="relative z-[101] flex rounded-lg border border-neutral-200 bg-white p-0.5 shadow-sm"
            >
              <Link
                href={hrefQa}
                scroll={false}
                prefetch
                role="tab"
                aria-selected={tab === 'qa'}
                onClick={() => setTab('qa')}
                className={`inline-flex cursor-pointer select-none items-center rounded-md px-2.5 py-1 text-[11px] font-medium no-underline transition ${
                  tab === 'qa'
                    ? 'bg-neutral-900 text-white shadow-sm'
                    : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                }`}
              >
                Synthèse Q&amp;R
              </Link>
              <Link
                href={hrefDiscours}
                scroll={false}
                prefetch
                role="tab"
                aria-selected={tab === 'discours'}
                onClick={() => setTab('discours')}
                className={`inline-flex cursor-pointer select-none items-center rounded-md px-2.5 py-1 text-[11px] font-medium no-underline transition ${
                  tab === 'discours'
                    ? 'bg-neutral-900 text-white shadow-sm'
                    : 'text-neutral-600 hover:bg-neutral-50 hover:text-neutral-900'
                }`}
              >
                🎤 Discours
              </Link>
            </div>
          </div>
          <Link
            href="/"
            className="relative z-[101] text-[11px] text-neutral-500 underline-offset-2 hover:text-neutral-800 hover:underline"
          >
            Accueil
          </Link>
        </div>
      </div>
      {tab === 'qa' ? qa : discours}
    </div>
  )
}
