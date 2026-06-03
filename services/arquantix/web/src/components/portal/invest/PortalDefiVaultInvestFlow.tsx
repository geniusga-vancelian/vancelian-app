'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { PortalInvestFlowDom } from '@/components/portal/invest/PortalInvestFlowDom'
import {
  PortalInvestChip,
  PortalInvestSelector,
} from '@/components/portal/invest/PortalInvestFlowParts'
import {
  PortalVaultExecutionController,
  type PortalVaultExecutionScene,
} from '@/components/portal/invest/PortalVaultExecutionController'
import { KalaiIcon } from '@/components/ui/KalaiIcon'
import { VAULT_FLOW_UI } from '@/components/portal/transaction/mappers/vaultUiCopy'
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
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { usePortalCachedScreen } from '@/lib/portal/usePortalCachedScreen'
import type { PortalVaultFlowScene, PortalVaultOperation } from '@/lib/portal/vaultFlowTypes'

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
  'Ce produit place vos USDC dans un coffre Morpho sur Base. Le rendement provient d’un protocole DeFi tiers et n’est pas garanti. L’APY est variable. Vous êtes exposé aux risques de smart contract, de liquidité et de marché.'

const LEDGITY_DISCLAIMER =
  'Ce produit place vos stablecoins dans un coffre Ledgity (ERC4626) sur Base, exposé à des actifs réels tokenisés (RWA). Le rendement n’est pas garanti et l’APY est variable. La liquidité peut être limitée. Vous êtes exposé aux risques de smart contract, de liquidité, de marché et de contrepartie RWA.'

function isLedgityVault(vault: DefiVault): vault is PortalLedgityVaultDetails {
  return vault.integrationMode === 'ledgity_vault'
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

/** DeFi vault invest / withdraw — Setup → Review → Processing → Result (R4.5-D). */
export function PortalDefiVaultInvestFlow({ vault, beta, mode = 'invest', onClose }: Props) {
  const isLedgity = isLedgityVault(vault)
  const disclaimer = isLedgity ? LEDGITY_DISCLAIMER : MORPHO_DISCLAIMER
  const integrationMode = isLedgity ? 'ledgity_vault' as const : 'direct_morpho' as const

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
  const [flowScene, setFlowScene] = useState<PortalVaultFlowScene>('setup')
  const [setupError, setSetupError] = useState<string | null>(null)
  const [pulseKey, setPulseKey] = useState(0)
  const [scene, setScene] = useState<'form' | 'selector'>('form')
  const [popSource, setPopSource] = useState(0)
  const positionRef = useRef<VaultPosition | null>(null)
  positionRef.current = position

  const { executionAddress: walletAddress } = usePortalExecutionScope()

  const { data: walletData } = usePortalCachedScreen<PortalCryptoWalletHubPayload>({
    cacheKey: 'portal:defi-invest-balances',
    url: '/api/portal/crypto-wallet',
    ttlMs: 45_000,
    errorMessage: '',
    scopeAware: true,
  })

  useEffect(() => {
    const positions = walletData?.positions?.positions ?? []
    const fromDirect = walletData?.tradingAvailableUsdc
    const usdc =
      fromDirect != null && Number.isFinite(fromDirect)
        ? Math.max(0, fromDirect)
        : resolveVaultDepositUsdcBalance(positions)
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
    setSetupError(null)
    setFlowScene('setup')
  }, [mode])

  const vaultBalance = useMemo(() => {
    if (!position) return 0
    return parseVaultPositionAmount(position.assetsInVault, position.asset.decimals)
  }, [position])

  const isInvest = mode === 'invest'
  const operation: PortalVaultOperation = isInvest ? 'deposit' : 'withdraw'
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

  const depositsDisabled = Boolean(beta?.depositsDisabled)
  const withdrawsDisabled = Boolean(beta?.withdrawsDisabled)
  const depositBlocked = isInvest && depositsDisabled
  const withdrawBlocked = !isInvest && withdrawsDisabled
  const operationBlocked = depositBlocked || withdrawBlocked

  const processingContext = useMemo(
    () => ({
      amountLabel: `${invFmtAmount(numeric, numeric % 1 === 0 ? 0 : 2)} ${vaultAssetSymbol}`,
      vaultLabel: target.name,
      assetSymbol: vaultAssetSymbol,
    }),
    [numeric, target.name, vaultAssetSymbol],
  )

  const reviewContext = useMemo(
    () => ({
      operation,
      amount: numeric,
      assetSymbol: vaultAssetSymbol,
      source,
      target,
      vaultAddress: vault.vaultAddress,
      provider: vault.provider,
      integrationMode,
      disclaimer,
      yieldPct: rate,
    }),
    [
      disclaimer,
      integrationMode,
      numeric,
      operation,
      rate,
      source,
      target,
      vault.provider,
      vault.vaultAddress,
      vaultAssetSymbol,
    ],
  )

  const normalizedAmount = useMemo(() => amount.trim().replace(',', '.'), [amount])

  const onExecutionSuccess = useCallback(async () => {
    setAmount('')
    if (walletAddress) {
      await loadPosition(walletAddress, { background: true })
    }
  }, [loadPosition, walletAddress])

  const setAmt = (value: number) => {
    const rounded = Math.round(value * 100) / 100
    setAmount(invFmtAmount(rounded, rounded % 1 === 0 ? 0 : 2))
  }

  const applyMax = () => {
    setAmt(isInvest ? source.balance : vaultBalance)
  }

  const setupDisabled =
    operationBlocked ||
    positionLoading ||
    numeric <= 0 ||
    numeric > maxAmt + 1e-6 ||
    !walletAddress

  const onContinueToReview = () => {
    setSetupError(null)
    if (setupDisabled) return
    if (!normalizedAmount || Number(normalizedAmount) <= 0) {
      setSetupError('Saisissez un montant valide.')
      return
    }
    setFlowScene('review')
  }

  useEffect(() => {
    setPulseKey((k) => k + 1)
  }, [amount, mode, target.key, source.key])

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

  const isExecutionScene = flowScene !== 'setup'

  const setupPane = (
      <div className="inv-pane">
        <header className="inv-head">
          <h2 className="inv-head__title">{isInvest ? 'Invest' : 'Withdraw'}</h2>
          <div className="inv-head__actions">
            <button type="button" className="inv-head__btn" onClick={onClose} aria-label="Close">
              <KalaiIcon name="close" size={16} />
            </button>
          </div>
        </header>

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
              disabled={maxAmt <= 0}
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

        {setupError ? <p className="inv-feedback inv-feedback--error">{setupError}</p> : null}

        <button
          type="button"
          className="btn btn--primary btn--lg inv-cta"
          disabled={setupDisabled}
          onClick={onContinueToReview}
        >
          {VAULT_FLOW_UI.continueCta}
        </button>
      </div>
  )

  return (
    <PortalExecutionScopeGate requirement="defi">
      <PortalInvestFlowDom
        scene={scene}
        form={
          isExecutionScene && walletAddress ? (
            <PortalVaultExecutionController
              flowScene={flowScene as PortalVaultExecutionScene}
              onFlowSceneChange={setFlowScene}
              presentation="invest"
              isLedgity={isLedgity}
              integrationMode={integrationMode}
              vaultAddress={vault.vaultAddress}
              provider={vault.provider}
              operation={operation}
              normalizedAmount={normalizedAmount}
              numeric={numeric}
              walletAddress={walletAddress}
              reviewContext={reviewContext}
              processingContext={processingContext}
              disclaimer={disclaimer}
              source={source}
              target={target}
              onClose={onClose}
              onExecutionSuccess={onExecutionSuccess}
            />
          ) : (
            setupPane
          )
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
