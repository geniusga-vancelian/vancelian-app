import { getHelpCollection } from '@/lib/help/get-help-data'
import { SectionHelpHero } from '@/components/sections/SectionHelpHero'
import { SectionHelpBreadcrumbs } from '@/components/sections/SectionHelpBreadcrumbs'
import { SectionHelpCollectionBody } from '@/components/sections/SectionHelpCollectionBody'
import { cookies } from 'next/headers'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { notFound } from 'next/navigation'
import { prisma } from '@/lib/prisma'
import { getPageSections } from '@/lib/cms/content'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { shouldUseHeroSecondaryImageOverlay } from '@/lib/cms/heroSecondaryNav'
import { cn } from '@/lib/utils'

interface PageProps {
  params: {
    collection: string
  }
  searchParams?: Record<string, string | string[] | undefined>
}

export async function generateMetadata({ params }: PageProps) {
  const collection = await getHelpCollection(params.collection)
  if (!collection) {
    return {
      title: 'Collection non trouvée - Arquantix',
    }
  }
  return {
    title: `${collection.title} - Centre d'aide Arquantix`,
    description: collection.description || collection.subtitle || undefined,
  }
}

export default async function HelpCollectionPage({ params, searchParams }: PageProps) {
  const cookieStore = await cookies()
  const locale = resolvePublicLocale({ cookieStore, searchParams })
  const collection = await getHelpCollection(params.collection)

  if (!collection) {
    notFound()
  }

  // Check if a CMS page with slug "help-collection" exists
  const cmsPage = await prisma.page.findUnique({
    where: { slug: 'help-collection' },
  })

  // If CMS page exists, render via CMS sections
  if (cmsPage) {
    const sections = await getPageSections('help-collection', locale, 'published')
    const overlayHero = shouldUseHeroSecondaryImageOverlay(sections)

    if (sections.length > 0) {
      return (
        <div
          className={cn(
            'min-h-screen bg-white',
            !overlayHero && 'pt-20 md:pt-24',
          )}
        >
          {sections.map((section) => (
            <SectionRenderer
              key={section.id}
              section={section}
              locale={locale}
              collectionSlug={params.collection}
              categorySlug={undefined}
            />
          ))}
        </div>
      )
    }
  }

  // Fallback: render with hardcoded sections
  return (
    <div className="min-h-screen bg-white pt-20 md:pt-24">
        <SectionHelpHero
          title={collection.title}
          placeholderSearch="Rechercher un article…"
          backgroundStyle="purple"
          locale={locale}
          collectionSlug={params.collection}
          collectionTitle={collection.title}
          showBreadcrumbs={true}
          breadcrumbsRootLabel="Toutes les collections"
          breadcrumbsSeparator="›"
        />
        <SectionHelpCollectionBody
          emptyCategoriesTitle="Aucune catégorie"
          emptyCategoriesSubtitle="Aucune catégorie disponible dans cette collection."
          emptyArticlesTitle="Aucun article"
          emptyArticlesSubtitle="Aucun article disponible dans cette catégorie."
          locale={locale}
          collectionSlug={params.collection}
        />
    </div>
  )
}

