'use client'

import * as React from 'react'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { Container } from '@/components/ui/Container'
import { VEditorialTitle } from './VEditorialTitle'
import { parseEditorialTitle } from '@/lib/cms/parseEditorialTitle'

export interface VSecurityPoint {
  text: string
}

export interface VSecurityLogo {
  label: string
  caption?: string
}

export interface VSecurityProps {
  eyebrow?: string
  title?: string
  description?: string
  points?: VSecurityPoint[]
  linkText?: string
  linkHref?: string
  logos?: VSecurityLogo[]
  className?: string
}

function CheckIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="mt-0.5 h-4 w-4 shrink-0 text-v-fg"
      aria-hidden
    >
      <path d="M4 12l5 5 11-11" />
    </svg>
  )
}

/** Section sécurité & régulation DS (`security`). */
export function VSecurity({
  eyebrow,
  title,
  description,
  points = [],
  linkText,
  linkHref,
  logos = [],
  className,
}: VSecurityProps) {
  const titleNode = title ? parseEditorialTitle(title) : null
  const pointList = points.filter((p) => p.text?.trim())
  const logoList = logos.filter((l) => l.label?.trim())

  return (
    <section className={cn('w-full bg-v-bg py-24 lg:py-32', className)}>
      <Container>
        <div data-v-scroll-fade className="grid grid-cols-1 items-start gap-16 lg:grid-cols-2 lg:gap-20">
          <div className="flex flex-col gap-6">
            {eyebrow?.trim() ? (
              <p className="m-0 font-ui text-[11px] font-medium uppercase tracking-[0.05em] text-v-fg-muted">
                {eyebrow}
              </p>
            ) : null}

            {titleNode ? (
              <VEditorialTitle as="h2" size="module" tone="default">
                {titleNode}
              </VEditorialTitle>
            ) : null}

            {description?.trim() ? (
              <p className="m-0 max-w-[520px] font-ui text-[16px] font-normal leading-[1.55] text-v-fg-body">
                {description}
              </p>
            ) : null}

            {pointList.length > 0 ? (
              <ul className="m-0 flex list-none flex-col gap-3 p-0">
                {pointList.map((p, i) => (
                  <li key={i} className="flex items-start gap-2.5 font-ui text-[14px] leading-[1.45] text-v-fg-body">
                    <CheckIcon />
                    <span>{p.text}</span>
                  </li>
                ))}
              </ul>
            ) : null}

            {linkText?.trim() && linkHref?.trim() ? (
              <Link
                href={linkHref}
                className="inline-flex items-center gap-1 font-ui text-[14px] font-semibold text-v-terracotta no-underline transition-colors duration-v-fast ease-v-out hover:underline hover:underline-offset-[3px]"
              >
                <span>{linkText}</span>
                <span aria-hidden>→</span>
              </Link>
            ) : null}
          </div>

          {logoList.length > 0 ? (
            <div className="grid grid-cols-2 gap-4 sm:gap-5">
              {logoList.map((logo, i) => (
                <div
                  key={i}
                  className="flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-v-card border border-v-fg-10 bg-[rgba(26,24,21,0.025)] px-4 py-6 text-center shadow-v-subtle"
                >
                  <span className="font-ui text-[22px] font-bold tracking-[0.04em] text-v-fg">
                    {logo.label}
                  </span>
                  {logo.caption?.trim() ? (
                    <p className="m-0 font-ui text-[12px] font-normal leading-[1.35] text-v-fg-muted">
                      {logo.caption}
                    </p>
                  ) : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </Container>
    </section>
  )
}
