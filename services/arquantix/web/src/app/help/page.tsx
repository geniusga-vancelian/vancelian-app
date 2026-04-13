import { getHelpCollections } from '@/lib/help/get-help-data'
import { SectionHelpHero } from '@/components/sections/SectionHelpHero'
import { SectionHelpCollectionsGrid } from '@/components/sections/SectionHelpCollectionsGrid'
import { getLocaleFromCookies } from '@/lib/i18n/locale-server'
import { defaultLocale } from '@/config/locales'
import { cookies } from 'next/headers'
import { getPrimaryMenu } from '@/lib/menu/getPrimaryMenu'
import { Navigation } from '@/components/sections/Navigation'
import { prisma } from '@/lib/prisma'
import { getPageSections } from '@/lib/cms/content'
import { SectionRenderer } from '@/components/cms/SectionRenderer'

export const metadata = {
  title: 'Centre d\'aide - Arquantix',
  description: 'Trouvez des réponses à vos questions sur Arquantix',
}

export default async function HelpPage() {
  const cookieStore = await cookies()
  const locale = await getLocaleFromCookies(cookieStore) || defaultLocale
  const menuItems = await getPrimaryMenu(locale)

  // Check if a CMS page with slug "help" exists
  const cmsPage = await prisma.page.findUnique({
    where: { slug: 'help' },
  })

  const themeColor = (cmsPage?.themeColor && (cmsPage.themeColor === 'dark' || cmsPage.themeColor === 'light')) 
    ? cmsPage.themeColor as 'dark' | 'light'
    : 'light'

  // If CMS page exists, render via CMS sections
  if (cmsPage) {
    const sections = await getPageSections('help', locale, 'published')

    if (sections.length > 0) {
      return (
        <>
          <Navigation menuItems={menuItems} themeColor={themeColor} />
          <div className="min-h-screen bg-white pt-20 md:pt-24">
            {sections.map((section) => (
              <SectionRenderer
                key={section.id}
                section={section}
                locale={locale}
                collectionSlug={undefined}
                categorySlug={undefined}
              />
            ))}
          </div>
        </>
      )
    }
  }

  // Fallback: render with hardcoded sections (will be CMS-driven later)
  return (
    <>
      <Navigation menuItems={menuItems} themeColor={themeColor} />
      <div className="min-h-screen bg-white pt-20 md:pt-24">
        <SectionHelpHero
          title="Conseils et réponses de l'équipe Arquantix"
          placeholderSearch="Rechercher un article…"
          backgroundStyle="purple"
          locale={locale}
        />
        <SectionHelpCollectionsGrid
          sectionTitle="Collections"
          sectionSubtitle="Parcourir par thème"
          cardCtaLabel="Voir"
          articlesCountLabel="articles"
          emptyTitle="Aucune collection"
          emptySubtitle="Créez votre première collection dans l'admin."
          locale={locale}
        />
      </div>
    </>
  )
}

