'use client'

import { Slider } from '@/components/ui/slider'
import {
  LOMBARD_MAX_USER_LTV_PERCENT,
  lombardLtvRiskLabelFr,
  lombardLtvRiskMessageFr,
  lombardLtvTrackGradient,
  resolveLombardLtvRiskTone,
} from '@/lib/portal/lombard/lombardBorrowLtv'
import { formatLombardUsdAmount } from '@/lib/portal/lombard/lombardFormat'
import type { LombardBorrowCapacity, LombardQuoteResult } from '@/lib/portal/lombard/lombardTypes'
import { cn } from '@/lib/utils'

type Props = {
  capacity: LombardBorrowCapacity
  targetLtvPercent: number
  quote: LombardQuoteResult | null
  borrowAmount: string
  onTargetLtvChange: (ltvPercent: number) => void
  onBorrowAmountChange: (amount: string) => void
  disabled?: boolean
}

const RISK_TONE_CLASS: Record<ReturnType<typeof resolveLombardLtvRiskTone>, string> = {
  idle: 'text-v-muted',
  safe: 'text-emerald-600',
  balanced: 'text-amber-600',
  risky: 'text-red-600',
}

export function PortalLombardLtvSlider({
  capacity,
  targetLtvPercent,
  quote,
  borrowAmount,
  onTargetLtvChange,
  onBorrowAmountChange,
  disabled = false,
}: Props) {
  const tone = resolveLombardLtvRiskTone(targetLtvPercent)
  const riskLabel = lombardLtvRiskLabelFr(targetLtvPercent)
  const riskMessage = lombardLtvRiskMessageFr(targetLtvPercent)

  return (
    <div className="flex flex-col gap-5">
      <div className="rounded-2xl border border-v-border bg-v-surface p-5">
        <div className="mb-4 flex items-start justify-between gap-4">
          <div>
            <p className="m-0 font-ui text-[13px] text-v-muted">Niveau de risque (LTV cible)</p>
            <p
              className={cn(
                'm-0 mt-1 font-ui text-[28px] font-semibold tabular-nums leading-none',
                RISK_TONE_CLASS[tone],
              )}
            >
              {targetLtvPercent}%
            </p>
          </div>
          <div className="text-right">
            <p className="m-0 font-ui text-[13px] text-v-muted">Maximum empruntable</p>
            <p className="m-0 mt-1 font-ui text-[22px] font-semibold tabular-nums text-v-fg">
              {formatLombardUsdAmount(capacity.maxBorrowAmount)}{' '}
              <span className="text-[14px] font-medium text-v-muted">USDC</span>
            </p>
            <p className="m-0 mt-1 font-ui text-[11px] text-v-muted">à cette LTV avec tout votre {capacity.collateral}</p>
          </div>
        </div>

        <div className="relative px-1 pb-6 pt-2">
          <div
            aria-hidden
            className="pointer-events-none absolute left-1 right-1 top-[calc(50%-2px)] h-1.5 rounded-full opacity-90"
            style={{ background: lombardLtvTrackGradient() }}
          />
          <Slider
            min={1}
            max={LOMBARD_MAX_USER_LTV_PERCENT}
            step={1}
            value={[Math.max(1, targetLtvPercent)]}
            disabled={disabled}
            onValueChange={(values) => onTargetLtvChange(values[0] ?? 1)}
            className="relative z-[1] [&_[data-slot=slider-track]]:h-2 [&_[data-slot=slider-track]]:bg-transparent [&_[data-slot=slider-range]]:bg-v-fg [&_[data-slot=slider-thumb]]:size-6 [&_[data-slot=slider-thumb]]:border-2 [&_[data-slot=slider-thumb]]:border-v-fg [&_[data-slot=slider-thumb]]:shadow-md"
          />
          <div className="mt-3 flex justify-between font-ui text-[11px] text-v-muted">
            <span>1 % · Prudent</span>
            <span>50 %</span>
            <span>70 % · Max</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-2 border-t border-v-border pt-4 font-ui text-[11px]">
          <div className="rounded-lg bg-emerald-500/10 px-2 py-2 text-center text-emerald-800">
            1–50 %<br />
            <span className="font-medium">Sécurisé</span>
          </div>
          <div className="rounded-lg bg-amber-500/10 px-2 py-2 text-center text-amber-900">
            50–60 %<br />
            <span className="font-medium">Équilibré</span>
          </div>
          <div className="rounded-lg bg-red-500/10 px-2 py-2 text-center text-red-800">
            60–70 %<br />
            <span className="font-medium">Élevé</span>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-v-border bg-v-surface p-4">
        <p className={cn('m-0 font-ui text-[15px] font-semibold', RISK_TONE_CLASS[tone])}>{riskLabel}</p>
        <p className="m-0 mt-2 font-ui text-[14px] leading-relaxed text-v-muted">{riskMessage}</p>
      </div>

      <label className="flex flex-col gap-2">
        <span className="font-ui text-[13px] text-v-muted">Montant USDC à emprunter</span>
        <input
          type="text"
          inputMode="decimal"
          value={borrowAmount}
          disabled={disabled}
          onChange={(e) => onBorrowAmountChange(e.target.value)}
          placeholder={`Ex. ${formatLombardUsdAmount(capacity.recommendedBorrowAmount)}`}
          className="rounded-xl border border-v-border bg-v-surface px-4 py-3 font-ui text-[18px] text-v-fg"
        />
        <span className="font-ui text-[12px] text-v-muted">
          Ce montant n&apos;influence pas la LTV — seule la garantie déposée s&apos;adapte.
        </span>
      </label>

      {quote ? (
        <div className="rounded-xl border border-v-border bg-v-surface p-4 font-ui text-[14px]">
          <p className="m-0 font-ui text-[13px] font-medium uppercase tracking-wide text-v-muted">Détail de l&apos;opération</p>
          <dl className="m-0 mt-3 grid gap-2">
            <div className="flex items-center justify-between gap-3">
              <dt className="text-v-muted">Vous recevrez</dt>
              <dd className="m-0 font-medium text-v-fg">{formatLombardUsdAmount(quote.borrowAmount)} USDC</dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-v-muted">Garantie déposée sur Morpho</dt>
              <dd className="m-0 font-medium text-v-fg">
                {quote.guaranteeAmount} {quote.collateral}
              </dd>
            </div>
            <div className="flex items-center justify-between gap-3">
              <dt className="text-v-muted">{capacity.collateral} restant dans le wallet</dt>
              <dd className="m-0 font-medium text-v-fg">
                {formatWalletRemainder(capacity.walletGuaranteeBalance, quote.guaranteeAmount)} {capacity.collateral}
              </dd>
            </div>
          </dl>
        </div>
      ) : null}

      <p className="m-0 font-ui text-[13px] leading-relaxed text-v-muted">
        Plus la LTV est élevée, moins de {capacity.collateral} est nécessaire par USDC emprunté — mais la position
        est plus sensible aux baisses de marché. Vous conservez votre exposition au {capacity.collateralName}.
      </p>
    </div>
  )
}

function formatWalletRemainder(walletBalance: string, guaranteeAmount: string): string {
  const wallet = Number(String(walletBalance).replace(',', '.'))
  const locked = Number(String(guaranteeAmount).replace(',', '.'))
  if (!Number.isFinite(wallet) || !Number.isFinite(locked)) return walletBalance
  const remainder = Math.max(0, wallet - locked)
  if (remainder >= 1) return String(Math.round(remainder * 1_000_000) / 1_000_000).replace(/\.?0+$/, '')
  return String(remainder)
}
