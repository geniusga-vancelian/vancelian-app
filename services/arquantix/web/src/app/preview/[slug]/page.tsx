import { redirect } from 'next/navigation'
import { getPageSections } from '@/lib/cms/content'
import { getSessionFromCookie } from '@/lib/auth'
import { cookies } from 'next/headers'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import { figmaDsSiteShellLightClassName } from '@/components/design-system/extracted/tokens/surfaces'
import { cn } from '@/lib/utils'
import { prisma } from '@/lib/prisma'
import { BlogTemplatePageView } from '@/components/cms/BlogTemplatePageView'
import { parseBlogListingSearchParams } from '@/lib/blog/parseBlogListingSearchParams'
import { VAULT_BUILDER_TEMPLATE } from '@/lib/catalog/packagedCatalogHelpers'
import { projectDetailPageContent } from '@/lib/routes/projectDetailPageShared'
import { VAULT_BUILDER_IFRAME_PREVIEW_QUERY } from '@/lib/cms/vaultBuilderPreviewConstants'

interface PreviewPageProps {
  params: { slug: string }
  searchParams: Record<string, string | string[] | undefined>
}

export default async function PreviewPage({
  params,
  searchParams,
}: PreviewPageProps) {
  // Check if user is authenticated (admin only)
  const session = await getSessionFromCookie()
  if (!session) {
    redirect('/admin/login')
  }

  const cookieStore = await cookies()
  const locale = resolvePublicLocale({
    cookieStore,
    searchParams,
    preferQueryLocaleOverCookie: true,
  })

  const cmsPage = await prisma.page.findUnique({
    where: { slug: params.slug },
    select: { template: true },
  })

  /** Même enveloppe et props que la page publique — contenu résolu en brouillon. */
  if (cmsPage?.template === 'blog') {
    const { category, pageNum, mosaicPageNum, segment } = parseBlogListingSearchParams(searchParams)
    return (
      <BlogTemplatePageView
        locale={locale}
        category={category}
        pageNum={pageNum}
        mosaicPageNum={mosaicPageNum}
        segment={segment}
        contentStatus="draft"
      />
    )
  }

  if (cmsPage?.template === VAULT_BUILDER_TEMPLATE) {
    return projectDetailPageContent({
      slug: params.slug,
      searchParams: {
        ...searchParams,
        [VAULT_BUILDER_IFRAME_PREVIEW_QUERY]: '1',
        locale,
      },
      urlLocale: locale,
    })
  }

  const sections = await getPageSections(params.slug, locale, 'draft')

  const showRaw = searchParams.raw === 'true'
  const firstCanonical =
    sections.length > 0
      ? resolveCanonicalSectionKey(sections[0]!.key) ?? sections[0]!.key
      : null
  const blogHeroBleedsFirst =
    firstCanonical === 'blog_hero' || firstCanonical === 'blog_article_hero'

  return (
    <div className={cn(figmaDsSiteShellLightClassName)}>
      {sections.length === 0 ? (
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <p className="mb-4 text-xl text-gray-400">No sections found for this page.</p>
            <a
              href="/admin/pages"
              className="text-indigo-400 underline hover:text-indigo-300"
            >
              Go to Admin
            </a>
          </div>
        </div>
      ) : showRaw ? (
        // Raw JSON view
        <div className="mx-auto max-w-4xl p-8">
          <div className="space-y-6">
            {sections.map((section) => (
              <div key={section.id} className="rounded-lg bg-gray-900 p-6 shadow">
                <div className="mb-4 flex items-start justify-between">
                  <div>
                    <h2 className="text-xl font-semibold">{section.key}</h2>
                    <p className="text-sm text-gray-400">
                      Order: {section.order} • Schema: {section.schemaVersion} • Status:{' '}
                      {section.status}
                    </p>
                  </div>
                </div>
                <pre className="overflow-auto rounded bg-gray-800 p-4 text-sm text-gray-300">
                  {JSON.stringify(section.data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <main>
          {sections.map((section, index) => (
            <SectionRenderer
              key={section.id}
              section={section}
              locale={locale}
              blogHeroBleedUnderNav={blogHeroBleedsFirst && index === 0}
            />
          ))}
        </main>
      )}
    </div>
  )
}
