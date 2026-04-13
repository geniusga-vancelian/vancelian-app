'use client'

import { useState, useEffect } from 'react'
import { supportedLocales, defaultLocale, type Locale } from '@/config/locales'

const COOKIE_NAME = 'arquantix-locale'
const COOKIE_MAX_AGE = 365 * 24 * 60 * 60 // 1 year

/**
 * Get browser locale (client-side)
 */
function getBrowserLocale(): Locale {
  if (typeof window === 'undefined') return defaultLocale
  
  const browserLang = navigator.language.split('-')[0].toLowerCase()
  if (supportedLocales.includes(browserLang as Locale)) {
    return browserLang as Locale
  }
  return defaultLocale
}

/**
 * Get current locale from cookie (client-side)
 */
function getCookieLocale(): Locale | null {
  if (typeof document === 'undefined') return null
  
  const cookies = document.cookie.split(';').reduce((acc, cookie) => {
    const [key, value] = cookie.trim().split('=')
    acc[key] = value
    return acc
  }, {} as Record<string, string>)
  
  const cookieLocale = cookies[COOKIE_NAME]
  if (cookieLocale && supportedLocales.includes(cookieLocale as Locale)) {
    return cookieLocale as Locale
  }
  return null
}

/**
 * Set locale in cookie (client-side)
 */
function setCookieLocale(locale: Locale): void {
  if (typeof document === 'undefined') return
  
  document.cookie = `${COOKIE_NAME}=${locale}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`
}

/**
 * Get current locale with fallback order:
 * 1) cookie
 * 2) browser language
 * 3) default locale
 */
export function getCurrentLocale(): Locale {
  const cookieLocale = getCookieLocale()
  if (cookieLocale) return cookieLocale
  
  const browserLocale = getBrowserLocale()
  return browserLocale
}

/**
 * Set current locale and persist to cookie
 */
export function setCurrentLocale(locale: Locale): void {
  if (!supportedLocales.includes(locale)) {
    console.warn(`Locale ${locale} is not supported`)
    return
  }
  
  setCookieLocale(locale)
  
  // Trigger custom event for components to react
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('localechange', { detail: { locale } }))
  }
}

/**
 * React hook to use current locale
 * Uses defaultLocale initially to avoid hydration mismatch, then reads cookie on mount
 */
export function useLocale(): [Locale, (locale: Locale) => void] {
  // Start with defaultLocale to match server-side rendering
  const [locale, setLocaleState] = useState<Locale>(defaultLocale)
  const [isMounted, setIsMounted] = useState(false)
  
  useEffect(() => {
    // Mark as mounted (client-side only)
    setIsMounted(true)
    
    // Initialize from cookie (client-side only)
    const current = getCurrentLocale()
    setLocaleState(current)
    
    // Listen for locale changes
    const handleLocaleChange = (e: CustomEvent) => {
      setLocaleState(e.detail.locale)
    }
    
    window.addEventListener('localechange', handleLocaleChange as EventListener)
    
    return () => {
      window.removeEventListener('localechange', handleLocaleChange as EventListener)
    }
  }, [])
  
  const setLocale = (newLocale: Locale) => {
    setCurrentLocale(newLocale)
    setLocaleState(newLocale)
  }
  
  // Return defaultLocale during SSR, actual locale after mount
  return [isMounted ? locale : defaultLocale, setLocale]
}

