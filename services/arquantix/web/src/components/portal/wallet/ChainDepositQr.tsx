'use client'

import { useMemo } from 'react'

function chainQrMatrix(seed: string, size = 25): number[][] {
  const matrix = Array.from({ length: size }, () => Array<number>(size).fill(0))
  let hash = 5381
  for (let i = 0; i < seed.length; i += 1) {
    hash = (hash << 5) + hash + seed.charCodeAt(i)
    hash |= 0
  }
  const rng = () => {
    hash = (hash * 1664525 + 1013904223) | 0
    return ((hash >>> 0) % 1000) / 1000
  }

  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      matrix[y]![x] = rng() > 0.52 ? 1 : 0
    }
  }

  const placeFinder = (oy: number, ox: number) => {
    for (let y = 0; y < 7; y += 1) {
      for (let x = 0; x < 7; x += 1) {
        const onBorder = y === 0 || y === 6 || x === 0 || x === 6
        const innerBox = y >= 2 && y <= 4 && x >= 2 && x <= 4
        matrix[oy + y]![ox + x] = onBorder || innerBox ? 1 : 0
      }
    }
    for (let y = -1; y <= 7; y += 1) {
      for (let x = -1; x <= 7; x += 1) {
        if (y === -1 || y === 7 || x === -1 || x === 7) {
          const yy = oy + y
          const xx = ox + x
          if (yy >= 0 && yy < size && xx >= 0 && xx < size) matrix[yy]![xx] = 0
        }
      }
    }
  }

  placeFinder(0, 0)
  placeFinder(0, size - 7)
  placeFinder(size - 7, 0)

  const ay = size - 6
  const ax = size - 6
  for (let y = 0; y < 5; y += 1) {
    for (let x = 0; x < 5; x += 1) {
      const onBorder = y === 0 || y === 4 || x === 0 || x === 4
      const innerDot = y === 2 && x === 2
      matrix[ay + y]![ax + x] = onBorder || innerDot ? 1 : 0
    }
  }

  return matrix
}

/** Decorative QR — handoff ChainQR (visual DS; use copy for exact address). */
export function ChainDepositQr({ value }: { value: string }) {
  const size = 25
  const matrix = useMemo(() => chainQrMatrix(value, size), [value])
  const cell = 100 / size

  return (
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
      <rect width="100" height="100" fill="#FFFFFF" />
      {matrix.map((row, y) =>
        row.map((filled, x) =>
          filled ? (
            <rect
              key={`${x}-${y}`}
              x={x * cell}
              y={y * cell}
              width={cell + 0.4}
              height={cell + 0.4}
              fill="#1A1815"
            />
          ) : null,
        ),
      )}
    </svg>
  )
}
