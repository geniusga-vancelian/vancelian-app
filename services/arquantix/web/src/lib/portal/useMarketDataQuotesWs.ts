'use client'

import { useEffect, useRef } from 'react'
import { buildMarketDataWsUrl } from '@/lib/portal/marketDataPublic'
import type { MarketQuoteUpdate } from '@/lib/portal/marketsTypes'

export type { MarketQuoteUpdate } from '@/lib/portal/marketsTypes'

const MAX_RETRIES = 3
const RETRY_DELAY_MS = 2000

/**
 * WebSocket quotes market-data — équivalent Flutter `MarketDataWsService`.
 * Souscrit aux symboles de l’onglet actif ; met à jour les prix en temps réel.
 */
export function useMarketDataQuotesWs(
  symbols: string[],
  onQuotes: (updates: MarketQuoteUpdate[]) => void,
  enabled = true,
  /** Base FastAPI publique (logos + WS) — prioritaire sur l’env build-time. */
  marketDataBaseUrl?: string | null,
) {
  const onQuotesRef = useRef(onQuotes)
  onQuotesRef.current = onQuotes

  useEffect(() => {
    if (!enabled || symbols.length === 0) return

    let disposed = false
    let retryAttempt = 0
    let ws: WebSocket | null = null
    let retryTimer: ReturnType<typeof setTimeout> | null = null

    const parseUpdates = (raw: unknown): MarketQuoteUpdate[] => {
      if (!raw || typeof raw !== 'object') return []
      const quotes = (raw as { quotes?: unknown }).quotes
      if (!Array.isArray(quotes)) return []

      const updates: MarketQuoteUpdate[] = []
      for (const entry of quotes) {
        if (!entry || typeof entry !== 'object') continue
        const row = entry as Record<string, unknown>
        const symbol = String(row.symbol ?? '')
          .trim()
          .toUpperCase()
        if (!symbol) continue
        const priceRaw = row.price
        const price =
          typeof priceRaw === 'number'
            ? priceRaw
            : Number.parseFloat(String(priceRaw ?? '').replace(',', '.'))
        if (!Number.isFinite(price) || price <= 0) continue
        const priceEurRaw = row.price_eur ?? row.priceEur
        const priceEur =
          typeof priceEurRaw === 'number'
            ? priceEurRaw
            : Number.parseFloat(String(priceEurRaw ?? '').replace(',', '.'))
        updates.push({
          symbol,
          price,
          priceEur: Number.isFinite(priceEur) ? priceEur : null,
        })
      }
      return updates
    }

    const connect = () => {
      if (disposed) return
      ws?.close()
      ws = new WebSocket(buildMarketDataWsUrl(symbols, marketDataBaseUrl ?? undefined))

      ws.onopen = () => {
        retryAttempt = 0
      }

      ws.onmessage = (event) => {
        if (disposed) return
        try {
          const json = JSON.parse(String(event.data)) as unknown
          const updates = parseUpdates(json)
          if (updates.length > 0) onQuotesRef.current(updates)
        } catch {
          // ignore parse errors (Flutter parity)
        }
      }

      ws.onerror = () => {
        ws?.close()
      }

      ws.onclose = () => {
        ws = null
        if (disposed) return
        if (retryAttempt < MAX_RETRIES) {
          retryAttempt += 1
          retryTimer = setTimeout(connect, RETRY_DELAY_MS)
        }
      }
    }

    connect()

    return () => {
      disposed = true
      if (retryTimer) clearTimeout(retryTimer)
      ws?.close()
    }
  }, [enabled, marketDataBaseUrl, symbols.join(',')])
}
