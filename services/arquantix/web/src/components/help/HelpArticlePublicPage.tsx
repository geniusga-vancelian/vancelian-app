import { getPresignedUrl } from '@/lib/storage/storageClient'
import ReactMarkdown from 'react-markdown'
import Link from 'next/link'
import { formatArticleDateShort } from '@/lib/blog/formatDates'
import { ArticleBlockType } from '@prisma/client'
import { ArticleBodyBulletListBlock } from '@/components/design-system/ArticleBodyBulletListBlock'
import { ArticleBodyQuoteBlock } from '@/components/design-system/ArticleBodyQuoteBlock'
import { ArticleStepsModule } from '@/components/design-system/ArticleStepsModule'
import { VaultMediaCarousel } from '@/components/exclusive-offer/VaultMediaCarousel'
import { figmaDsParagraphClassName } from '@/components/design-system/extracted'
import { cn } from '@/lib/utils'
import { TableOfContents } from '@/components/blog/TableOfContents'

interface Heading {
  id: string
  text: string
  level: number
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/(^-|-$)/g, '')
}

function renderBlock(
  block: { id: string; type: ArticleBlockType; data: unknown },
  headings: Heading[],
): { element: JSX.Element; heading?: Heading } {
  switch (block.type) {
    case ArticleBlockType.HEADING: {
      const headingText = ((block.data as { text?: string }) || {}).text || ''
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
    }
    case ArticleBlockType.PARAGRAPH:
      return {
        element: (
          <div
            className={cn(
              figmaDsParagraphClassName,
              'not-italic my-6 text-[#2a2d35]',
            )}
          >
            <ReactMarkdown
              components={{
                p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
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
              {((block.data as { text?: string }) || {}).text || ''}
            </ReactMarkdown>
          </div>
        ),
      }
    case ArticleBlockType.QUOTE:
      return {
        element: (
          <ArticleBodyQuoteBlock
            quote={String((block.data as { text?: string }).text ?? '')}
            author={(block.data as { author?: string }).author}
          />
        ),
      }
    case ArticleBlockType.BULLET_LIST:
      return {
        element: (
          <ArticleBodyBulletListBlock
            items={(block.data as { items?: string[] }).items || []}
          />
        ),
      }
    case ArticleBlockType.IMAGE: {
      const d = (block.data as Record<string, unknown>) || {}
      const url = typeof d.url === 'string' ? d.url : ''
      const mediaId = typeof d.mediaId === 'string' ? d.mediaId : ''
      const caption = typeof d.caption === 'string' ? d.caption.trim() : ''
      if (!url) {
        return {
          element: (
            <div className="my-10 flex h-64 w-full items-center justify-center rounded-lg bg-gray-200 text-gray-400">
              Image not found
            </div>
          ),
        }
      }
      return {
        element: (
          <div className="my-10 w-full min-w-0">
            <VaultMediaCarousel moduleTitle="" description="" items={[{ url, mediaId, alt: null }]} />
            {caption ? (
              <p className="mt-3 text-center text-[13px] text-[#8893b0]">{caption}</p>
            ) : null}
          </div>
        ),
      }
    }
    case ArticleBlockType.VIDEO: {
      const videoUrl = ((block.data as { url?: string }) || {}).url || ''
      const videoId = videoUrl.includes('youtube.com/watch?v=')
        ? videoUrl.split('v=')[1]?.split('&')[0]
        : videoUrl.includes('youtu.be/')
        ? videoUrl.split('youtu.be/')[1]?.split('?')[0]
        : videoUrl.includes('vimeo.com/')
        ? videoUrl.split('vimeo.com/')[1]?.split('?')[0]
        : null

      return {
        element: (
          <figure className="my-10">
            {videoId ? (
              <div className="aspect-video w-full rounded-lg overflow-hidden">
                {videoUrl.includes('vimeo.com') ? (
                  <iframe
                    src={`https://player.vimeo.com/video/${videoId}`}
                    className="w-full h-full"
                    allow="autoplay; fullscreen; picture-in-picture"
                    allowFullScreen
                  />
                ) : (
                  <iframe
                    src={`https://www.youtube.com/embed/${videoId}`}
                    className="w-full h-full"
                    allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                    allowFullScreen
                  />
                )}
              </div>
            ) : (
              <div className="w-full h-64 bg-gray-200 rounded-lg flex items-center justify-center text-gray-400">
                Invalid video URL
              </div>
            )}
            {(block.data as { caption?: string }).caption && (
              <figcaption className="text-sm text-gray-500 mt-3 text-center italic">
                {(block.data as { caption?: string }).caption}
              </figcaption>
            )}
          </figure>
        ),
      }
    }
    case ArticleBlockType.DOCUMENT: {
      const docData = block.data as { url?: string; title?: string }
      const docUrl = docData.url || ''
      const docTitle = docData.title || 'Document'

      return {
        element: (
          <div className="my-6">
            <a
              href={docUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="w-10 h-10 bg-gray-200 rounded flex items-center justify-center flex-shrink-0">
                <span className="text-xs font-semibold">PDF</span>
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">{docTitle}</p>
              </div>
              <svg
                className="w-5 h-5 text-gray-400 flex-shrink-0"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </a>
          </div>
        ),
      }
    }
    case ArticleBlockType.STEPS_MODULE:
      return {
        element: (
          <div className="my-10 w-full min-w-0">
            <ArticleStepsModule
              content={((block.data as Record<string, unknown>) || {}) as Record<string, unknown>}
            />
          </div>
        ),
      }
    default:
      return {
        element: <div className="my-6 text-gray-500">Unknown block type</div>,
      }
  }
}

import type { getHelpArticle } from '@/lib/help/get-help-data'

export type HelpArticleDetail = NonNullable<Awaited<ReturnType<typeof getHelpArticle>>>

interface Props {
  article: HelpArticleDetail
  collectionSlug: string
}

export async function HelpArticlePublicPage({ article, collectionSlug }: Props) {
  const headings: Heading[] = []
  const blocksWithUrls = await Promise.all(
    article.blocks.map(async (block) => {
      const rawData = block.data as Record<string, unknown>
      let blockData =
        rawData && typeof rawData === 'object' ? { ...rawData } : {}

      if (block.type === ArticleBlockType.IMAGE && blockData.mediaId) {
        try {
          const url = await getPresignedUrl(String(blockData.mediaId))
          blockData.url = url
        } catch (error) {
          console.error('Error getting presigned URL for image:', error)
        }
      } else if (block.type === ArticleBlockType.DOCUMENT && blockData.mediaId) {
        try {
          const url = await getPresignedUrl(String(blockData.mediaId))
          blockData.url = url
        } catch (error) {
          console.error('Error getting presigned URL for document:', error)
        }
      }

      return { ...block, data: blockData }
    }),
  )

  const renderedBlocks = blocksWithUrls.map((block) => {
    const result = renderBlock(block, headings)
    return { blockId: block.id, element: result.element }
  })

  return (
    <div className="min-h-screen bg-white">
      <article className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <nav className="text-sm text-gray-500 mb-8">
          <Link href="/help" className="hover:text-gray-700">
            Toutes les collections
          </Link>
          <span className="mx-2">/</span>
          <Link href={`/help/${collectionSlug}`} className="hover:text-gray-700">
            {article.collection.title}
          </Link>
          <span className="mx-2">/</span>
          <Link
            href={`/help/${collectionSlug}/${article.category.slug}`}
            className="hover:text-gray-700"
          >
            {article.category.title}
          </Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{article.title}</span>
        </nav>

        <header className="max-w-4xl mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
            {article.title}
          </h1>
          {article.standfirst && (
            <p className="text-xl text-gray-600 mb-6 italic leading-relaxed">{article.standfirst}</p>
          )}
          <div className="text-sm text-gray-500 space-y-1">
            {article.publishedAt && (
              <div>Publié le {formatArticleDateShort(article.publishedAt)}</div>
            )}
            {article.updatedAt &&
              article.publishedAt &&
              article.updatedAt > article.publishedAt && (
                <div>Mis à jour le {formatArticleDateShort(article.updatedAt)}</div>
              )}
          </div>
        </header>

        <div className="flex flex-col lg:flex-row gap-12">
          <div className="flex-1 max-w-4xl">
            <div className="prose prose-lg max-w-none">
              {renderedBlocks.map(({ blockId, element }) => (
                <div key={blockId}>{element}</div>
              ))}
            </div>
          </div>

          {article.allowAnchors && headings.length >= 3 && (
            <TableOfContents headings={headings} />
          )}
        </div>
      </article>
    </div>
  )
}
