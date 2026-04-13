'use client'

import { useEffect, useState } from 'react'
import { TableOfContents } from '@/components/blog/TableOfContents'

interface SectionHelpSidebarTocProps {
  tocTitle?: string
  locale: string
  articleId?: string
}

export function SectionHelpSidebarToc({
  tocTitle = 'Sur cette page',
  locale,
  articleId,
}: SectionHelpSidebarTocProps) {
  const [headings, setHeadings] = useState<Array<{ id: string; text: string; level: number }>>([])

  useEffect(() => {
    if (!articleId) return

    // Extract headings from the article content
    const articleElement = document.querySelector(`[data-article-id="${articleId}"]`)
    if (!articleElement) return

    const headingElements = articleElement.querySelectorAll('h2, h3, h4')
    const extractedHeadings: Array<{ id: string; text: string; level: number }> = []

    headingElements.forEach((heading) => {
      const id = heading.id || heading.textContent?.toLowerCase().replace(/\s+/g, '-') || ''
      const text = heading.textContent || ''
      const level = parseInt(heading.tagName.charAt(1))

      if (id && text) {
        extractedHeadings.push({ id, text, level })
      }
    })

    setHeadings(extractedHeadings)
  }, [articleId])

  if (headings.length < 3) {
    return null // Don't show TOC if less than 3 headings
  }

  return (
    <aside className="w-64 flex-shrink-0">
      <div className="sticky top-8">
        <h3 className="text-sm font-semibold text-gray-900 mb-4 uppercase tracking-wide">
          {tocTitle}
        </h3>
        <TableOfContents headings={headings} />
      </div>
    </aside>
  )
}









