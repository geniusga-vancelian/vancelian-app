'use client'

import { useEffect, useMemo, useRef, useState } from 'react'

import { KalaiIcon } from '@/components/ui/KalaiIcon'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import {
  computeReceivedParts,
  defaultInvestSources,
  invFmtAmount,
  invInEur,
  invParseAmount,
  buildLockedInvestSource,
  mergeSourceBalance,
  resolveBaseUsdcBalance,
  resolveEurcBalance,
  resolveInvestSourceKeyFromAssetSymbol,
  type PortalInvestSource,
  type PortalInvestTarget,
} from '@/lib/portal/portalInvestFlowFormat'
import { PortalInvestFlowDom } from '@/components/portal/invest/PortalInvestFlowDom'
import {
  PortalInvestChip,
  PortalInvestSelector,
} from '@/components/portal/invest/PortalInvestFlowParts'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type InvestMode = 'invest' | 'withdraw'

type InvestFlowProps = {
  onClose: () => void
  initialTargetKey?: string
  /** Pre-built target (exclusive offer detail). */
  vaultTarget?: PortalInvestTarget
  /** Actif ERC-4626 imposé (USDC / EURC) — verrouille la source, sans sélecteur. */
  depositAssetSymbol?: string | null
  initialMode?: InvestMode
}

function InvestGain({
  label,
  value,
  suffix,
  pulseKey,
}: {
  label: string
  value: string
  suffix: string
  pulseKey: number
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!ref.current) return
    ref.current.classList.remove('pulse')
    void ref.current.offsetWidth
    ref.current.classList.add('pulse')
  }, [pulseKey])

  return (
    <div ref={ref} className="inv-gain">
      <span className="inv-gain__label">{label}</span>
      <span className="inv-gain__value">
        + {value} {suffix}
      </span>
    </div>
  )
}

function InvestTech({
  source,
  target,
  pricePart,
}: {
  source: PortalInvestSource
  target: PortalInvestTarget
  pricePart: number
}) {
  const [open, setOpen] = useState(false)

  return (
    <>
      <button
        type="button"
        className={`inv-tech-toggle${open ? ' is-open' : ''}`}
        onClick={() => setOpen((v) => !v)}
      >
        Technical details
        <span className="inv-tech-toggle__arrow" aria-hidden="true">
          <KalaiIcon name="chevron-down" size={16} />
        </span>
      </button>
      {open ? (
        <div className="inv-tech">
          <div className="inv-tech__row">
            <span className="inv-tech__k">Price per share</span>
            <span className="inv-tech__v">{invFmtAmount(pricePart, 2)} €</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Execution time</span>
            <span className="inv-tech__v">Instant</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Network</span>
            <span className="inv-tech__v">Polygon</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Source asset</span>
            <span className="inv-tech__v">{source.techSource}</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Received asset</span>
            <span className="inv-tech__v">{target.tech}</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Network fees</span>
            <span className="inv-tech__v">Covered by Vancelian</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Signature</span>
            <span className="inv-tech__v">MPC custody</span>
          </div>
        </div>
      ) : null}
    </>
  )
}

function InvestForm({
  amount,
  setAmount,
  source,
  target,
  sources,
  targets,
  popSource,
  popTarget,
  mode,
  onOpenSelector,
  onClose,
}: {
  amount: string
  setAmount: (value: string) => void
  source: PortalInvestSource
  target: PortalInvestTarget
  sources: PortalInvestSource[]
  targets: PortalInvestTarget[]
  popSource: number
  popTarget: number
  mode: InvestMode
  onOpenSelector: (field: 'from' | 'to') => void
  onClose: () => void
}) {
  const isInvest = mode === 'invest'
  const numeric = invParseAmount(amount)
  const amountEur = invInEur(numeric, source)
  const received = computeReceivedParts(amountEur, target)
  const rate = target.yieldPct
  const daily = amountEur * rate / 365
  const monthly = amountEur * rate / 12
  const yearly = amountEur * rate
  const maxAmt = source.balance
  const sliderVal = Math.max(0, Math.min(maxAmt, numeric))
  const fillPct = maxAmt > 0 ? (sliderVal / maxAmt) * 100 : 0
  const sym = source.glyph

  const setAmt = (value: number) => {
    setAmount(invFmtAmount(Math.round(value)))
  }

  const verb = isInvest ? 'Invest' : 'Withdraw'
  const ctaLabel = numeric > 0 ? `${verb} ${invFmtAmount(numeric)} ${sym}` : 'Enter an amount'
  const disabled = numeric <= 0 || numeric > source.balance + 1e-3
  const [pulseKey, setPulseKey] = useState(0)

  useEffect(() => {
    setPulseKey((k) => k + 1)
  }, [amount, target.key, source.key, mode])

  const topLabel = isInvest ? 'I invest' : 'I withdraw from'
  const bottomLabel = isInvest ? 'I receive' : 'I receive on'
  const canPickSource = sources.length > 1
  const canPickTarget = targets.length > 1

  return (
    <div className="inv-pane">
      <header className="inv-head">
        <h2 className="inv-head__title">{isInvest ? 'Invest' : 'Withdraw'}</h2>
        <div className="inv-head__actions">
          <button type="button" className="inv-head__btn" onClick={onClose} aria-label="Close">
            <KalaiIcon name="close" size={16} />
          </button>
        </div>
      </header>

      <div className="inv-iowrap">
        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">{isInvest ? topLabel : bottomLabel}</span>
            <span className="inv-io__balance">
              {source.balanceLabel}
              <button type="button" className="inv-io__max" onClick={() => setAmt(source.balance)}>
                Max
              </button>
            </span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              inputMode="numeric"
              className="inv-io__amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              aria-label="Amount to invest"
            />
            <PortalInvestChip
              asset={source}
              popKey={popSource}
              selectable={canPickSource}
              onClick={() => onOpenSelector('from')}
            />
          </div>
        </div>

        <div className="inv-divider" aria-hidden="true" />

        <div className="inv-io">
          <div className="inv-io__top">
            <span className="inv-io__label">{isInvest ? bottomLabel : topLabel}</span>
            <span className="inv-io__balance">
              {target.held} {target.heldLabel}
            </span>
          </div>
          <div className="inv-io__row">
            <input
              type="text"
              className="inv-io__amount"
              value={invFmtAmount(received, received >= 100 ? 0 : 2)}
              readOnly
              aria-label="Estimated shares received"
            />
            <PortalInvestChip
              asset={target}
              popKey={popTarget}
              selectable={canPickTarget}
              onClick={() => onOpenSelector('to')}
            />
          </div>
        </div>
      </div>

      {isInvest ? (
        <div className="inv-sim">
          <div className="inv-sim__head">
            <span className="inv-sim__label">Quick simulation</span>
            <span className="inv-sim__hint">
              {invFmtAmount(numeric)} {sym} of {invFmtAmount(source.balance)} {sym}
            </span>
          </div>
          <input
            type="range"
            className="inv-range"
            min={0}
            max={maxAmt}
            step={Math.max(1, Math.round(maxAmt / 1000))}
            value={sliderVal}
            onChange={(e) => setAmt(Number(e.target.value))}
            style={{ ['--inv-fill' as string]: `${fillPct}%` }}
            aria-label="Amount to invest"
          />
          <div className="inv-gains">
            <InvestGain label="Daily" value={invFmtAmount(daily, 2)} suffix="€" pulseKey={pulseKey} />
            <InvestGain label="Monthly" value={invFmtAmount(monthly, 0)} suffix="€" pulseKey={pulseKey} />
            <InvestGain label="Yearly" value={invFmtAmount(yearly, 0)} suffix="€" pulseKey={pulseKey} />
          </div>
        </div>
      ) : null}

      <div className="inv-summary">
        <div className="inv-summary__row">
          <span className="k">Vancelian fees</span>
          <span className="v v--accent">Waived</span>
        </div>
        <div className="inv-summary__row">
          <span className="k">Target yield</span>
          <span className="v">
            {(rate * 100).toLocaleString('en-US', {
              minimumFractionDigits: 1,
              maximumFractionDigits: 1,
            })}
            %/yr
          </span>
        </div>
      </div>

      <button type="button" className="btn btn--primary btn--lg inv-cta" disabled={disabled}>
        {ctaLabel}
      </button>

      <InvestTech source={source} target={target} pricePart={target.pricePerPart} />
    </div>
  )
}

/**
 * Invest / withdraw flow — handoff `InvestFlow` (`invest-flow.js` · `invest.css`).
 * Embedded in `.ofd-invest-panel` (Offre.html) or `.v-card` (Portfolio.html).
 */
export function PortalInvestFlow({
  onClose,
  initialTargetKey,
  vaultTarget,
  depositAssetSymbol,
  initialMode = 'invest',
}: InvestFlowProps) {
  const lockedAssetSymbol = depositAssetSymbol?.trim().toUpperCase() || 'USDC'

  const targets = useMemo(
    () => (vaultTarget ? [vaultTarget] : []),
    [vaultTarget],
  )

  const [sources, setSources] = useState<PortalInvestSource[]>(() =>
    depositAssetSymbol
      ? [buildLockedInvestSource(lockedAssetSymbol, 0)]
      : defaultInvestSources(),
  )
  const [source, setSource] = useState<PortalInvestSource>(() =>
    depositAssetSymbol
      ? buildLockedInvestSource(lockedAssetSymbol, 0)
      : defaultInvestSources()[0]!,
  )
  const initialTarget =
    (initialTargetKey && targets.find((t) => t.key === initialTargetKey)) || targets[0] || null
  const [target, setTarget] = useState<PortalInvestTarget | null>(initialTarget)
  const mode: InvestMode = initialMode === 'withdraw' ? 'withdraw' : 'invest'
  const [amount, setAmount] = useState(() => (mode === 'invest' ? '10,000' : ''))
  const [scene, setScene] = useState<'form' | 'selector'>('form')
  const [field, setField] = useState<'from' | 'to' | null>(null)
  const [popKey, setPopKey] = useState({ source: 0, target: 0 })

  const { data: walletData } = usePortalCachedScreen<PortalCryptoWalletHubPayload>({
    cacheKey: 'portal:invest-flow-balances',
    url: '/api/portal/crypto-wallet',
    ttlMs: 45_000,
    errorMessage: '',
    scopeAware: true,
  })

  useEffect(() => {
    if (!walletData?.positions?.positions?.length) return
    const positions = walletData.positions.positions

    if (depositAssetSymbol) {
      const key = resolveInvestSourceKeyFromAssetSymbol(lockedAssetSymbol)
      const balance =
        key === 'eur' ? resolveEurcBalance(positions) : resolveBaseUsdcBalance(positions)
      const next = buildLockedInvestSource(lockedAssetSymbol, balance)
      setSources([next])
      setSource(next)
      return
    }

    setSources((prev) => {
      const usdc = resolveBaseUsdcBalance(positions)
      const eur = resolveEurcBalance(positions)
      let next = mergeSourceBalance(prev, 'usdc', usdc)
      next = mergeSourceBalance(next, 'eur', eur)
      setSource((current) => next.find((s) => s.key === current.key) ?? next[0]!)
      return next
    })
  }, [depositAssetSymbol, lockedAssetSymbol, walletData])

  useEffect(() => {
    if (!initialTargetKey || !targets.length) return
    const next = targets.find((t) => t.key === initialTargetKey)
    if (next) {
      setTarget(next)
      setPopKey((p) => ({ ...p, target: p.target + 1 }))
    }
  }, [initialTargetKey, targets])

  if (!target) return null

  const openSelector = (f: 'from' | 'to') => {
    if (f === 'from' && sources.length <= 1) return
    if (f === 'to' && targets.length <= 1) return
    setField(f)
    setScene('selector')
  }

  const closeSelector = () => {
    setScene('form')
  }

  const pickAsset = (asset: PortalInvestSource | PortalInvestTarget) => {
    if (field === 'from') {
      setSource(asset as PortalInvestSource)
      setPopKey((p) => ({ ...p, source: p.source + 1 }))
    } else {
      setTarget(asset as PortalInvestTarget)
      setPopKey((p) => ({ ...p, target: p.target + 1 }))
    }
    closeSelector()
  }

  return (
    <PortalInvestFlowDom
      scene={scene}
      form={
        <InvestForm
          amount={amount}
          setAmount={setAmount}
          source={source}
          target={target}
          sources={sources}
          targets={targets}
          popSource={popKey.source}
          popTarget={popKey.target}
          mode={mode}
          onOpenSelector={openSelector}
          onClose={onClose}
        />
      }
      selector={
        scene === 'selector' && field ? (
          <PortalInvestSelector
            field={field}
            source={source}
            target={target}
            sources={sources}
            targets={targets}
            onPick={pickAsset}
            onClose={closeSelector}
          />
        ) : null
      }
    />
  )
}
