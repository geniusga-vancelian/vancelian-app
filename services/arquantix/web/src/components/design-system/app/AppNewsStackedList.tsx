'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

export type AppNewsCategoryDot = 'terra' | 'green' | 'blue' | 'ink'

export type AppNewsStackedAsset =
  | { type: 'image'; src: string; alt?: string }
  | { type: 'crypto'; src: string; alt?: string }
  | { type: 'glyph'; variant: 'immo' | 'patri' | 'ink' | 'warm'; label?: string }
  | { type: 'more'; count: number }

export type AppNewsStackedListItem = {
  id: string
  href: string
  title: string
  authorName: string
  dateLabel: string
  categoryLabel?: string
  categoryDot?: AppNewsCategoryDot
  assets?: AppNewsStackedAsset[]
}

export type AppNewsStackedFilter = {
  id: string
  label: string
}

type Props = {
  items: AppNewsStackedListItem[]
  filters?: AppNewsStackedFilter[]
  selectedFilterId?: string
  onFilterChange?: (id: string) => void
  emptyMessage?: string
  className?: string
  linkComponent?: typeof Link
  /** `full` = DS 79 (avatars + chip). `text` = titre + byline seulement. */
  rowVariant?: 'full' | 'text'
  /** Supprime les séparateurs entre les lignes. */
  seamless?: boolean
}

function HouseGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M3 11l9-7 9 7v9a1 1 0 0 1-1 1h-5v-7h-6v7H4a1 1 0 0 1-1-1v-9z" />
    </svg>
  )
}

function PinGlyph() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 3a7 7 0 0 0-7 7c0 4 3 7 7 11 4-4 7-7 7-11a7 7 0 0 0-7-7z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  )
}

function AssetStack({ assets }: { assets: AppNewsStackedAsset[] }) {
  if (assets.length === 0) return null

  return (
    <div className="nx__assets" aria-hidden>
      {assets.map((asset, index) => {
        if (asset.type === 'more') {
          return (
            <span key={`more-${index}`} className="a a--more">
              +{asset.count}
            </span>
          )
        }

        if (asset.type === 'glyph') {
          return (
            <span
              key={`glyph-${index}`}
              className={cn(
                'a',
                asset.variant === 'immo' && 'a--immo',
                asset.variant === 'patri' && 'a--patri',
                asset.variant === 'ink' && 'a--ink',
                asset.variant === 'warm' && 'a--warm',
              )}
            >
              {asset.variant === 'immo' ? <HouseGlyph /> : null}
              {asset.variant === 'patri' ? <PinGlyph /> : null}
              {asset.variant === 'warm' ? (asset.label ?? 'News') : null}
            </span>
          )
        }

        return (
          <span key={`img-${index}`} className="a">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={asset.src} alt={asset.alt ?? ''} />
          </span>
        )
      })}
    </div>
  )
}

function CategoryChip({ label, dot }: { label: string; dot: AppNewsCategoryDot }) {
  return (
    <span className="cchip">
      <span className={cn('cdot', `cdot--${dot}`)} aria-hidden />
      {label}
    </span>
  )
}

function NewsRow({
  item,
  LinkComponent,
  rowVariant,
}: {
  item: AppNewsStackedListItem
  LinkComponent: typeof Link
  rowVariant: 'full' | 'text'
}) {
  const content =
    rowVariant === 'text' ? (
      <>
        <h3 className="nx__title">{item.title}</h3>
        <p className="nx__byline">
          {item.authorName}
          <span className="sep" aria-hidden>
            ·
          </span>
          {item.dateLabel}
        </p>
      </>
    ) : (
      <>
        <div className="nx__rowhead">
          {item.assets && item.assets.length > 0 ? <AssetStack assets={item.assets} /> : <span />}
          {item.categoryLabel ? (
            <CategoryChip label={item.categoryLabel} dot={item.categoryDot ?? 'ink'} />
          ) : null}
        </div>
        <h3 className="nx__title">{item.title}</h3>
        <p className="nx__byline">
          {item.authorName}
          <span className="sep" aria-hidden>
            ·
          </span>
          {item.dateLabel}
        </p>
      </>
    )

  return (
    <LinkComponent
      href={item.href}
      className={cn('nx__row', rowVariant === 'text' && 'nx__row--text')}
    >
      {content}
    </LinkComponent>
  )
}

/** Liste actualités empilées — DS `79-news-stacked-list`. */
export function AppNewsStackedList({
  items,
  filters,
  selectedFilterId,
  onFilterChange,
  emptyMessage = 'No articles in this category.',
  className,
  linkComponent: LinkComponent = Link,
  rowVariant = 'full',
  seamless = false,
}: Props) {
  const showFilters = filters != null && filters.length > 1 && onFilterChange != null

  return (
    <div className={cn('nx', className)}>
      {showFilters ? (
        <div className="nx__filters">
          <div className="seg" role="tablist">
            {filters.map((filter) => {
              const active = filter.id === selectedFilterId
              return (
                <button
                  key={filter.id}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  className={cn('seg__item', active && 'is-on')}
                  onClick={() => onFilterChange(filter.id)}
                >
                  {filter.label}
                </button>
              )
            })}
          </div>
        </div>
      ) : null}

      {items.length === 0 ? (
        <div className="nx__card nx__card--empty">
          <p className="m-0 px-4 py-8 text-center font-ui text-[14px] text-v-fg-muted">{emptyMessage}</p>
        </div>
      ) : (
        <div className={cn('nx__card', seamless && 'nx__card--seamless')}>
          {items.map((item) => (
            <NewsRow
              key={item.id}
              item={item}
              LinkComponent={LinkComponent}
              rowVariant={rowVariant}
            />
          ))}
        </div>
      )}
    </div>
  )
}
