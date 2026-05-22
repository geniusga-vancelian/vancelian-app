'use client'

import { VaultModuleHeader } from '@/components/exclusive-offer/VaultModuleHeader'
import {
  VAULT_MODULE_CARD_CLASS,
  vaultStripeClass,
} from '@/components/design-system/vaultTokens'
import { cn } from '@/lib/utils'

type AllocationSlice = {
  label: string
  percentage: number
  colorHex: string
}

function readAllocationSlices(content: Record<string, unknown>): AllocationSlice[] {
  const raw = content.slices
  if (!Array.isArray(raw)) return []
  return raw.flatMap((it) => {
    if (it == null || typeof it !== 'object' || Array.isArray(it)) return []
    const row = it as Record<string, unknown>
    const label = typeof row.label === 'string' ? row.label.trim() : ''
    const percentage = Number(row.percentage)
    const colorHex = typeof row.colorHex === 'string' ? row.colorHex.trim() : 'var(--v-fg-muted)'
    if (!label || !Number.isFinite(percentage)) return []
    return [{ label, percentage, colorHex }]
  })
}

export function VaultAllocationModuleWeb({ content }: { content: Record<string, unknown> }) {
  const title = typeof content.title === 'string' ? content.title.trim() : ''
  const intro = typeof content.introText === 'string' ? content.introText.trim() : ''
  const slices = readAllocationSlices(content)
  if (!slices.length && !title) return null

  return (
    <div className={cn(VAULT_MODULE_CARD_CLASS, 'space-y-8')}>
      <VaultModuleHeader title={title || undefined} description={intro || undefined} />
      {slices.length > 0 ? (
        <div className="grid gap-6 md:grid-cols-[minmax(0,240px)_1fr] md:items-center">
          <div
            className="mx-auto aspect-square w-full max-w-[240px] rounded-full"
            style={{
              background: `conic-gradient(${slices
                .reduce<{ parts: string[]; cursor: number }>(
                  (acc, slice) => {
                    const start = acc.cursor
                    const end = acc.cursor + slice.percentage
                    acc.parts.push(`${slice.colorHex} ${start}% ${end}%`)
                    acc.cursor = end
                    return acc
                  },
                  { parts: [], cursor: 0 },
                )
                .parts.join(', ')})`,
            }}
            aria-hidden
          />
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {slices.map((slice, i) => (
              <li key={`${slice.label}-${i}`} className="flex items-center justify-between gap-4">
                <span className="flex min-w-0 items-center gap-3 font-ui text-[15px] text-v-fg">
                  <span
                    className="h-3 w-3 shrink-0 rounded-full"
                    style={{ backgroundColor: slice.colorHex }}
                    aria-hidden
                  />
                  <span className="truncate">{slice.label}</span>
                </span>
                <span className="shrink-0 font-ui text-[15px] font-semibold text-v-fg">
                  {slice.percentage.toFixed(1)}%
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}

export function VaultPerformanceChartWeb({ content }: { content: Record<string, unknown> }) {
  const title = typeof content.title === 'string' ? content.title.trim() : ''
  const resolved = content._resolved as { points?: Array<{ label?: string; value?: number }> } | null
  const points = Array.isArray(resolved?.points) ? resolved!.points! : []

  if (!title && points.length === 0) return null

  const max = points.reduce((m, p) => Math.max(m, Number(p.value) || 0), 0) || 1

  return (
    <div className={cn(VAULT_MODULE_CARD_CLASS, 'space-y-6')}>
      <VaultModuleHeader title={title || undefined} />
      {points.length > 0 ? (
        <div className="flex h-48 items-end gap-2 border-b border-v-fg-10 pb-2">
          {points.map((point, i) => {
            const value = Number(point.value) || 0
            const heightPct = Math.max(4, (value / max) * 100)
            return (
              <div key={i} className="flex min-w-0 flex-1 flex-col items-center gap-2">
                <div
                  className="w-full max-w-[48px] rounded-t-v-input bg-v-green"
                  style={{ height: `${heightPct}%` }}
                  title={String(value)}
                />
                {point.label ? (
                  <span className="truncate font-ui text-[11px] text-v-fg-muted">{point.label}</span>
                ) : null}
              </div>
            )
          })}
        </div>
      ) : null}
    </div>
  )
}

export function VaultTransactionLatestModuleWeb({ content }: { content: Record<string, unknown> }) {
  const title = typeof content.title === 'string' ? content.title.trim() : ''
  const resolved = content._resolved as { rows?: Array<{ label?: string; amount?: string; date?: string }> } | null
  const rows = Array.isArray(resolved?.rows) ? resolved!.rows! : []

  if (!title && rows.length === 0) return null

  return (
    <div className={cn(VAULT_MODULE_CARD_CLASS, 'overflow-hidden p-0')}>
      {title ? (
        <div className="border-b border-v-fg-10 px-6 py-5 md:px-8">
          <h2 className="m-0 font-ui text-[clamp(22px,2.5vw,28px)] font-semibold text-v-fg">
            {title}
          </h2>
        </div>
      ) : null}
      {rows.length > 0 ? (
        <ul className="m-0 list-none p-0">
          {rows.map((row, i) => (
            <li
              key={i}
              className={cn(
                'flex items-center justify-between gap-4 px-6 py-4 md:px-8',
                vaultStripeClass(i),
              )}
            >
              <div className="min-w-0">
                <p className="m-0 truncate font-ui text-[15px] font-medium text-v-fg">
                  {row.label ?? '—'}
                </p>
                {row.date ? (
                  <p className="m-0 mt-1 font-ui text-[13px] text-v-fg-muted">{row.date}</p>
                ) : null}
              </div>
              {row.amount ? (
                <span className="shrink-0 font-ui text-[15px] font-semibold text-v-fg">
                  {row.amount}
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
