'use client'

import { ChevronRight } from 'lucide-react'
import type { PortalWalletRow } from '@/lib/portal/dashboardTypes'
import { portalWalletIcon, portalWalletIconToneClass } from '@/components/portal/dashboard/portalWalletIcons'
import { cn } from '@/lib/utils'

type Props = {
  rows: PortalWalletRow[]
  title?: string
}

export function PortalAccountsCard({ rows, title = 'My accounts' }: Props) {
  return (
    <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
      <div className="border-b border-v-fg-10 px-4 py-3">
        <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">{title}</h2>
      </div>
      <ul className="m-0 list-none p-0">
        {rows.map((row) => {
          const Icon = portalWalletIcon(row.iconKey)
          return (
            <li key={row.id}>
              <button
                type="button"
                className="flex w-full items-center gap-3 px-4 py-3.5 text-left transition-colors duration-v-fast hover:bg-v-card-hover"
              >
                <span
                  className={cn(
                    'inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-v-input',
                    portalWalletIconToneClass(row.iconTone),
                  )}
                >
                  <Icon className="h-5 w-5" strokeWidth={1.75} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-ui text-[15px] font-semibold text-v-fg">{row.title}</span>
                  <span className="mt-0.5 block truncate font-ui text-[13px] text-v-fg-muted">
                    {row.subtitle}
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-1">
                  <span className="font-ui text-[15px] font-semibold tabular-nums text-v-fg">
                    {row.balance}
                  </span>
                  <ChevronRight className="h-4 w-4 text-v-fg-muted" aria-hidden />
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </article>
  )
}
