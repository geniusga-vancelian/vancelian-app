/** Normalise les champs transaction LI.FI → Privy `sendTransaction`. */

export function parseSwapChainId(chainId: number | string): number {
  if (typeof chainId === 'number') return chainId
  const text = chainId.trim()
  if (text.startsWith('0x')) return parseInt(text, 16)
  const parsed = Number(text)
  if (!Number.isFinite(parsed)) {
    throw new Error(`chainId invalide: ${chainId}`)
  }
  return parsed
}

export function normalizeSwapTxValue(value: string): `0x${string}` {
  const raw = (value || '0').trim()
  if (raw.startsWith('0x')) return raw as `0x${string}`
  const wei = BigInt(raw)
  return `0x${wei.toString(16)}` as `0x${string}`
}

export function parseSwapGasLimit(gasLimit?: string | null): bigint | undefined {
  if (!gasLimit) return undefined
  const raw = gasLimit.trim()
  if (!raw) return undefined
  if (raw.startsWith('0x')) return BigInt(raw)
  return BigInt(raw)
}

export function normalizeTxHash(hash: string): string {
  const trimmed = hash.trim()
  return trimmed.startsWith('0x') ? trimmed : `0x${trimmed}`
}
