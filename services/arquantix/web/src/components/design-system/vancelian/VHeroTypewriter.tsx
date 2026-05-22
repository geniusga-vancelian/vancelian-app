'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'

export interface VHeroTypewriterProps {
  words: string[]
  className?: string
}

/** Mot animé typewriter pour la 3ᵉ ligne du hero homepage. */
export function VHeroTypewriter({ words, className }: VHeroTypewriterProps) {
  const list = React.useMemo(
    () => words.map((w) => w.trim()).filter(Boolean),
    // eslint-disable-next-line react-hooks/exhaustive-deps -- clé stable sur le contenu
    [words.join('\u0001')],
  )

  const longestWord = React.useMemo(
    () => list.reduce((max, w) => (w.length > max.length ? w : max), ''),
    [list],
  )

  const [text, setText] = React.useState(() => list[0] ?? '')
  const indexRef = React.useRef(0)

  React.useEffect(() => {
    if (list.length === 0) {
      setText('')
      return
    }
    if (list.length === 1) {
      setText(list[0])
      return
    }
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      setText(list[0])
      return
    }

    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | undefined

    const schedule = (fn: () => void, ms: number) => {
      timer = setTimeout(() => {
        if (!cancelled) fn()
      }, ms)
    }

    const typeWord = (word: string, done: () => void) => {
      let n = 0
      setText('')
      const tick = () => {
        if (cancelled) return
        n += 1
        setText(word.slice(0, n))
        if (n < word.length) schedule(tick, 70)
        else schedule(done, 1800)
      }
      tick()
    }

    const eraseWord = (word: string, done: () => void) => {
      let n = word.length
      const tick = () => {
        if (cancelled) return
        n -= 1
        setText(word.slice(0, Math.max(0, n)))
        if (n > 0) schedule(tick, 38)
        else schedule(done, 380)
      }
      tick()
    }

    const loop = () => {
      const word = list[indexRef.current % list.length]
      typeWord(word, () => {
        eraseWord(word, () => {
          indexRef.current += 1
          loop()
        })
      })
    }

    indexRef.current = 0
    schedule(loop, 1200)

    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [list])

  return (
    <span
      className={cn(
        'inline-grid align-top [grid-template-areas:"stack"]',
        className,
      )}
      aria-live="polite"
    >
      {/* Réserve la largeur du mot le plus long sans décaler le caret. */}
      <span
        aria-hidden
        className="invisible [grid-area:stack] font-display font-light italic tracking-normal whitespace-pre"
      >
        {longestWord || '\u00a0'}
      </span>
      <span className="[grid-area:stack] font-display font-light italic tracking-normal whitespace-pre">
        {text}
        <span className="hero-home-caret" aria-hidden />
      </span>
    </span>
  )
}
