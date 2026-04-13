import { notFound } from 'next/navigation'
import { getPageSections } from '@/lib/cms/content'
import { getLocaleOrDefault } from '@/config/locales'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { Navigation } from '@/components/sections/Navigation'
import { prisma } from '@/lib/prisma'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'

interface PublicPageProps {
  params: { slug: string }
  searchParams: { locale?: string }
}

export default async function PublicPage({ params, searchParams }: PublicPageProps) {
  const { slug } = params

  // "home" should not match this route (home is on /)
  if (slug === 'home') {
    notFound()
  }

  // Check if page exists
  const page = await prisma.page.findUnique({
    where: { slug },
  })

  if (!page) {
    notFound()
  }

  // Only serve pages with urlPath starting with "/" (not "/")
  // This ensures "home" doesn't match here
  if (page.urlPath === '/') {
    notFound()
  }

  const locale = getLocaleOrDefault(searchParams.locale)
  const sections = await getPageSections(slug, locale, 'published')
  const menuItems = await getPrimaryMenu(locale)

  if (sections.length === 0) {
    notFound()
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <Navigation menuItems={menuItems} />
      <main>
        {sections.map((section) => (
          <SectionRenderer key={section.id} section={section} />
        ))}
      </main>
    </div>
  )
}

