'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalPerformanceChart } from '@/components/portal/dashboard/PortalPerformanceChart'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import { cn } from '@/lib/utils'

export type AppBalanceCardFab = {
  id: string
  label: string
  icon: string
  href?: string
  disabled?: boolean
  onClick?: () => void
}

type Props = {
  welcomeName: string
  showAvatar?: boolean
  avatarInitials?: string | null
  avatarImageUrl?: string | null
  balanceLabel: string
  balancePending?: boolean
  changeAmountLabel?: string
  changePercentLabel?: string
  changePositive?: boolean
  chartValues: number[]
  showChart?: boolean
  balanceLabelText?: string
  searchHref?: string
  notificationsHref?: string
  fabs?: AppBalanceCardFab[]
  /** `dark` = variante A anthracite · `light` = variante B warm */
  variant?: 'dark' | 'light'
  className?: string
}

const DEFAULT_FABS: AppBalanceCardFab[] = [
  { id: 'deposit', label: 'Déposer', icon: 'add', href: PORTAL_ROUTES.walletDeposit },
  { id: 'withdraw', label: 'Retirer', icon: 'send-1', disabled: true },
  { id: 'invest', label: 'Investir', icon: 'trending-up', href: PORTAL_ROUTES.invest },
  { id: 'more', label: 'More', icon: 'apps', href: PORTAL_ROUTES.profile },
]

function BalanceFab({ fab }: { fab: AppBalanceCardFab }) {
  const inner = (
    <span className="bal-v2__fab" aria-hidden>
      <KalaiIcon name={fab.icon} size={20} />
    </span>
  )

  if (fab.href && !fab.disabled) {
    return (
      <PortalNavLink href={fab.href} className="bal-v2__fb no-underline">
        {inner}
        <span className="bal-v2__fb-label">{fab.label}</span>
      </PortalNavLink>
    )
  }

  return (
    <span className="bal-v2__fb">
      <button
        type="button"
        className="bal-v2__fab"
        disabled={fab.disabled}
        aria-label={fab.label}
        onClick={fab.onClick}
      >
        <KalaiIcon name={fab.icon} size={20} />
      </button>
      <span className="bal-v2__fb-label">{fab.label}</span>
    </span>
  )
}

/**
 * Balance Card — preview/19 (`bal--dark` · `bal--light`).
 * Dashboard : variante A anthracite par défaut.
 */
export function AppBalanceCardVariantB({
  welcomeName,
  showAvatar = true,
  avatarInitials,
  avatarImageUrl,
  balanceLabel,
  balancePending = false,
  changeAmountLabel = '+ 0,00 €',
  changePercentLabel = '+ 0,0 % YTD',
  changePositive = true,
  chartValues,
  showChart = true,
  balanceLabelText = 'Solde patrimonial',
  searchHref = PORTAL_ROUTES.search,
  notificationsHref = PORTAL_ROUTES.profile,
  fabs = DEFAULT_FABS,
  variant = 'dark',
  className,
}: Props) {
  const isDark = variant === 'dark'
  const [balanceVisible, setBalanceVisible] = useState(true)

  const displayBalance = balanceVisible ? balanceLabel : '••••••'
  const displayAmount = balanceVisible ? changeAmountLabel : '••••'
  const displayPercent = balanceVisible ? changePercentLabel : '••••'

  const chartSeries = useMemo(
    () => (chartValues.length >= 2 ? chartValues : []),
    [chartValues],
  )

  return (
    <article className={cn('bal-v2', isDark ? 'bal-v2--dark' : 'bal-v2--light', className)}>
      <div className="bal-v2__tab">
        <div className="bal-v2__welcome">
          {showAvatar ? (
            <span
              className={cn(
                'avt avt--40 shrink-0',
                avatarImageUrl ? 'overflow-hidden' : isDark ? 'bal-v2__avt-initials' : 'avt--dark',
              )}
            >
              {avatarImageUrl ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={avatarImageUrl} alt="" className="h-full w-full object-cover" />
              ) : (
                avatarInitials
              )}
            </span>
          ) : null}
          <div className="bal-v2__welcome-text">
            <span className="bal-v2__welcome-hi">Welcome back</span>
            <span className="bal-v2__welcome-name">{welcomeName}</span>
          </div>
        </div>
        <div className="bal-v2__actions">
          <Link href={searchHref} className="bal-v2__ic-btn no-underline" aria-label="Recherche">
            <KalaiIcon name="search" size={18} />
          </Link>
          <Link
            href={notificationsHref}
            className="bal-v2__ic-btn no-underline"
            aria-label="Notifications"
          >
            <KalaiIcon name="bell" size={18} />
          </Link>
        </div>
      </div>

      <div className="bal-v2__solde">
        <div className="bal-v2__lbl">
          {balanceLabelText}
          <button
            type="button"
            className="bal-v2__lbl-btn"
            aria-label={balanceVisible ? 'Masquer le solde' : 'Afficher le solde'}
            onClick={() => setBalanceVisible((v) => !v)}
          >
            <KalaiIcon name={balanceVisible ? 'eye' : 'eye-off'} size={16} />
          </button>
        </div>
        {balancePending ? (
          <span className="portal-shimmer bal-v2__shimmer-amt" aria-hidden />
        ) : (
          <div className="bal-v2__amt">{displayBalance}</div>
        )}
        {!balancePending ? (
          <div
            className={cn('bal-v2__chg', !changePositive && balanceVisible && 'bal-v2__chg--neg')}
            aria-label="Performance"
          >
            {balanceVisible ? (
              changePositive ? (
                <KalaiIcon name="arrow-up" size={12} className="shrink-0" />
              ) : (
                <KalaiIcon name="arrow-down" size={12} className="shrink-0" />
              )
            ) : null}
            <span>{displayAmount}</span>
            <span className="bal-v2__chg-pct">· {displayPercent}</span>
          </div>
        ) : null}
      </div>

      {showChart && !balancePending ? (
        <div className="bal-v2__chart">
          <PortalPerformanceChart
            values={chartSeries.length >= 2 ? chartSeries : []}
            tone={isDark ? 'dark' : 'light'}
            height={120}
            strokeWidth={1.5}
            showEndpoint
            endpointLive
          />
        </div>
      ) : null}

      <div className="bal-v2__fabs">
        {fabs.map((fab) => (
          <BalanceFab key={fab.id} fab={fab} />
        ))}
      </div>
    </article>
  )
}
