'use client'

import { useState } from 'react'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { cn } from '@/lib/utils'

type Props = {
  totalBorrowedLabel: string
  monthlyInterestLabel: string
  borrowHref: string
  repayHref?: string
  repayDisabled?: boolean
  className?: string
}

const BORROW_CHART_PATH =
  'M0,30 L24,32 L48,30 L72,34 L96,28 L120,32 L144,36 L168,32 L192,34 L216,40 L240,44 L264,42 L288,48 L320,52'

/** Hero emprunts — handoff `BorrowHero` (`.bal--dark` · `.bal--cat` · `.bal--borrow`). */
export function AppBorrowCategoryHero({
  totalBorrowedLabel,
  monthlyInterestLabel,
  borrowHref,
  repayHref,
  repayDisabled = true,
  className,
}: Props) {
  const [hidden, setHidden] = useState(false)
  const displayTotal = hidden ? '•\u00a0•\u00a0•\u00a0•\u00a0•\u00a0•' : totalBorrowedLabel
  const displayInterest = hidden ? '••••' : monthlyInterestLabel

  return (
    <section
      className={cn('bal bal--dark bal--cat bal--borrow w-full max-w-none', className)}
      style={{ background: 'var(--v-fg)' }}
    >
      <div className="bal__solde">
        <div className="bal__lbl">
          Total emprunté
          <button
            type="button"
            onClick={() => setHidden((value) => !value)}
            aria-label={hidden ? 'Afficher les montants' : 'Masquer les montants'}
            className="inline-flex items-center justify-center border-0 bg-transparent p-0.5 opacity-70"
          >
            <KalaiIcon name={hidden ? 'eye-off' : 'eye'} size={16} />
          </button>
        </div>
        <div className="bal__amt v-tnum" aria-live="polite">
          {displayTotal}
        </div>
        <div
          className="bal__chg !bg-transparent !px-0 !text-[13px] !font-normal"
          style={{ color: 'rgba(255,255,255,0.78)' }}
        >
          Coût d&apos;intérêt mensuel
          <span className="v-tnum" style={{ color: '#FFFFFF', marginLeft: 6 }}>
            · {displayInterest}
          </span>
        </div>
      </div>

      <div className="bal__chart" aria-hidden="true">
        <svg viewBox="0 0 320 96" preserveAspectRatio="none">
          <path
            d={BORROW_CHART_PATH}
            strokeWidth="1.5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      <div className="pt-1">
        <p className="money-phrase m-0 !text-[19px]" style={{ color: 'rgba(255,255,255,0.86)' }}>
          Vos cryptos restent à vous <span className="italic">—</span> vous empruntez en USDC dessus.
        </p>
      </div>

      <div className="bal__actions">
        <PortalNavLink href={borrowHref} className="btn btn--primary btn--lg no-underline">
          <KalaiIcon name="money-dollar" size={16} />
          Emprunter
        </PortalNavLink>
        {repayHref && !repayDisabled ? (
          <PortalNavLink href={repayHref} className="btn btn--secondary btn--lg no-underline">
            <KalaiIcon name="arrow-up" size={16} />
            Rembourser
          </PortalNavLink>
        ) : (
          <button type="button" className="btn btn--secondary btn--lg" disabled>
            <KalaiIcon name="arrow-up" size={16} />
            Rembourser
          </button>
        )}
      </div>
    </section>
  )
}
