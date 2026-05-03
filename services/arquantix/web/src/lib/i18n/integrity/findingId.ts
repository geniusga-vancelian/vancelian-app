import { createHash } from 'node:crypto'

export function stableFindingId(parts: string[]): string {
  const h = createHash('sha256')
  h.update(parts.join('|'))
  return h.digest('hex').slice(0, 16)
}
