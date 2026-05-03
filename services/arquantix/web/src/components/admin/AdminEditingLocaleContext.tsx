'use client'

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Locale } from '@/config/locales'
import { defaultLocale, supportedLocales } from '@/config/locales'

type Ctx = {
  locale: Locale
  setLocale: (l: Locale) => void
  cycleLocale: () => void
}

const AdminEditingLocaleContext = createContext<Ctx | null>(null)

export function AdminEditingLocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(defaultLocale)

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l)
  }, [])

  const cycleLocale = useCallback(() => {
    const i = supportedLocales.indexOf(locale)
    const next = supportedLocales[(i + 1) % supportedLocales.length]
    setLocaleState(next)
  }, [locale])

  const value = useMemo(
    () => ({ locale, setLocale, cycleLocale }),
    [locale, setLocale, cycleLocale],
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
    }
  }
  return ctx
}
