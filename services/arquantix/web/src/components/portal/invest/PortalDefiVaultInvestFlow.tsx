'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { PortalInvestFlowDom } from '@/components/portal/invest/PortalInvestFlowDom'
import {
  PortalInvestChip,
  PortalInvestSelector,
} from '@/components/portal/invest/PortalInvestFlowParts'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { Button } from '@/components/ui/button'
import { fetchPortalLedgityPosition } from '@/lib/portal/ledgity/ledgityVaultClient'
import type {
  PortalLedgityBetaPortalFlags,
  PortalLedgityVaultDetails,
  PortalLedgityVaultPosition,
} from '@/lib/portal/ledgity/ledgityVaultTypes'
import { fetchPortalMorphoPosition } from '@/lib/portal/morphoVaultClient'
import type {
  PortalMorphoBetaPortalFlags,
  PortalMorphoVaultDetails,
  PortalMorphoVaultPosition,
} from '@/lib/portal/morphoVaultTypes'
import type { PortalCryptoWalletHubPayload } from '@/lib/portal/cryptoWalletTypes'
import {
  buildDefiVaultInvestTarget,
  defaultInvestSources,
  invFmtAmount,
  invParseAmount,
  mergeSourceBalance,
  parseVaultPositionAmount,
  resolveVaultDepositUsdcBalance,
  type PortalInvestSource,
  type PortalInvestTarget,
} from '@/lib/portal/portalInvestFlowFormat'
import {
  type PortalLedgityExecutionPhase,
  usePortalLedgityVaultExecution,
} from '@/lib/portal/usePortalLedgityVaultExecution'
import {
  type PortalMorphoExecutionPhase,
  usePortalMorphoVaultExecution,
} from '@/lib/portal/usePortalMorphoVaultExecution'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'

type InvestMode = 'invest' | 'withdraw'

type DefiVault = PortalMorphoVaultDetails | PortalLedgityVaultDetails

type BetaFlags = PortalMorphoBetaPortalFlags | PortalLedgityBetaPortalFlags

type VaultPosition = PortalMorphoVaultPosition | PortalLedgityVaultPosition

type Props = {
  vault: DefiVault
  beta?: BetaFlags | null
  mode?: InvestMode
  onClose: () => void
}

const MORPHO_DISCLAIMER =
  'This product places your USDC in a Morpho vault on Base. Yield comes from a third-party DeFi protocol and is not guaranteed. APY is variable. You are exposed to smart contract, liquidity, and market risks.'

const LEDGITY_DISCLAIMER =
  'This product places your stablecoins in a Ledgity vault (ERC4626) on Base, exposed to tokenized real-world assets (RWA). Yield is not guaranteed and APY is variable. Liquidity may be limited. You are exposed to smart contract, liquidity, market, and RWA counterparty risks.'

type ExecutionPhase = PortalMorphoExecutionPhase | PortalLedgityExecutionPhase

function isLedgityVault(vault: DefiVault): vault is PortalLedgityVaultDetails {
  return vault.integrationMode === 'ledgity_vault'
}

function executionPhaseLabel(phase: ExecutionPhase): string {
  switch (phase) {
    case 'preparing':
      return 'Preparing…'
    case 'approval_pending':
      return 'Approval pending…'
    case 'deposit_pending':
      return 'Deposit pending…'
    case 'withdraw_pending':
      return 'Withdrawal pending…'
    case 'confirming':
      return 'Confirming on-chain…'
    case 'confirmed':
      return 'Confirmed'
    case 'failed':
      return 'Failed'
    default:
      return 'Processing…'
  }
}

function createIdempotencyKey(prefix: 'morpho' | 'ledgity'): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function DefiInvestGain({
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

function DefiInvestTech({
  source,
  target,
  vaultAddress,
}: {
  source: PortalInvestSource
  target: PortalInvestTarget
  vaultAddress: string
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
            <span className="inv-tech__v">1 {source.short}</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Execution time</span>
            <span className="inv-tech__v">On-chain (Base)</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Network</span>
            <span className="inv-tech__v">Base</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Source asset</span>
            <span className="inv-tech__v">{source.techSource}</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Vault contract</span>
            <span className="inv-tech__v">{vaultAddress}</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Received asset</span>
            <span className="inv-tech__v">{target.tech}</span>
          </div>
          <div className="inv-tech__row">
            <span className="inv-tech__k">Network fees</span>
            <span className="inv-tech__v">Covered by Vancelian when enabled</span>
          </div>
        </div>
      ) : null}
    </>
  )
}

/** DeFi vault invest / withdraw — handoff InvestFlow layout + on-chain execution. */
export function PortalDefiVaultInvestFlow({ vault, beta, mode = 'invest', onClose }: Props) {
  const isLedgity = isLedgityVault(vault)
  const disclaimer = isLedgity ? LEDGITY_DISCLAIMER : MORPHO_DISCLAIMER
  const disclaimerStorageKey = isLedgity
    ? `portal_ledgity_disclaimer_${vault.vaultAddress.toLowerCase()}`
    : `portal_morpho_disclaimer_${vault.vaultAddress.toLowerCase()}`

  const [amount, setAmount] = useState(() => (mode === 'invest' ? '10,000' : ''))
  const [sources, setSources] = useState<PortalInvestSource[]>(() => defaultInvestSources())
  const [source, setSource] = useState<PortalInvestSource>(() => defaultInvestSources()[0]!)
  const [target, setTarget] = useState<PortalInvestTarget>(() =>
    buildDefiVaultInvestTarget(
      isLedgity ? { kind: 'ledgity', vault } : { kind: 'morpho', vault: vault as PortalMorphoVaultDetails },
    ),
  )
  const [position, setPosition] = useState<VaultPosition | null>(null)
  const [positionLoading, setPositionLoading] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<ExecutionPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false)
  const [pulseKey, setPulseKey] = useState(0)
  const [scene, setScene] = useState<'form' | 'selector'>('form')
  const [popSource, setPopSource] = useState(0)
  const idempotencyKeyRef = useRef<string | null>(null)
  const positionRef = useRef<VaultPosition | null>(null)
  positionRef.current = position

  const { execute: executeMorpho } = usePortalMorphoVaultExecution()
  const { execute: executeLedgity } = usePortalLedgityVaultExecution()
  const { executionAddress: walletAddress } = usePortalExecutionScope()

  const { data: walletData } = usePortalCachedScreen<PortalCryptoWalletHubPayload>({
    cacheKey: 'portal:defi-invest-balances',
    url: '/api/portal/crypto-wallet',
    ttlMs: 45_000,
    errorMessage: '',
    scopeAware: true,
  })

  useEffect(() => {
    try {
      setDisclaimerAccepted(window.localStorage.getItem(disclaimerStorageKey) === '1')
    } catch {
      setDisclaimerAccepted(false)
    }
  }, [disclaimerStorageKey])

  const acceptDisclaimer = useCallback(() => {
    setDisclaimerAccepted(true)
    try {
      window.localStorage.setItem(disclaimerStorageKey, '1')
    } catch {
      /* ignore */
    }
  }, [disclaimerStorageKey])

  useEffect(() => {
    const positions = walletData?.positions?.positions ?? []
    const usdc = resolveVaultDepositUsdcBalance(positions)
    setSources((prev) => {
      const next = mergeSourceBalance(prev, 'usdc', usdc)
      setSource((current) => next.find((s) => s.key === current.key) ?? next[0]!)
      return next
    })
  }, [walletData])

  const loadPosition = useCallback(
    async (address: string, options?: { background?: boolean }) => {
      if (!options?.background) setPositionLoading(true)
      try {
        const next = isLedgity
          ? await fetchPortalLedgityPosition({ vaultAddress: vault.vaultAddress, walletAddress: address })
          : await fetchPortalMorphoPosition({
              vaultAddress: vault.vaultAddress,
              walletAddress: address,
            })
        setPosition(next)
        const vaultAmt = next
          ? parseVaultPositionAmount(next.assetsInVault, next.asset.decimals)
          : 0
        setTarget(
          buildDefiVaultInvestTarget(
            isLedgity
              ? { kind: 'ledgity', vault }
              : { kind: 'morpho', vault: vault as PortalMorphoVaultDetails },
            {
              display: next?.assetsInVaultDisplay ?? `0 ${vault.asset.symbol}`,
              heldLabel: vaultAmt > 0 ? 'in vault' : 'to initiate',
            },
          ),
        )
      } catch {
        if (!options?.background) {
          setPosition(null)
          setTarget(
            buildDefiVaultInvestTarget(
              isLedgity
                ? { kind: 'ledgity', vault }
                : { kind: 'morpho', vault: vault as PortalMorphoVaultDetails },
            ),
          )
        }
      } finally {
        if (!options?.background) setPositionLoading(false)
      }
    },
    [isLedgity, vault],
  )

  useEffect(() => {
    if (!walletAddress) {
      setPosition(null)
      setPositionLoading(false)
      return
    }
    setPosition(null)
    void loadPosition(walletAddress)
  }, [walletAddress, loadPosition])

  useEffect(() => {
    setAmount('')
    setError(null)
    setSuccess(null)
    idempotencyKeyRef.current = null
    setExecutionPhase('idle')
  }, [mode])

  const vaultBalance = useMemo(() => {
    if (!position) return 0
    return parseVaultPositionAmount(position.assetsInVault, position.asset.decimals)
  }, [position])

  const isInvest = mode === 'invest'
  const numeric = invParseAmount(amount)
  const amountEur = numeric * source.rateToEur
  const received = numeric
  const rate = target.yieldPct
  const daily = amountEur * rate / 365
  const monthly = amountEur * rate / 12
  const yearly = amountEur * rate
  const maxAmt = isInvest ? source.balance : vaultBalance
  const sliderVal = Math.max(0, Math.min(maxAmt, numeric))
  const fillPct = maxAmt > 0 ? (sliderVal / maxAmt) * 100 : 0
  const sym = source.glyph
  const vaultAssetSymbol = vault.asset.symbol

  const vaultBalanceLabel = positionLoading
    ? 'Loading vault balance…'
    : vaultBalance > 0
      ? `${invFmtAmount(vaultBalance, vaultBalance % 1 === 0 ? 0 : 2)} ${vaultAssetSymbol} in vault`
      : `${target.held} ${target.heldLabel}`

  const showDisclaimer = isInvest && !disclaimerAccepted
  const depositsDisabled = Boolean(beta?.depositsDisabled)
  const withdrawsDisabled = Boolean(beta?.withdrawsDisabled)
  const depositBlocked = isInvest && depositsDisabled
  const withdrawBlocked = !isInvest && withdrawsDisabled
  const operationBlocked = depositBlocked || withdrawBlocked

  const setAmt = (value: number) => {
    const rounded = Math.round(value * 100) / 100
    setAmount(invFmtAmount(rounded, rounded % 1 === 0 ? 0 : 2))
  }

  const applyMax = () => {
    setAmt(isInvest ? source.balance : vaultBalance)
  }

  const verb = isInvest ? 'Invest' : 'Withdraw'
  const ctaLabel =
    executing && executionPhase !== 'idle'
      ? executionPhaseLabel(executionPhase)
      : numeric > 0
        ? `${verb} ${invFmtAmount(numeric, numeric % 1 === 0 ? 0 : 2)} ${sym}`
        : 'Enter an amount'

  const disabled =
    executing ||
    showDisclaimer ||
    operationBlocked ||
    positionLoading ||
    numeric <= 0 ||
    numeric > maxAmt + 1e-6 ||
    !walletAddress

  useEffect(() => {
    setPulseKey((k) => k + 1)
  }, [amount, mode, target.key, source.key])

  const onSubmit = useCallback(async () => {
    if (executing) return
    if (numeric <= 0 || numeric > maxAmt + 1e-6 || !walletAddress || showDisclaimer || operationBlocked) {
      return
    }
    setError(null)
    setSuccess(null)

    if (isInvest && !disclaimerAccepted) {
      setError('Please accept the warnings before your first deposit.')
      return
    }

    const normalized = amount.trim().replace(',', '.')
    if (!normalized || Number(normalized) <= 0) {
      setError('Enter a valid amount.')
      return
    }

    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current = createIdempotencyKey(isLedgity ? 'ledgity' : 'morpho')
    }

    setExecuting(true)
    setExecutionPhase('preparing')
    try {
      const operation = isInvest ? 'deposit' : 'withdraw'
      const txHash = isLedgity
        ? await executeLedgity({
            vaultAddress: vault.vaultAddress,
            operation,
            amount: normalized,
            idempotencyKey: idempotencyKeyRef.current,
            onPhaseChange: setExecutionPhase,
          })
        : await executeMorpho({
            vaultAddress: vault.vaultAddress,
            operation,
            amount: normalized,
            idempotencyKey: idempotencyKeyRef.current,
            onPhaseChange: setExecutionPhase,
          })

      setSuccess(
        isInvest
          ? `Deposit of ${normalized} ${vault.asset.symbol} confirmed.${txHash ? ` Tx: ${txHash}` : ''}`
          : `Withdrawal of ${normalized} ${vault.asset.symbol} confirmed.${txHash ? ` Tx: ${txHash}` : ''}`,
      )
      setAmount('')
      idempotencyKeyRef.current = null
      setExecutionPhase('idle')
      if (walletAddress) {
        await loadPosition(walletAddress, { background: true })
      }
    } catch (e) {
      setExecutionPhase('failed')
      setError(e instanceof Error ? e.message : 'Operation failed.')
    } finally {
      setExecuting(false)
    }
  }, [
    amount,
    disclaimerAccepted,
    executeLedgity,
    executeMorpho,
    executing,
    isInvest,
    isLedgity,
    loadPosition,
    maxAmt,
    numeric,
    operationBlocked,
    showDisclaimer,
    vault.asset.symbol,
    vault.vaultAddress,
    walletAddress,
  ])

  const topLabel = isInvest ? 'I invest' : 'I withdraw from'
  const bottomLabel = isInvest ? 'I receive' : 'I receive on'
  const canPickSource = isInvest && sources.length > 1

  const openSelector = () => {
    if (!canPickSource) return
    setScene('selector')
  }

  const closeSelector = () => {
    setScene('form')
  }

  const pickSource = (asset: PortalInvestSource | PortalInvestTarget) => {
    setSource(asset as PortalInvestSource)
    setPopSource((k) => k + 1)
    closeSelector()
  }

  return (
    <PortalExecutionScopeGate requirement="defi">
      <PortalInvestFlowDom
        scene={scene}
        form={
          <div className="inv-pane">
            <header className="inv-head">
              <h2 className="inv-head__title">{isInvest ? 'Invest' : 'Withdraw'}</h2>
              <div className="inv-head__actions">
                <button type="button" className="inv-head__btn" onClick={onClose} aria-label="Close">
                  <KalaiIcon name="close" size={16} />
                </button>
              </div>
            </header>

            {showDisclaimer ? (
              <div className="inv-disclaimer">
                <p className="inv-disclaimer__title">Warning — first deposit</p>
                <p className="inv-disclaimer__body">{disclaimer}</p>
                <Button
                  type="button"
                  className="inv-disclaimer__btn"
                  onClick={acceptDisclaimer}
                  disabled={executing}
                >
                  I understand and wish to continue
                </Button>
              </div>
            ) : null}

            {operationBlocked ? (
              <p className="inv-alert">
                {depositBlocked
                  ? 'Deposits are temporarily paused. You can still withdraw your funds.'
                  : 'Withdrawals are temporarily paused.'}
              </p>
            ) : null}

            {!isInvest && !positionLoading && vaultBalance <= 0 ? (
              <p className="inv-alert">
                No funds in this vault yet. Deposit first, then you can withdraw here.
              </p>
            ) : null}

            <div className="inv-iowrap">
              <div className="inv-io">
                <div className="inv-io__top">
                  <span className="inv-io__label">{isInvest ? topLabel : bottomLabel}</span>
                  <span className="inv-io__balance">
                    {isInvest ? (
                      source.balanceLabel
                    ) : (
                      <>Wallet · {invFmtAmount(source.balance, 2)} USDC</>
                    )}
                    {isInvest && maxAmt > 0 ? (
                      <button type="button" className="inv-io__max" onClick={applyMax}>
                        Max
                      </button>
                    ) : null}
                  </span>
                </div>
                <div className="inv-io__row">
                  <input
                    type="text"
                    inputMode="decimal"
                    className="inv-io__amount"
                    value={amount}
                    disabled={executing || showDisclaimer}
                    onChange={(e) => setAmount(e.target.value)}
                    aria-label={isInvest ? topLabel : bottomLabel}
                  />
                  <PortalInvestChip
                    asset={source}
                    popKey={popSource}
                    selectable={canPickSource}
                    onClick={openSelector}
                  />
                </div>
              </div>

              <div className="inv-divider" aria-hidden="true" />

              <div className="inv-io">
                <div className="inv-io__top">
                  <span className="inv-io__label">{isInvest ? bottomLabel : topLabel}</span>
                  <span className="inv-io__balance">
                    {isInvest ? (
                      <>
                        {target.held} {target.heldLabel}
                      </>
                    ) : (
                      vaultBalanceLabel
                    )}
                    {!isInvest && vaultBalance > 0 ? (
                      <button type="button" className="inv-io__max" onClick={applyMax}>
                        Max
                      </button>
                    ) : null}
                  </span>
                </div>
                <div className="inv-io__row">
                  <input
                    type="text"
                    className="inv-io__amount"
                    value={invFmtAmount(received, received >= 100 ? 0 : 2)}
                    readOnly
                    aria-label="Estimated amount"
                  />
                  <PortalInvestChip asset={target} selectable={false} />
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
                  step={Math.max(0.01, maxAmt / 1000)}
                  value={sliderVal}
                  disabled={executing || showDisclaimer || maxAmt <= 0}
                  onChange={(e) => setAmt(Number(e.target.value))}
                  style={{ ['--inv-fill' as string]: `${fillPct}%` }}
                  aria-label="Amount to invest"
                />
                <div className="inv-gains">
                  <DefiInvestGain label="Daily" value={invFmtAmount(daily, 2)} suffix="€" pulseKey={pulseKey} />
                  <DefiInvestGain label="Monthly" value={invFmtAmount(monthly, 0)} suffix="€" pulseKey={pulseKey} />
                  <DefiInvestGain label="Yearly" value={invFmtAmount(yearly, 0)} suffix="€" pulseKey={pulseKey} />
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
                  {rate > 0
                    ? `${(rate * 100).toLocaleString('en-US', {
                        minimumFractionDigits: 1,
                        maximumFractionDigits: 2,
                      })}%/yr`
                    : '—'}
                </span>
              </div>
            </div>

            {error ? <p className="inv-feedback inv-feedback--error">{error}</p> : null}
            {success ? <p className="inv-feedback inv-feedback--success">{success}</p> : null}

            <button
              type="button"
              className="btn btn--primary btn--lg inv-cta"
              disabled={disabled}
              onClick={() => void onSubmit()}
            >
              {executing ? (
                <span className="inline-flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {ctaLabel}
                </span>
              ) : (
                ctaLabel
              )}
            </button>

            <DefiInvestTech source={source} target={target} vaultAddress={vault.vaultAddress} />
          </div>
        }
        selector={
          scene === 'selector' ? (
            <PortalInvestSelector
              field="from"
              source={source}
              target={target}
              sources={sources}
              targets={[target]}
              onPick={pickSource}
              onClose={closeSelector}
            />
          ) : null
        }
      />
    </PortalExecutionScopeGate>
  )
}
