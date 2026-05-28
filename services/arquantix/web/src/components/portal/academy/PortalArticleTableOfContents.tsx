'use client'

import { useEffect, useState } from 'react'

import type { ArticleHeading } from '@/components/blog/ArticleBlockStream'

type Props = {
  headings: ArticleHeading[]
}

/** Sommaire sticky scroll-spy — handoff `.art-toc`. */
export function PortalArticleTableOfContents({ headings }: Props) {
  const [active, setActive] = useState(headings[0]?.id ?? null)

  useEffect(() => {
    if (typeof window === 'undefined' || headings.length === 0) return

    const onScroll = () => {
      const probe = window.innerHeight * 0.28
      let bestId = headings[0]?.id ?? null
      let bestDist = Infinity

      for (const heading of headings) {
        const el = document.getElementById(heading.id)
        if (!el) continue
        const dist = Math.abs(el.getBoundingClientRect().top - probe)
        if (dist < bestDist) {
          bestDist = dist
          bestId = heading.id
        }
      }

      setActive(bestId)
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener('scroll', onScroll)
  }, [headings])

  if (headings.length === 0) return null

  return (
    <nav className="art-toc" aria-label="Sommaire de l'article">
      <div className="art-toc__eyebrow">Sommaire</div>
      <ol className="art-toc__list">
        {headings.map((heading) => (
          <li
            key={heading.id}
            className={heading.id === active ? 'art-toc__item is-active' : 'art-toc__item'}
          >
            <a
              href={`#${heading.id}`}
              className="art-toc__link"
              onClick={(event) => {
                event.preventDefault()
                const el = document.getElementById(heading.id)
                if (!el) return
                const y = el.getBoundingClientRect().top + window.scrollY - 88
                window.scrollTo({ top: y, behavior: 'smooth' })
              }}
            >
              {heading.text}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  )
}
