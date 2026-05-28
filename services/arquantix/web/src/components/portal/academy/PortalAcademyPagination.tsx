'use client'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { buildAcademyPagerPages } from '@/lib/portal/academyFormat'
import { cn } from '@/lib/utils'

type Props = {
  page: number
  pageCount: number
  onChange: (page: number) => void
}

/** Pagination — handoff `.acd-pager`. */
export function PortalAcademyPagination({ page, pageCount, onChange }: Props) {
  if (pageCount <= 1) return null

  const pages = buildAcademyPagerPages(page, pageCount)

  return (
    <nav className="acd-pager" aria-label="Pagination">
      <button
        type="button"
        className="acd-pager__nav"
        onClick={() => onChange(Math.max(1, page - 1))}
        disabled={page === 1}
        aria-label="Page précédente"
      >
        <KalaiIcon name="chevron-left" size={16} />
      </button>
      <div className="acd-pager__list">
        {pages.map((entry, index) =>
          entry === '…' ? (
            <span key={`sep-${index}`} className="acd-pager__sep" aria-hidden>
              …
            </span>
          ) : (
            <button
              key={entry}
              type="button"
              className={cn('acd-pager__num', entry === page && 'is-active')}
              onClick={() => onChange(entry)}
              aria-current={entry === page ? 'page' : undefined}
            >
              {entry}
            </button>
          ),
        )}
      </div>
      <button
        type="button"
        className="acd-pager__nav"
        onClick={() => onChange(Math.min(pageCount, page + 1))}
        disabled={page === pageCount}
        aria-label="Page suivante"
      >
        <KalaiIcon name="chevron-right" size={16} />
      </button>
    </nav>
  )
}
