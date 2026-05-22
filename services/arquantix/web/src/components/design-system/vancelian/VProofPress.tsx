'use client'

import * as React from 'react'
import { cn } from '@/lib/utils'
import { Container } from '@/components/ui/Container'

export type VProofPressMarkVariant = 'bfm' | 'tribune' | 'echos' | 'finyear' | 'text'

export interface VProofPressItem {
  label: string
  variant?: VProofPressMarkVariant
}

export interface VProofPressProps {
  eyebrow?: string
  items?: VProofPressItem[]
  className?: string
}

function PressMark({ label, variant = 'text' }: VProofPressItem) {
  if (variant === 'bfm') {
    return (
      <span className="inline-flex items-center gap-1.5 font-ui text-[14px] font-bold tracking-[0.04em] text-v-fg">
        <span className="inline-flex h-6 items-center justify-center bg-v-fg px-1.5 text-[12px] font-bold tracking-[0.02em] text-v-bg">
          BFM
        </span>
        <span className="text-[13px] font-normal tracking-[0.18em]">BUSINESS</span>
      </span>
    )
  }
  if (variant === 'tribune') {
    return (
      <span className="font-editorial text-[24px] font-normal tracking-[0.01em] text-v-fg">
        {label}
      </span>
    )
  }
  if (variant === 'echos') {
    return (
      <span className="font-editorial text-[22px] font-semibold text-v-fg">{label}</span>
    )
  }
  if (variant === 'finyear') {
    return (
      <span className="font-ui text-[16px] font-bold tracking-[0.22em] text-v-fg">{label}</span>
    )
  }
  return <span className="font-ui text-[14px] font-medium text-v-fg">{label}</span>
}

/** Bandeau presse DS (`proof-bar` variante presse). */
export function VProofPress({ eyebrow, items = [], className }: VProofPressProps) {
  const list = items.filter((i) => i.label?.trim())
  if (list.length === 0 && !eyebrow?.trim()) return null

  return (
    <section className={cn('w-full bg-v-bg py-10', className)}>
      <Container>
        <div data-v-scroll-fade className="flex flex-col items-center gap-10">
          {eyebrow?.trim() ? (
            <p className="m-0 text-center font-ui font-medium text-[11px] uppercase tracking-[0.05em] text-v-fg-muted">
              {eyebrow}
            </p>
          ) : null}
          <ul className="m-0 flex list-none flex-wrap items-center justify-center gap-9 p-0 md:gap-16">
            {list.map((item, i) => (
              <li
                key={i}
                className="opacity-40 grayscale transition-opacity duration-v-base ease-v-out hover:opacity-80"
                aria-label={item.label}
              >
                <PressMark {...item} />
              </li>
            ))}
          </ul>
        </div>
      </Container>
    </section>
  )
}
