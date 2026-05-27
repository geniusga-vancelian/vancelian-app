'use client'

import { useEffect, useState } from 'react'

import { isLombardDebugPanelClientHintVisible } from '@/lib/portal/lombard/lombardDebugAccess'
import type { LombardBetaCapSnapshot } from '@/lib/portal/lombard/lombardQaContext'

type LombardQaContextPayload = {
  debugVisible: boolean
  featureEnabled?: boolean
  betaLimitsEnabled?: boolean
  allowlistConfigured?: boolean
  maxUserLtvPercent?: number
  betaCaps?: LombardBetaCapSnapshot | null
}

export function usePortalLombardQaDebug(walletAddress: string | null | undefined) {
  const [visible, setVisible] = useState(isLombardDebugPanelClientHintVisible())
  const [betaCaps, setBetaCaps] = useState<LombardBetaCapSnapshot | null>(null)
  const [maxUserLtvPercent, setMaxUserLtvPercent] = useState<number | null>(null)

  useEffect(() => {
    if (!walletAddress) return

    let cancelled = false
    ;(async () => {
      try {
        const params = new URLSearchParams({ wallet_address: walletAddress })
        const res = await fetch(`/api/portal/lombard/qa-context?${params.toString()}`, {
          credentials: 'include',
          cache: 'no-store',
        })
        const data = (await res.json().catch(() => ({}))) as LombardQaContextPayload
        if (cancelled) return
        if (data.debugVisible) {
          setVisible(true)
          setBetaCaps(data.betaCaps ?? null)
          if (typeof data.maxUserLtvPercent === 'number') {
            setMaxUserLtvPercent(data.maxUserLtvPercent)
          }
        } else if (process.env.NODE_ENV === 'production') {
          setVisible(false)
        }
      } catch {
        /* keep client hint visibility in dev */
      }
    })()

    return () => {
      cancelled = true
    }
  }, [walletAddress])

  return { visible, betaCaps, maxUserLtvPercent }
}
