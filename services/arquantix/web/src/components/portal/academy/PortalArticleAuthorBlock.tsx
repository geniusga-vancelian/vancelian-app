'use client'

import { authorInitials } from '@/lib/portal/portalArticleFormat'

type Props = {
  authorName: string
  authorRole: string | null
}

/** Bloc auteur — handoff `.art-author`. */
export function PortalArticleAuthorBlock({ authorName, authorRole }: Props) {
  if (!authorName.trim()) return null

  return (
    <div className="art-author">
      <span className="art-author__avt" aria-hidden>
        <span className="art-author__mono">{authorInitials(authorName)}</span>
      </span>
      <div className="art-author__body">
        <div className="art-author__name">{authorName}</div>
        {authorRole ? <div className="art-author__role">{authorRole}</div> : null}
      </div>
      <button type="button" className="btn btn--secondary btn--sm">
        Follow
      </button>
    </div>
  )
}
