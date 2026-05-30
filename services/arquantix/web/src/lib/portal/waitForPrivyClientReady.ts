/** Attend que le SDK Privy côté client soit prêt (session restaurée). */
export async function waitForPrivyClientReady(
  isReady: () => boolean,
  options?: { timeoutMs?: number; intervalMs?: number },
): Promise<void> {
  const timeoutMs = options?.timeoutMs ?? 15_000
  const intervalMs = options?.intervalMs ?? 100
  const started = Date.now()

  while (Date.now() - started < timeoutMs) {
    if (isReady()) return
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }

  if (!isReady()) {
    throw new Error('Privy is still initializing. Please wait a moment and try again.')
  }
}
