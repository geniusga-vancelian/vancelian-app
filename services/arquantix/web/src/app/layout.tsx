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
import {
  getSiteI18nSettingsCached,
  shouldShowPublicLanguageSwitcher,
} from '@/lib/i18n/siteI18nSettings'

const siteMetadataBase = getSiteMetadataBase()

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
  const siteI18n = await getSiteI18nSettingsCached()
  const locale = resolveLayoutLocale({
    pathLocaleHeader: pathLocale,
    cookieStore,
    fallbackLocale: siteI18n.defaultLocale,
  }) as Locale
  const showPublicLanguageSwitcher = shouldShowPublicLanguageSwitcher(siteI18n)
  const preferDraftNav = pathname.startsWith('/preview/')
  const isIntegratedNavSectionDemoPreview =
    pathname === '/preview/section-demo/hero' ||
    pathname === '/preview/section-demo/hero_secondary' ||
    pathname === '/preview/section-demo/blog_hero' ||
    pathname === '/preview/section-demo/blog_article_reader' ||
    pathname === '/preview/section-demo/blog_article_hero'
  const isCursorDesignSystemPrint = pathname.startsWith('/design/cursor/print')
  const shellLessPreview =
    pathname.startsWith('/preview/common-module') ||
    pathname.startsWith('/preview/section/') ||
    pathname.startsWith('/preview/email/') ||
    pathname.startsWith('/preview/article-block-demo/') ||
    (pathname.startsWith('/preview/section-demo/') && !isIntegratedNavSectionDemoPreview) ||
    isCursorDesignSystemPrint
  const hideGlobalFooter =
    pathname.startsWith('/preview/common-module') ||
    pathname.startsWith('/preview/section/') ||
    pathname.startsWith('/preview/email/') ||
    pathname.startsWith('/preview/section-demo/') ||
    pathname.startsWith('/preview/article-block-demo/') ||
    isCursorDesignSystemPrint

  const menuFallback: MenuItem[] = showPublicLanguageSwitcher
    ? injectLanguageSwitcherIfMissing(
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
    : [
        {
          id: 'fallback-home',
          label: 'Home',
          urlPath: `/${locale}`,
          type: 'LINK',
          isRoot: true,
          enabled: true,
          order: 0,
        },
      ]

  let menuItems: MenuItem[] = menuFallback
  let initialNav = DEFAULT_NAV_SHELL
  if (!shellLessPreview) {
    try {
      const [m, n] = await Promise.all([
        getPrimaryMenu(locale, { languageSwitcherEnabled: showPublicLanguageSwitcher }),
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
        <SiteChrome
          menuItems={menuItems}
          initialNav={initialNav}
          showLanguageSwitcher={showPublicLanguageSwitcher}
          publicLocales={siteI18n.supportedLocales}
        >
          {children}
        </SiteChrome>
        {!hideGlobalFooter ? <SiteFooter /> : null}
      </body>
    </html>
  )
}
