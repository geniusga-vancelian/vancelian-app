let lombardPositionsRevision = 0
const listeners = new Set<() => void>()

export function bumpLombardPositionsRevision(): void {
  lombardPositionsRevision += 1
  for (const listener of listeners) listener()
}

export function getLombardPositionsRevision(): number {
  return lombardPositionsRevision
}

export function subscribeLombardPositionsRevision(listener: () => void): () => void {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
