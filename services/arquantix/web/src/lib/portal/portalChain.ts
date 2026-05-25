'use client'

import { useEffect, useState } from 'react'
import {
  DEFAULT_PORTAL_CHAIN,
  isValidPortalChain,
  type PortalChain,
} from '@/config/portalChains'

const COOKIE_NAME = 'arquantix-portal-chain'
const COOKIE_MAX_AGE = 365 * 24 * 60 * 60

function getCookieChain(): PortalChain | null {
  if (typeof document === 'undefined') return null

  const cookies = document.cookie.split(';').reduce(
    (acc, cookie) => {
      const [key, value] = cookie.trim().split('=')
      acc[key] = value
      return acc
    },
    {} as Record<string, string>,
  )

  const raw = cookies[COOKIE_NAME]
  if (raw && isValidPortalChain(raw)) return raw
  return null
}

function setCookieChain(chain: PortalChain): void {
  if (typeof document === 'undefined') return
  document.cookie = `${COOKIE_NAME}=${chain}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`
}

export function getCurrentPortalChain(): PortalChain {
  return getCookieChain() ?? DEFAULT_PORTAL_CHAIN
}

export function setCurrentPortalChain(chain: PortalChain): void {
  if (!isValidPortalChain(chain)) return
  setCookieChain(chain)
  if (typeof window !== 'undefined') {
    window.dispatchEvent(new CustomEvent('portalchainchange', { detail: { chain } }))
    window.dispatchEvent(
      new CustomEvent('arq:portal-chain-changed', { detail: { chain } }),
    )
  }
}

/** Hook client — même pattern que `useLocale`. */
export function usePortalChain(): [PortalChain, (chain: PortalChain) => void] {
  const [chain, setChainState] = useState<PortalChain>(DEFAULT_PORTAL_CHAIN)
  const [isMounted, setIsMounted] = useState(false)

  useEffect(() => {
    setIsMounted(true)
    setChainState(getCurrentPortalChain())

    const handleChange = (event: Event) => {
      const detail = (event as CustomEvent<{ chain?: PortalChain }>).detail
      if (detail?.chain && isValidPortalChain(detail.chain)) {
        setChainState(detail.chain)
      }
    }

    window.addEventListener('portalchainchange', handleChange)
    window.addEventListener('arq:portal-chain-changed', handleChange)
    return () => {
      window.removeEventListener('portalchainchange', handleChange)
      window.removeEventListener('arq:portal-chain-changed', handleChange)
    }
  }, [])

  const setChain = (next: PortalChain) => {
    setCurrentPortalChain(next)
    setChainState(next)
  }

  return [isMounted ? chain : DEFAULT_PORTAL_CHAIN, setChain]
}
