import { prisma } from '@/lib/prisma'
import { ContentStatus, ArticleBlockType, type Prisma } from '@prisma/client'
import { getPresignedUrl } from '@/lib/storage/storageClient'
import { defaultLocale } from '@/config/locales'
import { getLocaleFromCookies } from '@/lib/i18n/locale-server'
import { notFound } from 'next/navigation'
import { Metadata } from 'next'
import { cookies } from 'next/headers'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'
import { ArticleReadingLayout } from '@/components/layouts/ArticleReadingLayout'
import { TableOfContents } from '@/components/blog/TableOfContents'
import { ArticleCarousel } from '@/components/blog/ArticleCarousel'
import { calculateReadingTime } from '@/lib/blog/readingTime'
import { effectiveIsCompanyNews, parseCategorySlugs } from '@/lib/blog/articleService'
import { resolveArticleCategoryLabels } from '@/lib/blog/articleCategoryLabels'
import { getDateLabels, formatArticleDate, formatArticleDateShort } from '@/lib/blog/formatDates'
import ReactMarkdown from 'react-markdown'

interface ArticleBlock {
  id: string
  type: ArticleBlockType
  order: number
  data: any
}

type ArticleProjectWithProject = Prisma.ArticleProjectGetPayload<{
  include: {
    project: {
      include: {
        i18n: true
      }
    }
  }
}>

async function getArticle(slug: string, locale?: string) {
  // If locale not provided, get from cookie
  if (!locale) {
    const cookieStore = await cookies()
    locale = await getLocaleFromCookies(cookieStore) || defaultLocale
  }
  const article = await prisma.article.findUnique({
    where: { slug },
    include: {
      coverMedia: true,
      i18n: {
        where: { locale },
      },
      blocks: {
        orderBy: { order: 'asc' },
        include: {
          i18n: {
            where: { locale },
            take: 1,
          },
        },
      },
    },
  })

  // Fetch projects separately if article exists
  let projects: ArticleProjectWithProject[] = []
  if (article) {
    const articleProjects = await prisma.articleProject.findMany({
      where: { articleId: article.id },
      include: {
        project: {
          include: {
            i18n: {
              where: { locale },
              take: 1,
            },
          },
        },
      },
      orderBy: { createdAt: 'asc' },
    })
    projects = articleProjects
  }

  // Fetch categories with localized labels if article exists
  let categories: Array<{ id: string; slug: string; label: string }> = []
  const categorySlugs: string[] = (() => {
    if (!article) return []
    const raw = (article as any).categorySlugs
    if (!raw) return []
    if (Array.isArray(raw)) return raw.filter(Boolean)
    if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw)
        return Array.isArray(parsed) ? parsed.filter(Boolean) : []
      } catch {
        return []
      }
    }
    return []
  })()

  if (article && categorySlugs.length > 0) {
    categories = await resolveArticleCategoryLabels(categorySlugs, locale!)
  }

  if (!article || article.status !== ContentStatus.PUBLISHED) {
    return null
  }

  const i18n = article.i18n[0]
  if (!i18n) {
    return null
  }

  let coverUrl: string | null = null
  if (article.coverMedia) {
    coverUrl = article.coverMedia.url
    if (article.coverMedia.key) {
      try {
        coverUrl = await getPresignedUrl(article.coverMedia.key, 3600)
      } catch {
        // Fallback to original URL
        coverUrl = article.coverMedia.url
      }
    }
  }

  // Get presigned URLs for gallery images
  const galleryMediaIds: string[] = (() => {
    const raw = (article as any).galleryMediaIds
    if (!raw) return []
    if (Array.isArray(raw)) return raw.filter((x): x is string => typeof x === 'string' && x.length > 0)
    if (typeof raw === 'string') {
      try {
        const parsed = JSON.parse(raw)
        return Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === 'string' && x.length > 0) : []
      } catch {
        return []
      }
    }
    return []
  })()
  const galleryUrls: string[] = []
  if (galleryMediaIds.length > 0) {
    for (const mediaId of galleryMediaIds) {
      if (!mediaId) continue
      try {
        const media = await prisma.media.findUnique({
          where: { id: mediaId },
        })
        if (media) {
          let url = media.url
          if (media.key) {
            try {
              url = await getPresignedUrl(media.key, 3600)
            } catch {
              // Fallback to original URL
            }
          }
          galleryUrls.push(url)
        }
      } catch (error) {
        console.error('Error fetching gallery media:', error)
        // Continue with next media
      }
    }
  }

  // Get presigned URLs for document attachments
  const documents = Array.isArray(article.documents) ? article.documents : []
  const documentsWithUrls = await Promise.all(
    documents.map(async (doc: any) => {
      if (!doc || !doc.mediaId) {
        return { ...doc, url: null }
      }
      try {
        const media = await prisma.media.findUnique({
          where: { id: doc.mediaId },
        })
        if (media) {
          let url = media.url
          if (media.key) {
            try {
              url = await getPresignedUrl(media.key, 3600)
            } catch {
              // Fallback to original URL
            }
          }
          return { ...doc, url }
        }
        return { ...doc, url: null }
      } catch (error) {
        console.error('Error fetching document media:', error)
        return { ...doc, url: null }
      }
    })
  )

  // Get presigned URLs for image blocks and use localized block data
  const blocksWithUrls = await Promise.all(
    article.blocks.map(async (block) => {
      try {
        // Use localized block data if available, otherwise fallback to canonical block data
        const blockData = block.i18n[0]?.data || block.data

        if (block.type === ArticleBlockType.IMAGE && (blockData as any)?.mediaId) {
          try {
            const media = await prisma.media.findUnique({
              where: { id: (blockData as any).mediaId },
            })
            if (media?.key) {
              try {
                const url = await getPresignedUrl(media.key, 3600)
                return { ...block, data: blockData, imageUrl: url }
              } catch {
                return { ...block, data: blockData, imageUrl: media.url }
              }
            }
            return { ...block, data: blockData, imageUrl: media?.url || '' }
          } catch (error) {
            console.error('Error fetching block media:', error)
            return { ...block, data: blockData, imageUrl: '' }
          }
        }
        if (block.type === ArticleBlockType.DOCUMENT && (blockData as any)?.mediaId) {
          try {
            const media = await prisma.media.findUnique({
              where: { id: (blockData as any).mediaId },
            })
            if (media) {
              let url = media.url
              if (media.key) {
                try {
                  url = await getPresignedUrl(media.key, 3600)
                } catch {
                  // Fallback to original URL
                }
              }
              return { ...block, data: { ...(blockData as any), url } }
            }
            return { ...block, data: blockData }
          } catch (error) {
            console.error('Error fetching document media:', error)
            return { ...block, data: blockData }
          }
        }
        return { ...block, data: blockData }
      } catch (error) {
        console.error('Error processing block:', error)
        // Return block with canonical data as fallback
        return { ...block, data: block.data }
      }
    })
  )

  const isCompanyNewsFlag = effectiveIsCompanyNews({
    articleType: article.articleType,
    isCompanyNews: (article as { isCompanyNews?: boolean | null }).isCompanyNews,
    categorySlugs: article.categorySlugs,
  })

  return {
    ...article,
    i18n: i18n,
    coverUrl: coverUrl || '',
    galleryUrls,
    documents: documentsWithUrls,
    blocks: blocksWithUrls,
    projects,
    categories,
    locale,
    articleType: article.articleType,
    isCompanyNews: isCompanyNewsFlag,
  }
}

export async function generateMetadata({ params }: { params: { slug: string } }): Promise<Metadata> {
  try {
    const cookieStore = await cookies()
    const locale = await getLocaleFromCookies(cookieStore) || defaultLocale
    const article = await getArticle(params.slug, locale)

    if (!article) {
      return {
        title: 'Article not found',
      }
    }

    const coverUrl = article.coverUrl

  return {
    title: article.i18n.metaTitle || article.i18n.title,
    description: article.i18n.metaDescription || article.i18n.standfirst,
    openGraph: {
      title: article.i18n.metaTitle || article.i18n.title,
      description: article.i18n.metaDescription || article.i18n.standfirst,
      images: coverUrl ? [{ url: coverUrl }] : [],
      type: 'article',
      publishedTime: article.publishedAt ? article.publishedAt.toISOString() : undefined,
      authors: [article.authorName],
    },
    twitter: {
      card: 'summary_large_image',
      title: article.i18n.metaTitle || article.i18n.title,
      description: article.i18n.metaDescription || article.i18n.standfirst,
      images: coverUrl ? [coverUrl] : [],
    },
  }
  } catch (error) {
    console.error('Error generating metadata for article:', error)
    return {
      title: 'Article',
      description: 'Article page',
    }
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
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '')
}

function renderBlock(
  block: ArticleBlock & { imageUrl?: string },
  headings: Heading[]
): { element: JSX.Element; heading?: Heading } {
  switch (block.type) {
    case ArticleBlockType.HEADING:
      const headingText = (block.data as any).text || ''
      const headingId = slugify(headingText)
      const heading: Heading = {
        id: headingId,
        text: headingText,
        level: 2, // Default to H2, could be enhanced to support H3
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
                  <a href={href} className="text-indigo-600 hover:text-indigo-800 underline">
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
            {block.imageUrl ? (
              <img
                src={block.imageUrl}
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
              <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          </div>
        ),
      }
    default:
      return { element: <></> }
  }
}

export default async function ArticlePage({ params }: { params: { slug: string } }) {
  // Get locale from cookie
  const cookieStore = await cookies()
  const locale = await getLocaleFromCookies(cookieStore) || defaultLocale
  
  const article = await getArticle(params.slug, locale)
  const menuItems = await getPrimaryMenu(locale)

  if (!article) {
    notFound()
  }

  // Get theme color from blog CMS page or default to 'light' for blog articles
  const cmsPage = await prisma.page.findUnique({
    where: { slug: 'blog' },
  })
  const themeColor = (cmsPage?.themeColor && (cmsPage.themeColor === 'dark' || cmsPage.themeColor === 'light'))
    ? cmsPage.themeColor as 'dark' | 'light'
    : 'light'

  const dateLabels = getDateLabels(locale)
  const readingTime = calculateReadingTime(article.blocks)

  // Determine published date (use publishedAt if available, otherwise createdAt)
  const publishedDate = article.publishedAt
    ? new Date(article.publishedAt)
    : new Date(article.createdAt)
  const updatedDate = new Date(article.updatedAt)

  // Show "Updated" only if updatedAt is significantly later than publishedAt (more than 60 seconds)
  const showUpdated = updatedDate.getTime() - publishedDate.getTime() > 60000

  const slugTags = parseCategorySlugs((article as { categorySlugs?: unknown }).categorySlugs)
  const isVancelianCompanyNews =
    article.isCompanyNews === true || slugTags.includes('vancelian')

  const schemaOrg = {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: article.i18n.title,
    description: article.i18n.standfirst,
    image: article.coverUrl,
    datePublished: article.publishedAt,
    dateModified: article.updatedAt,
    author: {
      '@type': 'Person',
      name: article.authorName,
      jobTitle: article.authorRole || undefined,
    },
    publisher: {
      '@type': 'Organization',
      name: isVancelianCompanyNews ? 'Vancelian' : 'Arquantix',
      ...(isVancelianCompanyNews ? { url: 'https://www.vancelian.com' } : {}),
    },
  }

  // Extract headings for TOC
  const headings: Heading[] = []
  const blockElements = article.blocks.map((block) => {
    const result = renderBlock(block, headings)
    return { blockId: block.id, element: result.element }
  })

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(schemaOrg) }}
      />
      <ArticleReadingLayout menuItems={menuItems} themeColor={themeColor}>
        {/* Premium Header */}
        <header className="max-w-[960px] mx-auto px-4 sm:px-8 md:px-16 pt-12 pb-8">
          <div className="text-sm text-gray-500 mb-6 space-y-1">
            <div>
              {dateLabels.published}{' '}
              <time dateTime={publishedDate.toISOString()}>
                {formatArticleDate(publishedDate, locale)}
              </time>
            </div>
            {showUpdated && (
              <div>
                {dateLabels.updated}{' '}
                <time dateTime={updatedDate.toISOString()}>
                  {formatArticleDate(updatedDate, locale)}
                </time>
              </div>
            )}
          </div>
          
          <div className="mb-4 flex flex-wrap gap-2">
            <span className="inline-block px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-800">
              {article.articleType === 'ANALYSIS'
                ? 'Analysis'
                : article.isCompanyNews
                  ? 'Company News'
                  : 'Market News'}
            </span>
            {article.categories &&
              article.categories.map((category) => (
                <span
                  key={category.id}
                  className="inline-block px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-xs font-semibold"
                >
                  {category.label}
                </span>
              ))}
          </div>

          <h1 className="text-[2.75rem] md:text-[2.75rem] font-bold text-gray-900 mb-6 leading-tight tracking-tight">
            {article.i18n.title}
          </h1>
          <p className="text-xl md:text-2xl text-gray-700 italic mb-8 leading-relaxed">
            {article.i18n.standfirst}
          </p>
          <div className="flex items-center gap-3 text-base text-gray-600 border-t border-gray-200 pt-6">
            <span className="font-semibold">{article.authorName}</span>
            {article.authorRole && (
              <>
                <span className="text-gray-400">•</span>
                <span className="text-gray-500">{article.authorRole}</span>
              </>
            )}
            <span className="text-gray-400">•</span>
            <span className="text-gray-500">
              {readingTime} {dateLabels.minRead}
            </span>
          </div>
        </header>

        {/* Header Media: Video > Gallery > Cover Image */}
        {(article.videoUrl || (article.galleryUrls && article.galleryUrls.length > 0) || article.coverUrl) && (
          <div className="max-w-[960px] mx-auto px-4 sm:px-8 md:px-16 mb-12">
            {/* Cover title above media if exists */}
            {article.i18n.coverTitle && (
              <p className="text-sm md:text-base text-neutral-500 leading-relaxed mb-3">
                {article.i18n.coverTitle}
              </p>
            )}

            {/* Video (replaces cover if exists) */}
            {article.videoUrl ? (
              <div className="relative aspect-video bg-black rounded overflow-hidden">
                <iframe
                  src={
                    article.videoUrl.includes('youtube.com') || article.videoUrl.includes('youtu.be')
                      ? `https://www.youtube.com/embed/${article.videoUrl.includes('watch?v=') ? article.videoUrl.split('watch?v=')[1].split('&')[0] : article.videoUrl.split('/').pop()}`
                      : article.videoUrl.includes('vimeo.com')
                      ? `https://player.vimeo.com/video/${article.videoUrl.split('/').pop()}`
                      : article.videoUrl
                  }
                  className="w-full h-full"
                  allowFullScreen
                  title={article.i18n.title}
                />
              </div>
            ) : article.galleryUrls && article.galleryUrls.length > 0 ? (
              /* Gallery Carousel (cover + gallery images) */
              <ArticleCarousel
                images={[article.coverUrl, ...article.galleryUrls].filter(Boolean)}
                title={article.i18n.title}
              />
            ) : article.coverUrl ? (
              /* Simple Cover Image */
              <div className="relative">
                <img
                  src={article.coverUrl}
                  alt={article.i18n.title}
                  className="w-full h-auto"
                />
              </div>
            ) : null}

            {/* Cover metadata: Credit, Source - below media */}
            {(article.coverCredit || article.coverSource) && (
              <div className="mt-3 text-xs uppercase tracking-wide text-neutral-500">
                {article.coverCredit && <span>{article.coverCredit}</span>}
                {article.coverCredit && article.coverSource && <span> / </span>}
                {article.coverSource && <span>{article.coverSource}</span>}
              </div>
            )}
          </div>
        )}

        {/* Content with TOC */}
        <div className="max-w-[1280px] mx-auto pb-16">
          <div className="flex flex-col lg:flex-row">
            {/* Main content */}
            <div className="flex-1 max-w-[960px] mx-auto px-4 sm:px-8 md:px-16">
              <div className="text-lg leading-[1.75] text-gray-800">
                {blockElements.map(({ blockId, element }) => (
                  <div key={blockId}>{element}</div>
                ))}
              </div>
            </div>

            {/* TOC Sidebar */}
            {headings.length >= 3 && (
              <TableOfContents headings={headings} />
            )}
          </div>
        </div>

        {/* Documents at the bottom with separator */}
        {article.documents && article.documents.length > 0 && (
          <div className="max-w-[960px] mx-auto px-4 sm:px-8 md:px-16 mt-16 pb-12">
            <div className="border-t border-gray-200 pt-8">
              <div className="space-y-3">
                {article.documents.map((doc: any, index: number) => (
                  <a
                    key={index}
                    href={doc.url || '#'}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                  >
                    <div className="w-10 h-10 bg-gray-200 rounded flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-semibold">PDF</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-gray-900 truncate">{doc.title || 'Document'}</p>
                    </div>
                    <svg className="w-5 h-5 text-gray-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </a>
                ))}
              </div>
            </div>
          </div>
        )}
      </ArticleReadingLayout>
    </>
  )
}

