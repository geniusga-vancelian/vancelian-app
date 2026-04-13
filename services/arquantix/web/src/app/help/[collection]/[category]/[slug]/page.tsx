import { getHelpArticle } from '@/lib/help/get-help-data'
import { notFound } from 'next/navigation'
import { Metadata } from 'next'
import { ArticleBlockType } from '@prisma/client'
import { TableOfContents } from '@/components/blog/TableOfContents'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import ReactMarkdown from 'react-markdown'
import Link from 'next/link'
import { formatArticleDateShort } from '@/lib/blog/formatDates'

interface PageProps {
  params: {
    collection: string
    category: string
    slug: string
  }
}

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
          <ul className="list-disc list-outside space-y-3 my-8 text-lg leading-relaxed text-gray-800 pl-6">
            {((block.data as any).items || []).map((item: string, i: number) => (
              <li key={i} className="pl-2">
                {item}
              </li>
            ))}
          </ul>
        ),
      }
    case ArticleBlockType.IMAGE:
      return {
        element: (
          <figure className="my-10">
            {(block.data as any).mediaId ? (
              <img
                src={(block.data as any).url || ''}
                alt={(block.data as any).caption || ''}
                className="w-full h-auto rounded-lg"
              />
            ) : (
              <div className="w-full h-64 bg-gray-200 rounded-lg flex items-center justify-center text-gray-400">
                Image not found
              </div>
            )}
            {(block.data as any).caption && (
              <figcaption className="text-sm text-gray-400 mt-3 text-center italic">
                {(block.data as any).caption}
              </figcaption>
            )}
          </figure>
        ),
      }
    case ArticleBlockType.VIDEO:
      const videoUrl = (block.data as any).url || ''
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
            {(block.data as any).caption && (
              <figcaption className="text-sm text-gray-500 mt-3 text-center italic">
                {(block.data as any).caption}
              </figcaption>
            )}
          </figure>
        ),
      }
    case ArticleBlockType.DOCUMENT:
      const docData = block.data as any
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
    default:
      return {
        element: <div className="my-6 text-gray-500">Unknown block type</div>,
      }
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const article = await getHelpArticle(params.collection, params.category, params.slug)

  if (!article) {
    return {
      title: 'Article non trouvé - Arquantix',
    }
  }

  return {
    title: article.metaTitle || article.title,
    description: article.metaDescription || article.standfirst || undefined,
  }
}

export default async function HelpArticlePage({ params }: PageProps) {
  const article = await getHelpArticle(params.collection, params.category, params.slug)

  if (!article) {
    notFound()
  }

  // Extract headings from blocks
  const headings: Heading[] = []
  const blocksWithUrls = await Promise.all(
    article.blocks.map(async (block) => {
      const rawData = block.data as any
      let blockData = (rawData && typeof rawData === 'object') ? { ...rawData } : {}

      // Get presigned URLs for images and documents
      if (block.type === ArticleBlockType.IMAGE && blockData.mediaId) {
        try {
          const url = await getPresignedUrl(blockData.mediaId)
          blockData.url = url
        } catch (error) {
          console.error('Error getting presigned URL for image:', error)
        }
      } else if (block.type === ArticleBlockType.DOCUMENT && blockData.mediaId) {
        try {
          const url = await getPresignedUrl(blockData.mediaId)
          blockData.url = url
        } catch (error) {
          console.error('Error getting presigned URL for document:', error)
        }
      }

      return { ...block, data: blockData }
    })
  )

  const renderedBlocks = blocksWithUrls.map((block) => {
    const result = renderBlock(block, headings)
    return { blockId: block.id, element: result.element }
  })

  return (
    <div className="min-h-screen bg-white">
      <article className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500 mb-8">
          <Link href="/help" className="hover:text-gray-700">
            Toutes les collections
          </Link>
          <span className="mx-2">/</span>
          <Link
            href={`/help/${params.collection}`}
            className="hover:text-gray-700"
          >
            {article.collection.title}
          </Link>
          <span className="mx-2">/</span>
          <Link
            href={`/help/${params.collection}/${params.category}`}
            className="hover:text-gray-700"
          >
            {article.category.title}
          </Link>
          <span className="mx-2">/</span>
          <span className="text-gray-900">{article.title}</span>
        </nav>

        {/* Header */}
        <header className="max-w-4xl mb-12">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6 leading-tight">
            {article.title}
          </h1>
          {article.standfirst && (
            <p className="text-xl text-gray-600 mb-6 italic leading-relaxed">
              {article.standfirst}
            </p>
          )}
          <div className="text-sm text-gray-500 space-y-1">
            {article.publishedAt && (
              <div>
                Publié le {formatArticleDateShort(article.publishedAt)}
              </div>
            )}
            {article.updatedAt && article.publishedAt && article.updatedAt > article.publishedAt && (
              <div>
                Mis à jour le {formatArticleDateShort(article.updatedAt)}
              </div>
            )}
          </div>
        </header>

        {/* Content with TOC */}
        <div className="flex flex-col lg:flex-row gap-12">
          {/* Main content */}
          <div className="flex-1 max-w-4xl">
            <div className="prose prose-lg max-w-none">
              {renderedBlocks.map(({ blockId, element }) => (
                <div key={blockId}>{element}</div>
              ))}
            </div>
          </div>

          {/* TOC sidebar */}
          {article.allowAnchors && headings.length >= 3 && (
            <TableOfContents headings={headings} />
          )}
        </div>
      </article>
    </div>
  )
}

