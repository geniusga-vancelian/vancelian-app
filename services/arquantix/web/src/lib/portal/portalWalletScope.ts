'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import type { PortalWalletScopeId } from '@/lib/portal/portalWalletScopeTypes'

const COOKIE_NAME = 'arquantix-portal-wallet-scope'
const COOKIE_MAX_AGE = 365 * 24 * 60 * 60

function getCookieWalletScopeId(): PortalWalletScopeId | null {
  if (typeof document === 'undefined') return null

  const cookies = document.cookie.split(';').reduce(
    (acc, cookie) => {
      const [key, value] = cookie.trim().split('=')
      acc[key] = value
      return acc
    },
    {} as Record<string, string>,
  )

  const raw = cookies[COOKIE_NAME]?.trim()
  return raw || null
}

function setCookieWalletScopeId(scopeId: PortalWalletScopeId | null): void {
  if (typeof document === 'undefined') return
  if (!scopeId) {
    document.cookie = `${COOKIE_NAME}=; path=/; max-age=0; SameSite=Lax`
    return
  }
  document.cookie = `${COOKIE_NAME}=${encodeURIComponent(scopeId)}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`
}

export function getCurrentPortalWalletScopeId(): PortalWalletScopeId | null {
  return getCookieWalletScopeId()
}

export function setCurrentPortalWalletScopeId(scopeId: PortalWalletScopeId | null): void {
  setCookieWalletScopeId(scopeId)
  if (typeof window !== 'undefined') {
    window.dispatchEvent(
      new CustomEvent('arq:portal-wallet-scope-changed', { detail: { scopeId } }),
    )
  }
}

export function usePortalWalletScopeId(): [
  PortalWalletScopeId | null,
  (scopeId: PortalWalletScopeId | null) => void,
] {
  const [scopeId, setScopeIdState] = useState<PortalWalletScopeId | null>(null)
  const [isMounted, setIsMounted] = useState(false)

  const scopeIdRef = useRef<PortalWalletScopeId | null>(null)

  useEffect(() => {
    setIsMounted(true)
    const initial = getCurrentPortalWalletScopeId()
    scopeIdRef.current = initial
    setScopeIdState(initial)

    const handleChange = (event: Event) => {
      const detail = (event as CustomEvent<{ scopeId?: PortalWalletScopeId | null }>).detail
      const next = detail?.scopeId ?? null
      scopeIdRef.current = next
      setScopeIdState(next)
    }

    window.addEventListener('arq:portal-wallet-scope-changed', handleChange)
    return () => {
      window.removeEventListener('arq:portal-wallet-scope-changed', handleChange)
    }
  }, [])

  const setScopeId = useCallback((next: PortalWalletScopeId | null) => {
    if (scopeIdRef.current === next) return
    scopeIdRef.current = next
    setCurrentPortalWalletScopeId(next)
    setScopeIdState(next)
  }, [])

  return [isMounted ? scopeId : null, setScopeId]
}
