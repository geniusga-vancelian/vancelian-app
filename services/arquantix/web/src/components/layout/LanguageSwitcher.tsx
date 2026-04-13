'use client'

import { useState, useRef, useEffect } from 'react'
import { useLocale } from '@/lib/i18n/locale'
import { supportedLocales, type Locale } from '@/config/locales'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'

interface LanguageSwitcherProps {
  themeColor?: 'dark' | 'light';
}

export function LanguageSwitcher({ themeColor = 'dark' }: LanguageSwitcherProps) {
  const [locale, setLocale] = useLocale()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  
  const isLight = themeColor === 'light'
  const textColor = isLight ? 'text-black' : 'text-white'

  // Close dropdown when clicking outside
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

    setLocale(newLocale)
    setIsOpen(false)
    
    // Soft refresh to update content
    router.refresh()
  }

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "flex items-center gap-1.5 text-[10px] uppercase tracking-wider transition-opacity hover:opacity-80",
          textColor
        )}
        aria-label="Change language"
        aria-expanded={isOpen}
      >
        <span>{locale.toUpperCase()}</span>
        <svg
          className={cn(
            "w-3 h-3 transition-transform",
            isOpen && "rotate-180"
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 bg-black/90 backdrop-blur-sm rounded-md shadow-lg border border-white/10 min-w-[80px] z-50">
          <div className="py-1">
            {supportedLocales.map((loc) => (
              <button
                key={loc}
                onClick={() => handleLocaleChange(loc)}
                className={cn(
                  "w-full text-left px-4 py-2 text-[10px] uppercase tracking-wider transition-colors",
                  loc === locale
                    ? "bg-[#C6A47C]/20 text-[#C6A47C]"
                    : "text-white hover:bg-white/10"
                )}
              >
                {loc.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

