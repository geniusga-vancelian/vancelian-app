import { redirect, notFound } from 'next/navigation'
import { cookies } from 'next/headers'
import { getSessionFromCookie } from '@/lib/auth'
import { resolvePublicLocale } from '@/lib/i18n/resolvePublicLocale'
import { SectionRenderer } from '@/components/cms/SectionRenderer'
import { getCommonModulePreviewSection } from '@/lib/cms/commonModulePreview'
import { figmaDsSiteShellLightClassName } from '@/components/design-system/extracted/tokens/surfaces'
import { cn } from '@/lib/utils'

type Props = {
  params: { id: string }
  searchParams: Record<string, string | string[] | undefined>
}

/**
 * Aperçu admin : un seul module commun (Zone 2), même rendu public que sur une page.
 */
export default async function PreviewCommonModulePage({ params, searchParams }: Props) {
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
  const section = await getCommonModulePreviewSection(params.id, locale)

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
