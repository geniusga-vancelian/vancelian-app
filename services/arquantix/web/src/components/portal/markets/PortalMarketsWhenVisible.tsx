'use client'

import { useEffect, useRef, useState, type ReactNode } from 'react'

type Props = {
  children: ReactNode
  fallback?: ReactNode
  /** Marge avant intersection (px) — précharge légèrement below-the-fold. */
  rootMargin?: string
  className?: string
}

/** Monte les enfants à la première intersection (sections Markets below-the-fold). */
export function PortalMarketsWhenVisible({
  children,
  fallback = null,
  rootMargin = '240px 0px',
  className,
}: Props) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const node = ref.current
    if (!node || visible) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry?.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { rootMargin },
    )

    observer.observe(node)
    return () => observer.disconnect()
  }, [rootMargin, visible])

  return (
    <div ref={ref} className={className}>
      {visible ? children : fallback}
    </div>
  )
}
