import { redirect, notFound } from 'next/navigation'
import { cookies } from 'next/headers'
import { getSessionFromCookie } from '@/lib/auth'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { getSectionPreviewById } from '@/lib/cms/content'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { figmaDsSiteShellLightClassName } from '@/components/design-system/extracted/tokens/surfaces'
import { cn } from '@/lib/utils'

interface Props {
  params: { id: string }
  searchParams: Record<string, string | string[] | undefined>
}

/**
 * Aperçu admin : rendu d’un seul module (section) en brouillon, même pipeline que la page complète.
 */
export default async function PreviewSectionPage({ params, searchParams }: Props) {
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

  const section = await getSectionPreviewById(params.id, locale, 'draft')
  if (!section) {
    notFound()
  }

  return (
    <div className={cn(figmaDsSiteShellLightClassName)}>
      <main>
        <SectionRenderer section={section} locale={section.locale} />
      </main>
    </div>
  )
}
