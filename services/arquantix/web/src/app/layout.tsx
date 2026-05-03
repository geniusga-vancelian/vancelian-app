import type { Metadata } from 'next'
import { cookies, headers } from 'next/headers'
import '../styles/globals.css'
import { SiteFooter } from '@/components/site/SiteFooter'
import { SiteChrome } from '@/components/site/SiteChrome'
import { getPrimaryMenu, injectLanguageSwitcherIfMissing } from '@/lib/menu/getPrimaryMenu'
import type { Locale } from '@/config/locales'
import { resolveLayoutLocale } from '@/lib/i18n/resolveLayoutLocale'
import {
  DEFAULT_NAV_SHELL,
  getNavShellStateForPathname,
} from '@/lib/cms/navShellContext'
import type { MenuItem } from '@/lib/menu/getPrimaryMenu'
import { CMS_PAGE_METADATA_FALLBACK } from '@/lib/metadata/cmsPageMetadata'
import { getSiteMetadataBase } from '@/lib/metadata/siteOrigin'
import { figmaDsBodyRootClassName } from '@/components/design-system/extracted/tokens/surfaces'

// TODO: Le CSS exporté Figma (Tailwind v4) n'est pas compatible avec Tailwind v3
// Les composants utilisent déjà des classes Tailwind, ils devraient fonctionner sans
// import '../styles/figma-export.css'

const siteMetadataBase = getSiteMetadataBase()

/**
 * Valeurs par défaut si une route ne définit pas son propre `generateMetadata`.
 * `metadataBase` : défini si `NEXT_PUBLIC_SITE_URL` ou `VERCEL_URL` (voir `siteOrigin.ts`).
 */
export const metadata: Metadata = {
  ...CMS_PAGE_METADATA_FALLBACK,
  ...(siteMetadataBase ? { metadataBase: siteMetadataBase } : {}),
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const headersList = await headers()
  const pathname = headersList.get('x-arq-pathname') ?? '/'
  const cookieStore = await cookies()
  const pathLocale = headersList.get('x-arq-locale')
  const locale = resolveLayoutLocale({ pathLocaleHeader: pathLocale, cookieStore }) as Locale
  const preferDraftNav = pathname.startsWith('/preview/')
  /** Heroes + blog : en prod ils intègrent le menu primaire — même rendu en preview section-demo. */
  const isIntegratedNavSectionDemoPreview =
    pathname === '/preview/section-demo/hero' ||
    pathname === '/preview/section-demo/hero_secondary' ||
    pathname === '/preview/section-demo/blog_hero' ||
    pathname === '/preview/section-demo/blog_article_reader' ||
    pathname === '/preview/section-demo/blog_article_hero'
  /** Routes "print" du design system Cursor : exportées en PDF, sans coquille. */
  const isCursorDesignSystemPrint = pathname.startsWith('/design/cursor/print')
  /** Aperçu isolé sans coquille menu (common-module, section, section-demo sauf modules avec nav intégrée, article-block-demo, ou previews e-mail). */
  const shellLessPreview =
    pathname.startsWith('/preview/common-module') ||
    pathname.startsWith('/preview/section/') ||
    pathname.startsWith('/preview/email/') ||
    pathname.startsWith('/preview/article-block-demo/') ||
    (pathname.startsWith('/preview/section-demo/') && !isIntegratedNavSectionDemoPreview) ||
    isCursorDesignSystemPrint
  /** Aucun pied de page global sur les routes d’aperçu de modules. */
  const hideGlobalFooter =
    pathname.startsWith('/preview/common-module') ||
    pathname.startsWith('/preview/section/') ||
    pathname.startsWith('/preview/email/') ||
    pathname.startsWith('/preview/section-demo/') ||
    pathname.startsWith('/preview/article-block-demo/') ||
    isCursorDesignSystemPrint

  const menuFallback: MenuItem[] = injectLanguageSwitcherIfMissing(
    [
      {
        id: 'fallback-home',
        label: 'Home',
        urlPath: `/${locale}`,
        type: 'LINK',
        isRoot: true,
        enabled: true,
        order: 0,
      },
    ],
    locale,
  )

  let menuItems: MenuItem[] = menuFallback
  let initialNav = DEFAULT_NAV_SHELL
  if (!shellLessPreview) {
    try {
      const [m, n] = await Promise.all([
        getPrimaryMenu(locale),
        getNavShellStateForPathname(pathname, locale, { preferDraft: preferDraftNav }),
      ])
      menuItems = m
      initialNav = n
    } catch (e) {
      console.error('[RootLayout] Menu ou coquille nav indisponible — repli minimal.', e)
    }
  }

  return (
    <html lang={locale}>
      <body className={figmaDsBodyRootClassName}>
        <SiteChrome menuItems={menuItems} initialNav={initialNav}>
          {children}
        </SiteChrome>
        {!hideGlobalFooter ? <SiteFooter /> : null}
      </body>
    </html>
  )
}

