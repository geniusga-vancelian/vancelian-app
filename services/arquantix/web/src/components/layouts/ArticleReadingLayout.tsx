import type { ReactNode } from 'react'
import { ReadingProgress } from '@/components/blog/ReadingProgress'
import { cn } from '@/lib/utils'

/**
 * Gabarit lecture (blog, offre exclusive) : progression + contenu sous le header fixe du layout.
 * La barre de navigation est fournie une seule fois par {@link SiteChrome}.
 */
export function ArticleReadingLayout({
  showReadingProgress = true,
  /** Premier module = bandeau blog sous nav (`blog_article_hero`) : le module gère le décalage — pas de `pt-20` ici. */
  suppressHeaderOffset = false,
  children,
}: {
  showReadingProgress?: boolean
  suppressHeaderOffset?: boolean
  children: ReactNode
}) {
  return (
    <>
      {showReadingProgress ? <ReadingProgress /> : null}
      <article
        className={cn(
          'min-h-screen bg-white',
          !suppressHeaderOffset && 'pt-20 md:pt-24',
        )}
      >
        {children}
      </article>
    </>
  )
}
