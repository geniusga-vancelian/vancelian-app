import { figmaDsTitleSmallClassName } from '@/components/design-system/extracted'
import {
  ArticleShareFacebookIcon,
  ArticleShareInstagramIcon,
  ArticleShareLinkedInIcon,
  ArticleShareXIcon,
} from '@/components/blog/article-share-icons'
import { ArticleShareYoutubeNativeButton } from '@/components/blog/article-share-youtube-native-button'
import { getLocaleOrDefault } from '@/config/locales'
import { siteCommonCta } from '@/lib/i18n/siteCommonCta'

function shareUrl(
  type: 'facebook' | 'twitter' | 'linkedin' | 'email',
  pageUrl: string,
  title: string,
) {
  const u = encodeURIComponent(pageUrl)
  const t = encodeURIComponent(title)
  switch (type) {
    case 'facebook':
      return `https://www.facebook.com/sharer/sharer.php?u=${u}`
    case 'twitter':
      return `https://twitter.com/intent/tweet?url=${u}&text=${t}`
    case 'linkedin':
      return `https://www.linkedin.com/sharing/share-offsite/?url=${u}`
    case 'email':
      return `mailto:?subject=${t}&body=${u}`
    default:
      return pageUrl
  }
}

function shareThreadsUrl(pageUrl: string, title: string) {
  return `https://www.threads.net/intent/post?text=${encodeURIComponent(`${title}\n\n${pageUrl}`)}`
}

/** Pastilles 24px, pictogrammes blancs sur fond noir (kit SVG Figma). */
const iconClass =
  'grid size-6 shrink-0 select-none place-items-center rounded-full bg-black text-white transition-colors hover:bg-neutral-900 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-black'

export function ArticleShareRow({
  pageUrl,
  title,
  locale,
  shareLabel,
}: {
  pageUrl: string
  title: string
  locale: string
  shareLabel?: string
}) {
  const label = shareLabel?.trim() || siteCommonCta(locale, 'article_share')
  const loc = getLocaleOrDefault(locale)
  return (
    <div className="mb-8">
      <p className={`${figmaDsTitleSmallClassName} mb-5 text-[#0f1219]`}>
        {label}
      </p>
      <div className="flex flex-wrap items-center gap-2.5">
        <a
          href={shareUrl('facebook', pageUrl, title)}
          target="_blank"
          rel="noopener noreferrer"
          className={iconClass}
          aria-label="Facebook"
        >
          <ArticleShareFacebookIcon className="text-white" />
        </a>
        <a
          href={shareUrl('twitter', pageUrl, title)}
          target="_blank"
          rel="noopener noreferrer"
          className={iconClass}
          aria-label="X / Twitter"
        >
          <ArticleShareXIcon className="text-white" />
        </a>
        <a
          href={shareUrl('linkedin', pageUrl, title)}
          target="_blank"
          rel="noopener noreferrer"
          className={iconClass}
          aria-label="LinkedIn"
        >
          <ArticleShareLinkedInIcon className="text-white" />
        </a>
        <a
          href={shareThreadsUrl(pageUrl, title)}
          target="_blank"
          rel="noopener noreferrer"
          className={iconClass}
          aria-label={siteCommonCta(loc, 'article_share_threads_aria')}
        >
          <ArticleShareInstagramIcon className="text-white" />
        </a>
        <ArticleShareYoutubeNativeButton
          pageUrl={pageUrl}
          title={title}
          locale={locale}
          className={iconClass}
        />
      </div>
    </div>
  )
}
