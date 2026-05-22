import Link from 'next/link'
import { headers } from 'next/headers'
import { CONSOLE_PATH_PREFIX, isFullSitePreviewPathname } from '@/lib/portal/portalRouting'

export async function PreviewDraftBanner() {
  const pathname = headers().get('x-arq-pathname') ?? ''
  if (!isFullSitePreviewPathname(pathname)) {
    return null
  }

  return (
    <div
      className="sticky top-0 z-[100] border-b border-amber-200/80 bg-amber-50/95 px-4 py-2 text-sm text-amber-950 backdrop-blur-sm"
      role="status"
      aria-live="polite"
    >
      <div className="mx-auto flex max-w-[1280px] flex-wrap items-center justify-between gap-2">
        <p className="min-w-0">
          <span className="font-semibold">Aperçu brouillon</span>
          <span className="hidden sm:inline">
            {' '}
            — contenu CMS non publié, visible uniquement avec votre session admin.
          </span>
        </p>
        <Link
          href={`${CONSOLE_PATH_PREFIX}/pages`}
          className="shrink-0 rounded-md border border-amber-300 bg-white px-3 py-1 text-xs font-medium text-amber-950 shadow-sm transition hover:bg-amber-100"
        >
          Retour au CMS
        </Link>
      </div>
    </div>
  )
}
