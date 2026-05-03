'use client'

import { getLocaleOrDefault } from '@/config/locales'
import { ArticleShareYoutubeIcon } from '@/components/blog/article-share-icons'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'

type Props = {
  pageUrl: string
  title: string
  locale: string
  className: string
}

/**
 * Icône YouTube fournie par le design : ouvre le partage système (mobile) ou copie le lien (desktop).
 * Pas d’URL de « share article » YouTube côté web ; le pictogramme reste celui du kit Figma.
 */
export function ArticleShareYoutubeNativeButton({ pageUrl, title, locale, className }: Props) {
  const loc = getLocaleOrDefault(locale)
  return (
    <button
      type="button"
      className={className}
      aria-label={siteCommonCta(loc, 'article_share_system_aria')}
      onClick={() => {
        if (typeof navigator !== 'undefined' && typeof navigator.share === 'function') {
          void navigator.share({ title, url: pageUrl }).catch(() => {})
          return
        }
        if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
          void navigator.clipboard.writeText(pageUrl).catch(() => {})
        }
      }}
    >
      <ArticleShareYoutubeIcon className="text-white" />
    </button>
  )
}
