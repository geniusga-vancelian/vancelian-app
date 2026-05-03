import { getHelpArticle } from '@/lib/help/get-help-data'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'
import { buildArticleBlockElements } from '@/components/blog/ArticleBlockStream'

interface SectionHelpArticleReaderProps {
  updatedLabel?: string
  byLabel?: string
  readingTimeLabel?: string
  relatedTitle?: string
  locale: string
  collectionSlug: string
  /** Conservé pour compatibilité CMS ; la résolution article ignore ce champ. */
  categorySlug?: string
  articleSlug: string
}

/**
 * Rendu d'un article du Centre d'aide. Délègue le rendu des blocs au
 * pipeline universel `<ArticleBlockStream>` / `buildArticleBlockElements`
 * — exactement le même que pour le blog public — afin de prendre en charge
 * tous les types `ArticleBlockType` (HEADING, PARAGRAPH, MEDIA_*,
 * STEPS_MODULE, HOW_IT_WORKS_CAROUSEL, etc.) sans réimplémenter un
 * `renderBlock` partiel.
 *
 * Côté Help, l'i18n des blocs est portée par la colonne `locale` de
 * `HelpArticleBlock` (filtrage déjà fait dans `getHelpArticle`), donc le
 * `mergeArticleBlockLocalizedData` côté blog retombe simplement sur
 * `block.data`.
 */
export async function SectionHelpArticleReader({
  updatedLabel = 'Mis à jour',
  byLabel = 'Par',
  readingTimeLabel = 'min de lecture',
  locale,
  collectionSlug,
  categorySlug: _legacyCategorySlug,
  articleSlug,
}: SectionHelpArticleReaderProps) {
  const article = await getHelpArticle(collectionSlug, articleSlug, locale)

  if (!article) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <p className="text-gray-500">{siteCommonCta(locale, 'article_not_found')}</p>
      </div>
    )
  }

  const readingTime = calculateReadingTime(article.blocks)
  const { elements } = buildArticleBlockElements(article.blocks)

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <article>
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
          {article.title}
        </h1>

        {article.standfirst && (
          <p className="text-xl text-gray-600 mb-8 leading-relaxed">{article.standfirst}</p>
        )}

        <div className="flex items-center gap-4 text-sm text-gray-500 mb-8 pb-8 border-b border-gray-200">
          {article.updatedAt && (
            <span>
              {updatedLabel} {formatArticleDateShort(article.updatedAt, locale)}
            </span>
          )}
          {article.authorName && (
            <span>
              {byLabel} {article.authorName}
            </span>
          )}
          <span>
            {readingTime} {readingTimeLabel}
          </span>
        </div>

        <div className="prose prose-lg max-w-none">
          {elements.map(({ blockId, element }) => (
            <div key={blockId}>{element}</div>
          ))}
        </div>
      </article>
    </div>
  )
}
