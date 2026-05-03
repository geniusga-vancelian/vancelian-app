import { redirect, notFound } from 'next/navigation'
import { cookies } from 'next/headers'
import { getSessionFromCookie } from '@/lib/auth'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { getSectionTypeDemoSection } from '@/lib/cms/sectionTypeDemoPreview'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { resolveCanonicalSectionKey } from '@/lib/sections/library'
import { figmaDsSiteShellLightClassName } from '@/components/design-system/extracted/tokens/surfaces'
import { cn } from '@/lib/utils'

interface Props {
  params: { sectionKey: string }
  searchParams: Record<string, string | string[] | undefined>
}

/**
 * Aperçu admin : rendu d’un type de module à partir des données par défaut du catalogue (démo).
 */
export default async function PreviewSectionDemoPage({ params, searchParams }: Props) {
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

  const section = await getSectionTypeDemoSection(params.sectionKey, locale)
  if (!section) {
    notFound()
  }

  const canonical = resolveCanonicalSectionKey(section.key) ?? section.key

  return (
    <div className={cn(figmaDsSiteShellLightClassName)}>
      <main
        className={cn(
          /** Lecteur seul : même retrait que {@link ArticleReadingLayout} sous le menu fixe. */
          canonical === 'blog_article_reader' && 'pt-20 md:pt-24',
        )}
      >
        <SectionRenderer
          section={section}
          locale={section.locale}
          blogHeroBleedUnderNav={
            canonical === 'blog_hero' || canonical === 'blog_article_hero'
          }
        />
      </main>
    </div>
  )
}
