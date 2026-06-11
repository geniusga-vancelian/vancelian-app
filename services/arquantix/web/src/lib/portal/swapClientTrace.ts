/** Traces client swap — append-only audit (best-effort, debug Privy embed). */

export async function recordSwapClientTrace(
  swapId: string,
  body: {
    step: string
    phase?: string
    detail?: string
    correlation_id?: string
  },
): Promise<void> {
  try {
    await fetch(`/api/portal/swaps/${swapId}/client-trace`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(8_000),
    })
  } catch {
    // best-effort — ne bloque jamais l'exécution
  }
}
