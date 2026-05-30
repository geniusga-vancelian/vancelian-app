import type { ComponentType, ReactNode } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { cn } from '@/lib/utils'

export type AppLoanSafety = 'ok' | 'warn' | 'error'

type LinkLikeProps = {
  href: string
  className?: string
  children: ReactNode
}

export type AppLoanCardStat = {
  label: ReactNode
  value: ReactNode
}

type Props = {
  assetTitle: string
  collateralSubtitle: string
  collateralIconUrl?: string
  stats: AppLoanCardStat[]
  trailingStats?: AppLoanCardStat[]
  safety?: AppLoanSafety
  safetyLabel?: string
  usagePercent?: number
  alertAtPercent?: number
  href?: string
  onClick?: () => void
  LinkComponent?: ComponentType<LinkLikeProps>
  className?: string
}

function safetyTone(safety: AppLoanSafety) {
  if (safety === 'error') {
    return { color: 'var(--v-error)', bg: 'var(--v-error-bg)', fill: 'var(--v-error)' }
  }
  if (safety === 'warn') {
    return {
      color: 'var(--v-yellow-pressed)',
      bg: 'var(--v-yellow-bg)',
      fill: 'var(--v-yellow-pressed)',
    }
  }
  return { color: 'var(--v-green)', bg: 'var(--v-success-bg)', fill: 'var(--v-green)' }
}

function LoanSafetyTag({ safety, label }: { safety: AppLoanSafety; label: string }) {
  const tone = safetyTone(safety)
  return (
    <span className="loan__safety" style={{ color: tone.color, background: tone.bg }}>
      <span className="loan__safety-dot" style={{ background: tone.color }} />
      {label}
    </span>
  )
}

/** Carte emprunt actif — `.loan` (Webapp-full category-detail). */
export function AppLoanCard({
  assetTitle,
  collateralSubtitle,
  collateralIconUrl,
  stats,
  trailingStats,
  safety,
  safetyLabel,
  usagePercent,
  alertAtPercent,
  href,
  onClick,
  LinkComponent,
  className,
}: Props) {
  const LinkImpl = LinkComponent ?? Link
  const usageFill =
    usagePercent != null
      ? {
          width: `${Math.max(0, Math.min(100, usagePercent))}%`,
          background: safetyTone(safety ?? 'ok').fill,
        }
      : undefined

  const inner = (
    <>
      <header className="loan__head">
        <span className="loan__coin" aria-hidden="true">
          {collateralIconUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={collateralIconUrl} alt="" />
          ) : null}
        </span>
        <div className="loan__title-block">
          <h4 className="loan__title">{assetTitle}</h4>
          <p className="loan__sub v-tnum">{collateralSubtitle}</p>
        </div>
        <span className="loan__chv" aria-hidden="true">
          <KalaiIcon name="chevron-right" size={20} />
        </span>
      </header>
      <dl className="loan__stats">
        {stats.map((row, i) => (
          <div key={`head-${i}`} className="loan__row">
            <dt>{row.label}</dt>
            <dd className={typeof row.value === 'string' ? 'v-tnum' : undefined}>
              {row.value}
            </dd>
          </div>
        ))}
        {safety && safetyLabel ? (
          <div className="loan__row">
            <dt>Niveau de sécurité</dt>
            <dd>
              <LoanSafetyTag safety={safety} label={safetyLabel} />
            </dd>
          </div>
        ) : null}
        {usagePercent != null ? (
          <div className="loan__row">
            <dt>Utilisation actuelle</dt>
            <dd className="v-tnum">
              <span className="loan__usage">
                <span className="loan__usage-bar">
                  <span className="loan__usage-fill" style={usageFill} />
                </span>
                <span>{usagePercent}&nbsp;%</span>
              </span>
            </dd>
          </div>
        ) : null}
        {trailingStats?.map((row, i) => (
          <div key={`tail-${i}`} className="loan__row">
            <dt>{row.label}</dt>
            <dd className={typeof row.value === 'string' ? 'v-tnum' : undefined}>
              {row.value}
            </dd>
          </div>
        ))}
        {alertAtPercent != null ? (
          <div className="loan__row">
            <dt>
              <KalaiIcon name="bell" size={16} className="loan__alert-ic" />
              Je reçois une alerte à
            </dt>
            <dd className="v-tnum">{alertAtPercent}&nbsp;%</dd>
          </div>
        ) : null}
      </dl>
    </>
  )

  const cardClass = cn('loan', className)

  if (href) {
    return (
      <LinkImpl href={href} className={cn('v-card', cardClass)}>
        {inner}
      </LinkImpl>
    )
  }

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn('v-card', cardClass)}>
        {inner}
      </button>
    )
  }

  return <article className={cn('v-card', cardClass)}>{inner}</article>
}
