'use client'

import { useState, useRef, useEffect } from 'react'
import { Check, ChevronDown, Globe } from 'lucide-react'
import { useLocale } from '@/lib/i18n/locale'
import { supportedLocales, isValidLocale, type Locale } from '@/config/locales'
import { useRouter, usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { getLocalizedPathForLocale } from '@/lib/i18n/localizedPath'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { NAV_PRIMARY_LINK_TYPO, NAV_RAIL_CIRCLE_TRIGGER_CLASS } from '@/components/design-system/nav-primary-link'

/** Noms complets affichés (comme réf. produit), pas les codes FR/EN/IT. */
const LOCALE_DISPLAY_NAME: Record<Locale, string> = {
  fr: 'Français',
  en: 'English',
  it: 'Italiano',
}

interface LanguageSwitcherProps {
  themeColor?: 'dark' | 'light'
  /**
   * `toolbar-icon` : pastille ronde globe (barre desktop / mobile compacte).
   * `drawer-row` : ligne globe + libellé + chevron (menu mobile plein écran, type SwissBorg).
   */
  variant?: 'toolbar-icon' | 'drawer-row'
}

export function LanguageSwitcher({
  themeColor: _themeColor = 'dark',
  variant = 'toolbar-icon',
}: LanguageSwitcherProps) {
  const [storedLocale, setStoredLocale] = useLocale()
  const pathname = usePathname() ?? '/'
  const urlLocaleMatch = pathname.match(/^\/(fr|en|it)(?:\/|$)/)
  const urlLocale =
    urlLocaleMatch?.[1] && isValidLocale(urlLocaleMatch[1])
      ? (urlLocaleMatch[1] as Locale)
      : null
  const locale = urlLocale ?? storedLocale
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const router = useRouter()

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleLocaleChange = (newLocale: Locale) => {
    if (newLocale === locale) {
      setIsOpen(false)
      return
    }

    setStoredLocale(newLocale)
    setIsOpen(false)
    if (typeof window !== 'undefined') {
      window.dispatchEvent(
        new CustomEvent('arq:locale-changed', {
          detail: { locale: newLocale },
        }),
      )
    }

    const next = getLocalizedPathForLocale(pathname, newLocale)
    if (next) {
      router.push(next)
      return
    }
    router.refresh()
  }

  /** Icône globe : proportionnée au disque (34px, comme les boutons du rail). */
  const globeClass = 'h-[19px] w-[19px] shrink-0 text-black'

  const listboxPanel = (
    <div
      className="overflow-hidden rounded-xl border border-black/10 bg-white py-1 shadow-lg"
      role="listbox"
      aria-label={siteCommonCta(locale, 'language_switcher_aria')}
    >
      {supportedLocales.map((loc) => (
        <button
          key={loc}
          type="button"
          role="option"
          aria-selected={loc === locale}
          onClick={() => handleLocaleChange(loc)}
          className={cn(
            "flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left font-['Avenir:Heavy',sans-serif] text-[15px] leading-none tracking-normal text-[#62656E] transition-colors hover:bg-black/[0.04] hover:text-black",
            loc === locale && 'text-black',
          )}
        >
          <span>{LOCALE_DISPLAY_NAME[loc]}</span>
          <span
            className="flex h-4 w-4 shrink-0 items-center justify-center text-[#0f766e]"
            aria-hidden
          >
            {loc === locale ? <Check className="h-4 w-4" strokeWidth={2.25} /> : null}
          </span>
        </button>
      ))}
    </div>
  )

  if (variant === 'drawer-row') {
    return (
      <div className="relative border-b border-black/[0.06]" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className={cn(
            NAV_PRIMARY_LINK_TYPO,
            'flex w-full items-center justify-between gap-2 px-4 py-3.5 text-left text-[#62656E] transition-colors hover:bg-[#F3F3F3] hover:text-black',
            isOpen && 'bg-[#F3F3F3] text-black',
          )}
          aria-label={siteCommonCta(locale, 'language_switcher_aria')}
          aria-expanded={isOpen}
          aria-haspopup="listbox"
        >
          <span className="flex min-w-0 flex-1 items-center gap-2.5">
            <Globe className="h-[18px] w-[18px] shrink-0" strokeWidth={1.75} aria-hidden />
            <span className="min-w-0">{LOCALE_DISPLAY_NAME[locale]}</span>
          </span>
          <ChevronDown
            className={cn('h-4 w-4 shrink-0 text-[#62656E] transition-transform duration-200', isOpen && 'rotate-180')}
            strokeWidth={2}
            aria-hidden
          />
        </button>
        {isOpen ? <div className="border-t border-black/[0.04] bg-[#FAFAFA] p-2">{listboxPanel}</div> : null}
      </div>
    )
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex shrink-0 items-center justify-center rounded-full bg-white shadow-sm ring-1 ring-black/5 transition hover:bg-white hover:opacity-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#0f766e]/40 focus-visible:ring-offset-2',
          NAV_RAIL_CIRCLE_TRIGGER_CLASS,
        )}
        aria-label={siteCommonCta(locale, 'language_switcher_aria')}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <Globe className={globeClass} strokeWidth={1.65} aria-hidden />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full z-50 mt-3 w-[min(100vw-2rem,220px)]">
          {/*
            Panneau listbox : overflow-hidden + rounded-xl pour que le fond au survol
            des lignes reste dans les coins arrondis (pas de « débord » rectangulaire).
          */}
          {listboxPanel}
        </div>
      )}
    </div>
  )
}
