'use client'

import type { ArticleHeading } from '@/components/blog/ArticleBlockStream'
import { PortalArticleShareBlock } from '@/components/portal/academy/PortalArticleShareBlock'
import { PortalArticleTableOfContents } from '@/components/portal/academy/PortalArticleTableOfContents'

type Props = {
  title: string
  headings: ArticleHeading[]
}

/** Colonne latérale article — partage + sommaire sticky. */
export function PortalArticleSidebar({ title, headings }: Props) {
  const tocHeadings = headings.filter((heading) => heading.level === 2)

  return (
    <div className="art-side-stack">
      <PortalArticleShareBlock title={title} />
      <PortalArticleTableOfContents headings={tocHeadings} />
    </div>
  )
}
