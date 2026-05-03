import { Fragment } from 'react'

import { SectionFigmaBlockHeader } from '@/components/sections/SectionFigmaBlockHeader'
import { cn } from '@/lib/utils'
import {
  figmaDsLabelEmphasizedSmClassName,
  figmaDsParagraphClassName,
  figmaDsParagraphLargeBoldClassName,
} from '@/components/design-system/extracted/tokens/typography'

const DOT = 20
/** Centrage horizontal du filet (2px) dans la colonne 20px. */
const LINE_LEFT_PX = (DOT - 2) / 2
/**
 * Haut du filet : centre vertical du 1er disque (rangée `items-center`, hauteur = ligne Paragraph Large Bold 18px × 1,6).
 * Évite que le pointillé dépasse au-dessus de l’avatar.
 */
const FIRST_STEP_LINE_TOP = 'calc(1.8rem / 2)'
/**
 * Bas de la pastille (h-5) centrée verticalement sur la 1ʳᵉ ligne titre = Paragraph Large Bold (18px × 1,6 = 1,8 rem de hauteur de ligne).
 * Masque du filet sous la dernière pastille : commence pile sous le disque.
 */
const LAST_STEP_LINE_MASK_TOP = 'calc((1.8rem + 1.25rem) / 2)'

export type ArticleStepsItemData = {
  dayLabel?: string
  date?: string
  title: string
  description?: string
  tags?: string[]
  isCompleted?: boolean
}

export type ArticleStepsContent = {
  title?: string
  /** Surtitre (pastille / eyebrow) — centré, au-dessus du titre de module. */
  subtitle?: string
  /** Texte d’intro sous le titre (aligné modules Vault : centré, corps 18px). */
  description?: string
  rightLabel?: string
  items: ArticleStepsItemData[]
}

type StepStatus = 'completed' | 'active' | 'upcoming'

function resolveStatuses(steps: ArticleStepsItemData[]): StepStatus[] {
  const firstPending = steps.findIndex((s) => !s.isCompleted)
  return steps.map((s, i) => {
    if (s.isCompleted) return 'completed' as const
    if (firstPending === -1) return 'completed' as const
    if (i === firstPending) return 'active' as const
    return 'upcoming' as const
  })
}

function parseItems(raw: unknown): ArticleStepsItemData[] {
  if (!Array.isArray(raw)) return []
  const out: ArticleStepsItemData[] = []
  for (const it of raw) {
    if (it == null || typeof it !== 'object' || Array.isArray(it)) continue
    const o = it as Record<string, unknown>
    const title = typeof o.title === 'string' ? o.title.trim() : ''
    if (!title) continue
    const tagsRaw = o.tags
    const tags =
      tagsRaw instanceof Array
        ? tagsRaw.map((e) => String(e ?? '')).filter((s) => s.length > 0)
        : []
    out.push({
      dayLabel: typeof o.dayLabel === 'string' ? o.dayLabel : undefined,
      date: typeof o.date === 'string' ? o.date : undefined,
      title,
      description: typeof o.description === 'string' ? o.description : undefined,
      tags,
      isCompleted: o.isCompleted === true,
    })
  }
  return out
}

function CompletedDot() {
  return (
    <div
      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-fuchsia-400 via-orange-400 to-amber-300 shadow-sm"
      aria-hidden
    >
      <svg
        className="h-3 w-3 text-white"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2.5}
        aria-hidden
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
      </svg>
    </div>
  )
}

function ActiveDot() {
  return (
    <div
      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full border-2 border-black bg-white"
      aria-hidden
    >
      <svg
        className="h-3.5 w-3.5 animate-spin text-black"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden
      >
        <path
          d="M12 2a10 10 0 0 0-10 10"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
    </div>
  )
}

function UpcomingDot() {
  return (
    <div
      className="h-5 w-5 shrink-0 rounded-full border border-black bg-white"
      aria-hidden
    />
  )
}

function StepDot({ status }: { status: StepStatus }) {
  switch (status) {
    case 'completed':
      return <CompletedDot />
    case 'active':
      return <ActiveDot />
    default:
      return <UpcomingDot />
  }
}

type Props = {
  content: Record<string, unknown>
  className?: string
  activeLabel?: string
}

/**
 * Titre de module, surtitre et description **hors** du fond #f0f0f0 (aligné `SectionFigmaBlockHeader`) ;
 * zone grise = timeline. Rangée titre + pastille : `items-center` (pastille centrée sur la hauteur de ligne du titre, 18px / lh 1,6).
 * Masque sous dernière pastille : `top` = bas du disque centré (`LAST_STEP_LINE_MASK_TOP`).
 */
export function ArticleStepsModule({ content, className, activeLabel = 'EN COURS' }: Props) {
  const c = content || {}
  const title = typeof c.title === 'string' ? c.title.trim() : ''
  const subtitle = typeof c.subtitle === 'string' ? c.subtitle.trim() : ''
  const intro = typeof c.description === 'string' ? c.description.trim() : ''
  const rightLabel = typeof c.rightLabel === 'string' ? c.rightLabel.trim() : ''
  const items = parseItems(c.items)
  if (items.length === 0) return null

  const statuses = resolveStatuses(items)

  const hasModuleHeader = Boolean(subtitle || title || intro)

  return (
    <div className={cn('w-full', className)}>
      {hasModuleHeader ? (
        <SectionFigmaBlockHeader
          className="!mb-8 md:!mb-10"
          eyebrow={subtitle || undefined}
          title={title || undefined}
          description={intro || undefined}
        />
      ) : null}
      {rightLabel ? (
        <p
          className={cn(
            figmaDsParagraphClassName,
            'm-0 mb-6 text-center text-[#62656e]',
            hasModuleHeader && '-mt-1 md:-mt-2',
          )}
        >
          {rightLabel}
        </p>
      ) : null}

      <div
        className={cn(
          'overflow-visible rounded-2xl bg-[#f0f0f0] p-10 shadow-[0_8px_24px_rgba(0,0,0,0.04)]',
        )}
      >
        <div className="relative min-h-0 overflow-visible">
        {/* Ligne : un seul segment top→bottom, dans les 32px entre étapes sans discontinuité. */}
        <div
          className="pointer-events-none absolute bottom-0 z-0 w-0 border-l-2 border-dotted border-l-[#b0b4bd] border-t-0 border-r-0 border-b-0"
          style={{ left: `${LINE_LEFT_PX}px`, top: FIRST_STEP_LINE_TOP, bottom: 0 }}
          aria-hidden
        />

        <div className="relative z-10 flex min-h-0 flex-col gap-8 overflow-visible">
          {items.map((step, i) => {
            const isLast = i === items.length - 1
            const status = statuses[i]!
            const date = step.date?.trim() ?? ''
            const desc = step.description?.trim() ?? ''
            return (
              <Fragment key={i}>
                <div className="relative overflow-visible">
                  <div className="flex items-center gap-[16px] overflow-visible">
                    <div
                      className="relative z-30 box-border flex h-5 w-5 min-w-[20px] max-w-[20px] shrink-0 flex-col items-center justify-center overflow-visible bg-[#f0f0f0]"
                      aria-hidden
                    >
                      <StepDot status={status} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <p className={cn(figmaDsParagraphLargeBoldClassName, 'm-0 text-black')}>
                          {step.title}
                        </p>
                        {status === 'active' ? (
                          <span
                            className={cn(
                              figmaDsLabelEmphasizedSmClassName,
                              'inline-block rounded-sm bg-white px-1.5 py-1 align-middle',
                            )}
                          >
                            {activeLabel}
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  {isLast ? (
                    <div
                      className="pointer-events-none absolute bottom-0 left-0 z-10 w-5 bg-[#f0f0f0]"
                      style={{ top: LAST_STEP_LINE_MASK_TOP }}
                      aria-hidden
                    />
                  ) : null}
                  {date || desc ? (
                    <div className="mt-1 space-y-1 pl-9">
                      {date ? (
                        <p
                          className={cn(
                            figmaDsParagraphClassName,
                            'm-0 text-[#62656e]',
                          )}
                        >
                          {date}
                        </p>
                      ) : null}
                      {desc ? (
                        <p
                          className={cn(
                            figmaDsParagraphClassName,
                            'm-0 text-[#62656e]',
                          )}
                        >
                          {desc}
                        </p>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              </Fragment>
            )
          })}
        </div>
      </div>
      </div>
    </div>
  )
}
