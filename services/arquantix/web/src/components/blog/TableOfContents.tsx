'use client'

import { useEffect, useRef, useState } from 'react'
import {
  InThisArticleNav,
} from '@/components/design-system/extracted'

interface Heading {
  id: string
  text: string
  level: number
}

interface TableOfContentsProps {
  headings: Heading[]
  title?: string
  minCount?: number
  className?: string
  navClassName?: string
}

export function TableOfContents({
  headings,
  title = 'Sommaire',
  minCount = 3,
  className,
  navClassName,
}: TableOfContentsProps) {
  const [activeId, setActiveId] = useState<string>('')
  /** Après un clic, on fixe l’item actif et on ignore l’observer le temps du scroll (sinon 1ʳᵉ / dernière section ne « rentrent » pas dans la bande rootMargin). */
  const ignoreObserverUntilRef = useRef(0)

  useEffect(() => {
    if (headings.length === 0) return

    const observerOptions = {
      /* Bande un peu plus haute qu’avant pour mieux capter le haut de page et les sections courtes */
      rootMargin: '-12% 0px -52% 0px',
      threshold: 0,
    }

    const observerCallback = (entries: IntersectionObserverEntry[]) => {
      if (Date.now() < ignoreObserverUntilRef.current) {
        return
      }
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          setActiveId(entry.target.id)
        }
      })
    }

    const observer = new IntersectionObserver(observerCallback, observerOptions)

    headings.forEach((heading) => {
      const element = document.getElementById(heading.id)
      if (element) {
        observer.observe(element)
      }
    })

    return () => {
      headings.forEach((heading) => {
        const element = document.getElementById(heading.id)
        if (element) {
          observer.unobserve(element)
        }
      })
    }
  }, [headings])

  const handleClick = (id: string) => {
    const element = document.getElementById(id)
    if (!element) return

    setActiveId(id)
    const lockMs = 1200
    ignoreObserverUntilRef.current = Date.now() + lockMs

    const headerOffset = 100
    const rect = element.getBoundingClientRect()
    const y = rect.top + window.scrollY - headerOffset
    const maxY = Math.max(0, document.documentElement.scrollHeight - window.innerHeight)
    const top = Math.min(Math.max(0, y), maxY)

    window.scrollTo({
      top,
      behavior: 'smooth',
    })

    const releaseObserver = () => {
      ignoreObserverUntilRef.current = 0
    }
    if (typeof window !== 'undefined' && 'onscrollend' in window) {
      window.addEventListener('scrollend', releaseObserver, { once: true })
    }
    window.setTimeout(releaseObserver, lockMs)
  }

  if (headings.length < minCount) {
    return null
  }

  /** Tant que l’observer n’a pas posé d’`activeId`, on met en avant le 1ʳᵉ lien (comportement maquette). */
  const resolvedActiveId = activeId || headings[0]?.id || ''

  return (
    <InThisArticleNav
      title={title}
      items={headings.map((heading) => ({
        id: heading.id,
        label: heading.text,
        level: heading.level,
        isActive: heading.id === resolvedActiveId,
      }))}
      onItemClick={handleClick}
      className={navClassName ?? 'sticky top-28 ml-0 hidden w-full self-start lg:ml-0 lg:block'}
      panelClassName={className}
    />
  )
}









