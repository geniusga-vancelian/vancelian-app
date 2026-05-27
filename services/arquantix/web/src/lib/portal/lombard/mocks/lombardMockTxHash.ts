/** Browser- and Node-safe mock tx hash (no node:crypto — safe for client bundles). */
export function generateLombardMockTxHash(): string {
  const bytes = new Uint8Array(32)
  crypto.getRandomValues(bytes)
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  return `0x${hex}`
}
