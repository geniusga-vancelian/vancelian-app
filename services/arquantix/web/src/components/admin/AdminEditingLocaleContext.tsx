'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Locale } from '@/config/locales'
import { defaultLocale, getLocaleOrDefault, isValidLocale, supportedLocales } from '@/config/locales'

type Ctx = {
  locale: Locale
  setLocale: (l: Locale) => void
  cycleLocale: () => void
  editingLocales: Locale[]
  siteSettingsLoaded: boolean
}

const AdminEditingLocaleContext = createContext<Ctx | null>(null)

export function AdminEditingLocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(defaultLocale)
  const [editingLocales, setEditingLocales] = useState<Locale[]>(() => [...supportedLocales])
  const [siteSettingsLoaded, setSiteSettingsLoaded] = useState(false)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch('/api/admin/settings/translation')
        if (!res.ok) {
          setSiteSettingsLoaded(true)
          return
        }
        const data = (await res.json()) as {
          settings?: {
            supportedLocales?: string[]
            defaultLocale?: string
            multilingualEnabled?: boolean
          }
        }
        if (cancelled || !data.settings) {
          setSiteSettingsLoaded(true)
          return
        }
        const s = data.settings
        const sup = (s.supportedLocales || []).filter((x): x is Locale => isValidLocale(x))
        const dl = getLocaleOrDefault(s.defaultLocale)
        const multi = s.multilingualEnabled !== false
        const allowed: Locale[] = !multi ? [dl] : sup.length > 0 ? sup : [dl]

        setEditingLocales(allowed)
        setLocaleState((prev) => (allowed.includes(prev) ? prev : dl))
      } catch {
        /* keep defaults */
      } finally {
        if (!cancelled) setSiteSettingsLoaded(true)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l)
  }, [])

  const cycleLocale = useCallback(() => {
    if (editingLocales.length <= 1) return
    const i = editingLocales.indexOf(locale)
    const next = editingLocales[(i + 1) % editingLocales.length]
    setLocaleState(next)
  }, [locale, editingLocales])

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      cycleLocale,
      editingLocales,
      siteSettingsLoaded,
    }),
    [locale, setLocale, cycleLocale, editingLocales, siteSettingsLoaded],
  )

  return (
    <AdminEditingLocaleContext.Provider value={value}>
      {children}
    </AdminEditingLocaleContext.Provider>
  )
}

export function useAdminEditingLocale(): Ctx {
  const ctx = useContext(AdminEditingLocaleContext)
  if (!ctx) {
    return {
      locale: defaultLocale,
      setLocale: () => {},
      cycleLocale: () => {},
      editingLocales: [...supportedLocales],
      siteSettingsLoaded: false,
    }
  }
  return ctx
}
