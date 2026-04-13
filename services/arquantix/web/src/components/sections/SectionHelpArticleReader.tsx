import { getHelpArticle } from '@/lib/help/get-help-data'
import { ArticleBlockType } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import ReactMarkdown from 'react-markdown'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { calculateReadingTime } from '@/lib/blog/readingTime'

interface SectionHelpArticleReaderProps {
  updatedLabel?: string
  byLabel?: string
  readingTimeLabel?: string
  relatedTitle?: string
  locale: string
  collectionSlug: string
  categorySlug: string
  articleSlug: string
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/(^-|-$)/g, '')
}

interface Heading {
  id: string
  text: string
  level: number
}

function renderBlock(
  block: any,
  headings: Heading[]
): { element: JSX.Element; heading?: Heading } {
  switch (block.type) {
    case ArticleBlockType.HEADING:
      const headingText = (block.data as any).text || ''
      const headingId = slugify(headingText)
      const heading: Heading = {
        id: headingId,
        text: headingText,
        level: 2,
      }
      headings.push(heading)

      return {
        element: (
          <h2
            id={headingId}
            className="text-3xl font-bold text-gray-900 mt-12 mb-6 leading-tight"
          >
            {headingText}
          </h2>
        ),
        heading,
      }
    case ArticleBlockType.PARAGRAPH:
      return {
        element: (
          <div className="text-lg leading-[1.75] text-gray-800 my-6">
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-4">{children}</p>,
                strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                em: ({ children }) => <em className="italic">{children}</em>,
                a: ({ href, children }) => (
                  <a
                    href={href}
                    className="text-indigo-600 hover:text-indigo-800 underline"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {(block.data as any).text || ''}
            </ReactMarkdown>
          </div>
        ),
      }
    case ArticleBlockType.QUOTE:
      return {
        element: (
          <blockquote className="border-l-4 border-indigo-600 pl-6 py-4 my-10 italic text-gray-700 text-lg leading-relaxed">
            <p>{(block.data as any).text}</p>
            {(block.data as any).author && (
              <footer className="mt-3 text-base text-gray-500 not-italic font-normal">
                — {(block.data as any).author}
              </footer>
            )}
          </blockquote>
        ),
      }
    case ArticleBlockType.BULLET_LIST:
      return {
        element: (
          <ul className="list-disc list-inside space-y-2 my-6 text-lg text-gray-800">
            {((block.data as any).items || []).map((item: string, idx: number) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        ),
      }
    case ArticleBlockType.NUMBERED_LIST:
      return {
        element: (
          <ol className="list-decimal list-inside space-y-2 my-6 text-lg text-gray-800">
            {((block.data as any).items || []).map((item: string, idx: number) => (
              <li key={idx}>{item}</li>
            ))}
          </ol>
        ),
      }
    case ArticleBlockType.IMAGE:
      return {
        element: (
          <div className="my-10">
            <img
              src={(block.data as any).url || ''}
              alt={(block.data as any).alt || ''}
              className="w-full rounded-lg"
            />
            {(block.data as any).caption && (
              <p className="text-sm text-gray-500 mt-2 text-center">
                {(block.data as any).caption}
              </p>
            )}
          </div>
        ),
      }
    case ArticleBlockType.VIDEO:
      return {
        element: (
          <div className="my-10">
            <video
              src={(block.data as any).url || ''}
              controls
              className="w-full rounded-lg"
            />
            {(block.data as any).caption && (
              <p className="text-sm text-gray-500 mt-2 text-center">
                {(block.data as any).caption}
              </p>
            )}
          </div>
        ),
      }
    case ArticleBlockType.DOCUMENT:
      return {
        element: (
          <div className="my-6">
            <a
              href={(block.data as any).url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-indigo-600 hover:text-indigo-800 underline"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
              </svg>
              {(block.data as any).filename || 'Document'}
            </a>
          </div>
        ),
      }
    default:
      return {
        element: <div className="my-6 text-gray-500">Unknown block type</div>,
      }
  }
}

export async function SectionHelpArticleReader({
  updatedLabel = 'Mis à jour',
  byLabel = 'Par',
  readingTimeLabel = 'min de lecture',
  locale,
  collectionSlug,
  categorySlug,
  articleSlug,
}: SectionHelpArticleReaderProps) {
  const article = await getHelpArticle(collectionSlug, categorySlug, articleSlug, locale)

  if (!article) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <p className="text-gray-500">Article introuvable</p>
      </div>
    )
  }

  const headings: Heading[] = []
  const readingTime = calculateReadingTime(article.blocks)

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <article>
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
          {article.title}
        </h1>

        {article.standfirst && (
          <p className="text-xl text-gray-600 mb-8 leading-relaxed">
            {article.standfirst}
          </p>
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
          {article.blocks.map((block) => {
            const { element } = renderBlock(block, headings)
            return <div key={block.id}>{element}</div>
          })}
        </div>
      </article>
    </div>
  )
}

