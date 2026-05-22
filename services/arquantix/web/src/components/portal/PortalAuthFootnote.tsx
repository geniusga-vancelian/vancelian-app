'use client'

import type { PortalAuthContent } from '@/lib/cms/portal-auth'

type PortalAuthFootnoteProps = {
  content?: PortalAuthContent['legal']
}

function legalLinkProps(href: string) {
  if (/^https?:\/\//i.test(href)) {
    return { target: '_blank' as const, rel: 'noopener noreferrer' }
  }
  return {}
}

export function PortalAuthFootnote({ content }: PortalAuthFootnoteProps) {
  if (!content) return null

  const {
    footnotePrefix,
    footnoteConjunction,
    termsLabel,
    termsHref,
    privacyLabel,
    privacyHref,
  } = content

  return (
    <p className="portal-auth__footnote">
      {footnotePrefix}{' '}
      <a href={termsHref} className="portal-auth__link" {...legalLinkProps(termsHref)}>
        {termsLabel}
      </a>{' '}
      {footnoteConjunction}{' '}
      <a href={privacyHref} className="portal-auth__link" {...legalLinkProps(privacyHref)}>
        {privacyLabel}
      </a>
      .
    </p>
  )
}
