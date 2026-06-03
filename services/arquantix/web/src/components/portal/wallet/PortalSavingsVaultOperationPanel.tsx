'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { PortalExecutionScopeBanner } from '@/components/portal/PortalExecutionScopeBanner'
import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import {
  PortalVaultExecutionController,
  type PortalVaultExecutionScene,
} from '@/components/portal/invest/PortalVaultExecutionController'
import { Button } from '@/components/ui/button'
import { VAULT_FLOW_UI } from '@/components/portal/transaction/mappers/vaultUiCopy'
import { fetchPortalLedgityPosition } from '@/lib/portal/ledgity/ledgityVaultClient'
import {
  formatEarnApyFromBps as formatLedgityApyFromBps,
  formatEarnTokenAmount as formatLedgityTokenAmount,
} from '@/lib/portal/ledgity/ledgityVaultFormat'
import type {
  PortalLedgityBetaPortalFlags,
  PortalLedgityVaultDetails,
  PortalLedgityVaultPosition,
} from '@/lib/portal/ledgity/ledgityVaultTypes'
import { fetchPortalMorphoPosition } from '@/lib/portal/morphoVaultClient'
import { getPortalDefiIntegrationLabel } from '@/lib/portal/morphoConstants'
import { formatEarnApyFromBps, formatEarnTokenAmount } from '@/lib/portal/morphoVaultFormat'
import type {
  PortalMorphoBetaPortalFlags,
  PortalMorphoVaultDetails,
  PortalMorphoVaultPosition,
} from '@/lib/portal/morphoVaultTypes'
import type { PortalDefiBetaPortalFlags, PortalDefiVaultDetails } from '@/lib/portal/portalSavingsTypes'
import {
  buildDefiVaultInvestTarget,
  defaultInvestSources,
  invParseAmount,
} from '@/lib/portal/portalInvestFlowFormat'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import type { PortalVaultFlowScene, PortalVaultOperation } from '@/lib/portal/vaultFlowTypes'

type Tab = 'deposit' | 'withdraw'

type Props = {
  vault: PortalDefiVaultDetails
  beta?: PortalDefiBetaPortalFlags
  activeTab: Tab
  onSuccess?: () => void
}

const MORPHO_DISCLAIMER =
  'Ce produit place vos USDC dans un coffre Morpho sur Base. Le rendement provient d’un protocole DeFi tiers et n’est pas garanti. L’APY est variable. Vous êtes exposé aux risques de smart contract, de liquidité et de marché.'

const LEDGITY_DISCLAIMER =
  'Ce produit place vos stablecoins dans un coffre Ledgity (ERC4626) sur Base, exposé à des actifs réels tokenisés (RWA). Le rendement n’est pas garanti et l’APY est variable. La liquidité peut être limitée. Vous êtes exposé aux risques de smart contract, de liquidité, de marché et de contrepartie RWA.'

function isLedgityVault(vault: PortalDefiVaultDetails): vault is PortalLedgityVaultDetails {
  return vault.integrationMode === 'ledgity_vault'
}

type VaultPosition = PortalMorphoVaultPosition | PortalLedgityVaultPosition

/** Savings inline deposit / withdraw — Setup → Review → Processing → Result (R4.5-D). */
export function PortalSavingsVaultOperationPanel({ vault, beta, activeTab, onSuccess }: Props) {
  const isLedgity = isLedgityVault(vault)
  const operation: PortalVaultOperation = activeTab
  const disclaimer = isLedgity ? LEDGITY_DISCLAIMER : MORPHO_DISCLAIMER
  const integrationMode = isLedgity ? 'ledgity_vault' as const : 'direct_morpho' as const
  const assetSymbol = vault.asset.symbol
  const formatApy = isLedgity ? formatLedgityApyFromBps : formatEarnApyFromBps
  const formatTokenAmount = isLedgity ? formatLedgityTokenAmount : formatEarnTokenAmount

  const [amount, setAmount] = useState('')
  const [position, setPosition] = useState<VaultPosition | null>(null)
  const [positionLoading, setPositionLoading] = useState(true)
  const [flowScene, setFlowScene] = useState<PortalVaultFlowScene>('setup')
  const [setupError, setSetupError] = useState<string | null>(null)
  const positionRef = useRef<VaultPosition | null>(null)
  positionRef.current = position

  const source = useMemo(() => defaultInvestSources()[0]!, [])
  const target = useMemo(
    () =>
      buildDefiVaultInvestTarget(
        isLedgity
          ? { kind: 'ledgity', vault: vault as PortalLedgityVaultDetails }
          : { kind: 'morpho', vault: vault as PortalMorphoVaultDetails },
      ),
    [isLedgity, vault],
  )

  const { executionAddress: displayWalletAddress } = usePortalExecutionScope()

  const loadPosition = useCallback(
    async (walletAddress: string, options?: { background?: boolean }) => {
      if (!options?.background && positionRef.current === null) {
        setPositionLoading(true)
      }
      try {
        const next = isLedgity
          ? await fetchPortalLedgityPosition({ vaultAddress: vault.vaultAddress, walletAddress })
          : await fetchPortalMorphoPosition({
              vaultAddress: (vault as PortalMorphoVaultDetails).vaultAddress,
              walletAddress,
            })
        setPosition(next)
      } catch {
        if (!options?.background) setPosition(null)
      } finally {
        setPositionLoading(false)
      }
    },
    [isLedgity, vault],
  )

  useEffect(() => {
    if (!displayWalletAddress) {
      setPosition(null)
      setPositionLoading(false)
      return
    }
    setPosition(null)
    setPositionLoading(true)
    void loadPosition(displayWalletAddress)
  }, [displayWalletAddress, loadPosition])

  useEffect(() => {
    setAmount('')
    setSetupError(null)
    setFlowScene('setup')
  }, [activeTab])

  const maxWithdraw = useMemo(() => {
    if (!position) return ''
    const raw = position.assetsInVault
    if (!raw || raw === '0') return '0'
    const decimals = position.asset.decimals
    const value = BigInt(raw)
    const base = BigInt(10) ** BigInt(decimals)
    const whole = value / base
    const fraction = value % base
    if (fraction === BigInt(0)) return whole.toString()
    const fracStr = fraction.toString().padStart(decimals, '0').replace(/0+$/, '')
    return `${whole}.${fracStr}`
  }, [position])

  const numeric = invParseAmount(amount)
  const yieldPct = (vault.userApyBps ?? 0) > 0 ? (vault.userApyBps ?? 0) / 10_000 : 0

  const morphoBeta = !isLedgity ? (beta as PortalMorphoBetaPortalFlags | undefined) : undefined
  const ledgityBeta = isLedgity ? (beta as PortalLedgityBetaPortalFlags | undefined) : undefined
  const depositsDisabled = Boolean(morphoBeta?.depositsDisabled ?? ledgityBeta?.depositsDisabled)
  const withdrawsDisabled = Boolean(morphoBeta?.withdrawsDisabled ?? ledgityBeta?.withdrawsDisabled)
  const depositBlocked = activeTab === 'deposit' && depositsDisabled
  const withdrawBlocked = activeTab === 'withdraw' && withdrawsDisabled
  const operationBlocked = depositBlocked || withdrawBlocked
  const betaLimits = morphoBeta?.limits ?? ledgityBeta?.limits

  const processingContext = useMemo(
    () => ({
      amountLabel: `${amount.trim() || '0'} ${assetSymbol}`,
      vaultLabel: vault.name,
      assetSymbol,
    }),
    [amount, assetSymbol, vault.name],
  )

  const reviewContext = useMemo(
    () => ({
      operation,
      amount: numeric,
      assetSymbol,
      source,
      target,
      vaultAddress: vault.vaultAddress,
      provider: vault.provider,
      integrationMode,
      disclaimer,
      yieldPct,
    }),
    [
      amount,
      assetSymbol,
      disclaimer,
      integrationMode,
      numeric,
      operation,
      source,
      target,
      vault.provider,
      vault.vaultAddress,
      yieldPct,
    ],
  )

  const normalizedAmount = useMemo(() => amount.trim().replace(',', '.'), [amount])

  const onExecutionSuccess = useCallback(async () => {
    setAmount('')
    if (displayWalletAddress) {
      await loadPosition(displayWalletAddress, { background: true })
    }
    onSuccess?.()
  }, [displayWalletAddress, loadPosition, onSuccess])

  const setupDisabled = operationBlocked || positionLoading || numeric <= 0 || !displayWalletAddress

  if (flowScene !== 'setup' && displayWalletAddress) {
    return (
      <PortalVaultExecutionController
        flowScene={flowScene as PortalVaultExecutionScene}
        onFlowSceneChange={setFlowScene}
        presentation="savings"
        isLedgity={isLedgity}
        integrationMode={integrationMode}
        vaultAddress={vault.vaultAddress}
        provider={vault.provider}
        operation={operation}
        normalizedAmount={normalizedAmount}
        numeric={numeric}
        walletAddress={displayWalletAddress}
        reviewContext={reviewContext}
        processingContext={processingContext}
        disclaimer={disclaimer}
        source={source}
        target={target}
        onClose={() => setFlowScene('setup')}
        onExecutionSuccess={onExecutionSuccess}
      />
    )
  }

  return (
    <article className="card-simple overflow-hidden !w-full">
      <div className="border-b border-v-fg-10 px-4 py-3">
        <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">
          {activeTab === 'deposit' ? 'Deposit' : 'Withdraw'}
        </h2>
        <p className="m-0 mt-1 font-ui text-[13px] text-v-fg-muted">
          APY {formatApy(vault.userApyBps)} · {getPortalDefiIntegrationLabel(vault.integrationMode)}
        </p>
      </div>

      <div className="px-4 py-4">
        <PortalExecutionScopeGate requirement="defi">
          <>
            <PortalExecutionScopeBanner context="defi" className="mb-4" />

            {beta?.message && beta.allowed ? (
              <p className="mb-4 rounded-v-card border border-sky-200 bg-sky-50 px-4 py-3 font-ui text-[13px] text-sky-950">
                {beta.message}
              </p>
            ) : null}

            {operationBlocked ? (
              <p className="mb-4 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-900">
                {depositBlocked
                  ? 'Deposits are temporarily paused. You can still withdraw your funds.'
                  : 'Withdrawals are temporarily paused.'}
              </p>
            ) : null}

            {betaLimits && activeTab === 'deposit' ? (
              <p className="mb-4 font-ui text-[12px] text-v-fg-muted">
                Beta: min {betaLimits.minDepositUsdc} · max {betaLimits.maxDepositUsdc} USDC / tx · max exposure{' '}
                {betaLimits.maxUserExposureUsdc} USDC
              </p>
            ) : null}

            <div className="mb-4 rounded-v-card border border-v-border bg-v-card px-4 py-3 font-ui text-[13px]">
              <p className="m-0 text-v-fg-muted">Wallet</p>
              <p className="m-0 mt-1 font-medium text-v-fg">{displayWalletAddress}</p>
              <p className="m-0 mt-3 text-v-fg-muted">Vault position</p>
              <p className="m-0 mt-1 font-semibold text-v-fg">
                {positionLoading && position === null
                  ? '…'
                  : position?.assetsInVaultDisplay ?? `0 ${assetSymbol}`}
              </p>
            </div>

            <label className="flex flex-col gap-2 font-ui text-[13px] text-v-fg-muted">
              Amount ({assetSymbol})
              <input
                type="text"
                inputMode="decimal"
                value={amount}
                disabled={operationBlocked}
                onChange={(e) => setAmount(e.target.value)}
                placeholder={activeTab === 'withdraw' && maxWithdraw ? `Max ${maxWithdraw}` : '0.00'}
                className="h-12 rounded-v-control border border-v-border bg-white px-4 font-ui text-[16px] text-v-fg outline-none focus:border-v-fg"
              />
            </label>

            {activeTab === 'withdraw' && maxWithdraw ? (
              <button
                type="button"
                disabled={positionLoading}
                onClick={() => setAmount(maxWithdraw)}
                className="mt-2 v-text-link border-0 bg-transparent p-0 font-ui text-[13px]"
              >
                Withdraw maximum ({maxWithdraw} {assetSymbol})
              </button>
            ) : null}

            {setupError ? (
              <p className="mt-3 mb-0 rounded-v-control bg-red-50 px-3 py-2 font-ui text-[13px] text-v-error">
                {setupError}
              </p>
            ) : null}

            <Button
              type="button"
              disabled={setupDisabled}
              className="mt-4 h-[52px] w-full rounded-full font-ui text-[16px] font-semibold"
              onClick={() => {
                setSetupError(null)
                if (setupDisabled) return
                if (!normalizedAmount || Number(normalizedAmount) <= 0) {
                  setSetupError('Saisissez un montant valide.')
                  return
                }
                setFlowScene('review')
              }}
            >
              {VAULT_FLOW_UI.continueCta}
            </Button>
          </>
        </PortalExecutionScopeGate>
      </div>
    </article>
  )
}
