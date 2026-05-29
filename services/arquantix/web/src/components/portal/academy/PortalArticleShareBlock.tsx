'use client'

import { useCallback, useMemo, useState } from 'react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'

type Props = {
  title: string
}

function WhatsAppIcon({ size = 16 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden
      style={{ display: 'block' }}
    >
      <path d="M19.05 4.91A10 10 0 0 0 12 2 10 10 0 0 0 2 12c0 1.76.46 3.45 1.34 4.95L2 22l5.16-1.35A10 10 0 0 0 12 22a10 10 0 0 0 10-10 10 10 0 0 0-2.95-7.09zM12 20.17a8.17 8.17 0 0 1-4.16-1.14l-.3-.18-3.07.8.82-2.99-.19-.31a8.18 8.18 0 1 1 6.9 3.82zm4.48-6.13c-.25-.12-1.45-.72-1.68-.8-.22-.08-.39-.12-.55.12-.17.25-.63.8-.78.97-.14.16-.29.18-.53.06-.25-.12-1.04-.38-1.98-1.22-.74-.66-1.23-1.47-1.37-1.72-.14-.25-.02-.39.11-.51.11-.11.25-.29.37-.43.13-.14.17-.25.25-.41.08-.16.04-.31-.02-.43-.06-.12-.55-1.33-.76-1.83-.2-.48-.41-.41-.55-.42l-.47-.01c-.16 0-.43.06-.66.31-.22.25-.86.84-.86 2.05 0 1.21.88 2.38 1 2.55.12.17 1.74 2.66 4.22 3.73.59.26 1.05.41 1.41.52.59.19 1.13.16 1.55.1.47-.07 1.45-.59 1.66-1.16.2-.57.2-1.06.14-1.16-.06-.1-.22-.16-.47-.28z" />
    </svg>
  )
}

/** Share block — handoff `.art-share`. */
export function PortalArticleShareBlock({ title }: Props) {
  const [copied, setCopied] = useState(false)

  const pageUrl = useMemo(() => {
    if (typeof window === 'undefined') return ''
    return window.location.href
  }, [])

  const waHref = useMemo(() => {
    if (!pageUrl) return 'https://wa.me/'
    const text = title.trim() ? `${title.trim()} — ${pageUrl}` : pageUrl
    return `https://wa.me/?text=${encodeURIComponent(text)}`
  }, [pageUrl, title])

  const mailHref = useMemo(() => {
    if (!pageUrl) return 'mailto:'
    const subject = title.trim() || 'Vancelian article'
    const body = pageUrl
    return `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  }, [pageUrl, title])

  const copyLink = useCallback(() => {
    if (typeof navigator !== 'undefined' && navigator.clipboard && pageUrl) {
      navigator.clipboard.writeText(pageUrl).catch(() => {})
    }
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }, [pageUrl])

  const shareNative = useCallback(async () => {
    if (typeof navigator === 'undefined' || !navigator.share || !pageUrl) return
    try {
      await navigator.share({ title: title.trim() || 'Vancelian article', url: pageUrl })
    } catch {
      // User cancelled or share unavailable.
    }
  }, [pageUrl, title])

  return (
    <div className="art-share">
      <div className="art-share__eyebrow">Share article</div>
      <div className="art-share__row">
        <a className="art-share__btn" href={mailHref} aria-label="Share by email">
          <KalaiIcon name="mail" size={16} />
        </a>
        <a
          className="art-share__btn"
          href={waHref}
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Share on WhatsApp"
        >
          <WhatsAppIcon size={16} />
        </a>
        <button type="button" className="art-share__btn" aria-label="Share" onClick={shareNative}>
          <KalaiIcon name="share" size={16} />
        </button>
        <button
          type="button"
          className={copied ? 'art-share__btn is-on' : 'art-share__btn'}
          aria-label="Copy link"
          onClick={copyLink}
        >
          <KalaiIcon name="link" size={16} />
        </button>
        <button type="button" className="art-share__btn" aria-label="Bookmark">
          <KalaiIcon name="bookmark" size={16} />
        </button>
        {copied ? (
          <span className="art-share__toast" role="status">
            Link copied
          </span>
        ) : null}
      </div>
    </div>
  )
}
