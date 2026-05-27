'use client'

import { useCallback, useEffect, useState } from 'react'

import { fetchPortalLombardPositions } from '@/lib/portal/lombard/lombardClient'
import type { LombardPositionsPayload } from '@/lib/portal/lombard/lombardPositionTypes'
import {
  getLombardPositionsRevision,
  subscribeLombardPositionsRevision,
} from '@/lib/portal/lombard/lombardPositionsRefresh'
import { useLombardV1PortalEnabled } from '@/lib/portal/lombard/useLombardV1PortalEnabled'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'

const DEFAULT_POLL_MS = 45_000

export function usePortalLombardPositions(options?: { pollMs?: number; enabled?: boolean }) {
  const pollMs = options?.pollMs ?? DEFAULT_POLL_MS
  const { executionAddress, deFiEnabled } = usePortalExecutionScope()
  const { enabled: lombardEnabled, loading: featureLoading } = useLombardV1PortalEnabled()
  const [revision, setRevision] = useState(getLombardPositionsRevision())
  const [data, setData] = useState<LombardPositionsPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const active =
    (options?.enabled ?? true) && lombardEnabled && deFiEnabled && Boolean(executionAddress)

  useEffect(() => subscribeLombardPositionsRevision(() => setRevision(getLombardPositionsRevision())), [])

  const refresh = useCallback(async () => {
    if (!active || !executionAddress) {
      setData(null)
      setLoading(false)
      return
    }

    setError(null)
    try {
      const payload = await fetchPortalLombardPositions({ walletAddress: executionAddress })
      setData(payload)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to load loan positions.')
    } finally {
      setLoading(false)
    }
  }, [active, executionAddress])

  useEffect(() => {
    if (featureLoading) return
    setLoading(true)
    void refresh()
  }, [featureLoading, refresh, revision])

  useEffect(() => {
    if (!active || featureLoading) return undefined
    const timer = window.setInterval(() => {
      void refresh()
    }, pollMs)
    return () => window.clearInterval(timer)
  }, [active, featureLoading, pollMs, refresh])

  return {
    data,
    positions: data?.positions ?? [],
    hasActiveLoan: Boolean(data?.hasActiveLoan),
    loading: loading || featureLoading,
    error,
    refresh,
    enabled: active,
  }
}
