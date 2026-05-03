import { cn } from '@/lib/utils'
import { DoubleQuoteIcon } from '@/components/design-system/extracted'
import {
  figmaDsArticleQuoteAuthorClassName,
  figmaDsArticleQuoteContainerClassName,
  figmaDsArticleQuoteTextClassName,
} from '@/components/design-system/extracted/tokens/typography'

type Props = {
  quote: string
  author?: string | null
  className?: string
}

/**
 * Bloc citation aligné Figma (traits haut / bas, pas de fond, pas de bordure gauche, guillemet en dégradé).
 */
export function ArticleBodyQuoteBlock({ quote, author, className }: Props) {
  const authorTrim = author?.trim() ?? ''
  return (
    <figure className={cn(figmaDsArticleQuoteContainerClassName, 'my-12 w-full', className)}>
      <div className="flex gap-4">
        <span className="shrink-0 pt-1" aria-hidden>
          <DoubleQuoteIcon />
        </span>
        <div className="min-w-0 flex-1">
          <blockquote className="m-0">
            <p className={figmaDsArticleQuoteTextClassName}>{quote}</p>
            {authorTrim ? (
              <footer className={cn('mt-4 block', figmaDsArticleQuoteAuthorClassName)}>{authorTrim}</footer>
            ) : null}
          </blockquote>
        </div>
      </div>
    </figure>
  )
}
