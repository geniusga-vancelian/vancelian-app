'use client'

import { useEffect, useState } from 'react'

import { fetchPortalLombardMarkets } from '@/lib/portal/lombard/lombardClient'

/** Reads Lombard availability from BFF (respects LOMBARD_V1_ENABLED server-side). */
export function useLombardV1PortalEnabled(): {
  enabled: boolean
  loading: boolean
} {
  const [enabled, setEnabled] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const payload = await fetchPortalLombardMarkets()
        if (!cancelled) setEnabled(Boolean(payload.enabled))
      } catch {
        if (!cancelled) setEnabled(false)
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  return { enabled, loading }
}
