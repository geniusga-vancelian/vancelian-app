'use client'

import * as React from 'react'
import {
  OfferFundingProgressCard,
  OfferFundingStatCard,
} from '@/components/design-system/offerFunding'
import { SIMPLE_MARKDOWN_MODULE_TITLE_TYPO } from '@/components/design-system'
import ReactMarkdown from 'react-markdown'
import { cn } from '@/lib/utils'

export type FundingModuleItemKey = 'progress' | 'apr' | 'target'

export type FundingModuleResolved = {
  progressPct: number
  rateDisplay: string
  totalDisplay: string
}

function itemConfig(
  items: unknown,
  key: FundingModuleItemKey,
): { enabled: boolean; label: string } {
  if (!Array.isArray(items)) return { enabled: true, label: '' }
  for (const raw of items) {
    if (raw == null || typeof raw !== 'object' || Array.isArray(raw)) continue
    const o = raw as Record<string, unknown>
    if (o.key !== key) continue
    const enabled = o.enabled !== false
    const label = typeof o.label === 'string' ? o.label.trim() : ''
    return { enabled, label }
  }
  return { enabled: true, label: '' }
}

/**
 * Bloc financement Vault — `content._resolved` enrichi côté serveur ; libellés dans `items` (JSON builder).
 */
export function VaultFundingModuleSection({ content }: { content: Record<string, unknown> }) {
  const resolved = content._resolved as FundingModuleResolved | null | undefined
  if (!resolved) {
    return null
  }

  const titleRaw = typeof content.title === 'string' ? content.title.trim() : ''
  const footnoteRaw = typeof content.footnote === 'string' ? content.footnote.trim() : ''
  const items = content.items

  const p = itemConfig(items, 'progress')
  const a = itemConfig(items, 'apr')
  const t = itemConfig(items, 'target')

  if (!p.enabled && !a.enabled && !t.enabled) {
    return null
  }

  const pct = Math.min(100, Math.max(0, Math.round(resolved.progressPct)))
  const showRemaining = p.enabled && pct < 100

  const blocks: React.ReactNode[] = []
  if (p.enabled) {
    blocks.push(
      <div key="progress" className="flex min-h-0 min-w-0 md:col-span-2">
        <OfferFundingProgressCard
          className="min-h-0 flex-1"
          percentage={pct}
          fundedLabel={p.label}
          showRemaining={showRemaining}
        />
      </div>,
    )
  }
  if (a.enabled) {
    blocks.push(
      <div key="apr" className="flex min-h-0 min-w-0">
        <OfferFundingStatCard className="flex-1" label={a.label} value={resolved.rateDisplay} />
      </div>,
    )
  }
  if (t.enabled) {
    blocks.push(
      <div key="target" className="flex min-h-0 min-w-0">
        <OfferFundingStatCard className="flex-1" label={t.label} value={resolved.totalDisplay} />
      </div>,
    )
  }

  const n = blocks.length
  const gridClass =
    n === 3
      ? 'grid size-full grid-cols-1 gap-2 md:grid-cols-4 md:items-stretch md:gap-x-2 md:gap-y-2'
      : n === 2
        ? 'grid size-full grid-cols-1 gap-2 md:grid-cols-2 md:items-stretch md:gap-2'
        : 'grid size-full grid-cols-1 gap-2'

  return (
    <div className="w-full space-y-4">
      {titleRaw ? (
        <h2 className={cn(SIMPLE_MARKDOWN_MODULE_TITLE_TYPO, 'text-center')}>{titleRaw}</h2>
      ) : null}
      <div className={gridClass}>{blocks}</div>
      {footnoteRaw ? (
        <div
          className={cn(
            'prose prose-neutral max-w-none font-ui text-[14px] text-v-fg-muted',
            'prose-p:my-2 prose-p:text-inherit',
          )}
        >
          <ReactMarkdown>{footnoteRaw}</ReactMarkdown>
        </div>
      ) : null}
    </div>
  )
}
