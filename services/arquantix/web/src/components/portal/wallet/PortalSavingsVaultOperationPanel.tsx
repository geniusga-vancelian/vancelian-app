'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { PortalExecutionScopeBanner } from '@/components/portal/PortalExecutionScopeBanner'
import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { Button } from '@/components/ui/button'
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
  type PortalMorphoExecutionPhase,
  usePortalMorphoVaultExecution,
} from '@/lib/portal/usePortalMorphoVaultExecution'
import {
  type PortalLedgityExecutionPhase,
  usePortalLedgityVaultExecution,
} from '@/lib/portal/usePortalLedgityVaultExecution'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'

type Tab = 'deposit' | 'withdraw'

type Props = {
  vault: PortalDefiVaultDetails
  beta?: PortalDefiBetaPortalFlags
  activeTab: Tab
  onSuccess?: () => void
}

const MORPHO_DISCLAIMER =
  'This product places your USDC in a Morpho vault on Base. Yield comes from a third-party DeFi protocol and is not guaranteed. APY is variable. You are exposed to smart contract, liquidity, and market risks.'

const LEDGITY_DISCLAIMER =
  'This product places your stablecoins in a Ledgity vault (ERC4626) on Base, exposed to tokenized real-world assets (RWA). Yield is not guaranteed and APY is variable. Liquidity may be limited. You are exposed to smart contract, liquidity, market, and RWA counterparty risks.'

type ExecutionPhase = PortalMorphoExecutionPhase | PortalLedgityExecutionPhase

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

function isLedgityVault(vault: PortalDefiVaultDetails): vault is PortalLedgityVaultDetails {
  return vault.integrationMode === 'ledgity_vault'
}

type VaultPosition = PortalMorphoVaultPosition | PortalLedgityVaultPosition

export function PortalSavingsVaultOperationPanel({ vault, beta, activeTab, onSuccess }: Props) {
  const isLedgity = isLedgityVault(vault)
  const assetSymbol = vault.asset.symbol
  const formatApy = isLedgity ? formatLedgityApyFromBps : formatEarnApyFromBps
  const formatTokenAmount = isLedgity ? formatLedgityTokenAmount : formatEarnTokenAmount
  const disclaimer = isLedgity ? LEDGITY_DISCLAIMER : MORPHO_DISCLAIMER
  const disclaimerStorageKey = isLedgity
    ? `portal_ledgity_disclaimer_${vault.vaultAddress.toLowerCase()}`
    : `portal_morpho_disclaimer_${vault.vaultAddress.toLowerCase()}`

  const [amount, setAmount] = useState('')
  const [position, setPosition] = useState<VaultPosition | null>(null)
  const [positionLoading, setPositionLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<ExecutionPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false)
  const idempotencyKeyRef = useRef<string | null>(null)
  const positionRef = useRef<VaultPosition | null>(null)
  positionRef.current = position

  const { execute: executeMorpho } = usePortalMorphoVaultExecution()
  const { execute: executeLedgity } = usePortalLedgityVaultExecution()
  const { executionAddress: displayWalletAddress } = usePortalExecutionScope()

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

  const loadPosition = useCallback(
    async (walletAddress: string, options?: { background?: boolean }) => {
      if (!options?.background && positionRef.current === null) {
        setPositionLoading(true)
      }

      try {
        const next = isLedgity
          ? await fetchPortalLedgityPosition({
              vaultAddress: vault.vaultAddress,
              walletAddress,
            })
          : await fetchPortalMorphoPosition({
              vaultAddress: (vault as PortalMorphoVaultDetails).vaultAddress,
              walletAddress,
            })
        setPosition(next)
      } catch {
        if (!options?.background) {
          setPosition(null)
        }
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
    setError(null)
    setSuccess(null)
    idempotencyKeyRef.current = null
    setExecutionPhase('idle')
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

  const onSubmit = useCallback(async () => {
    if (executing) return
    setError(null)
    setSuccess(null)

    if (activeTab === 'deposit' && !disclaimerAccepted) {
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
    const idempotencyKey = idempotencyKeyRef.current

    setExecuting(true)
    setExecutionPhase('preparing')
    try {
      const execute = isLedgity ? executeLedgity : executeMorpho
      const txHash = await execute({
        vaultAddress: vault.vaultAddress,
        operation: activeTab,
        amount: normalized,
        idempotencyKey,
        onPhaseChange: setExecutionPhase,
      })
      setSuccess(
        activeTab === 'deposit'
          ? `Deposit of ${normalized} ${assetSymbol} confirmed.${txHash ? ` Tx: ${txHash}` : ''}`
          : `Withdrawal of ${normalized} ${assetSymbol} confirmed.${txHash ? ` Tx: ${txHash}` : ''}`,
      )
      setAmount('')
      idempotencyKeyRef.current = null
      setExecutionPhase('idle')
      if (displayWalletAddress) {
        await loadPosition(displayWalletAddress, { background: true })
      }
      onSuccess?.()
    } catch (e) {
      setExecutionPhase('failed')
      setError(e instanceof Error ? e.message : 'Operation failed.')
    } finally {
      setExecuting(false)
    }
  }, [
    activeTab,
    amount,
    assetSymbol,
    disclaimerAccepted,
    displayWalletAddress,
    executeLedgity,
    executeMorpho,
    executing,
    isLedgity,
    loadPosition,
    onSuccess,
    vault.vaultAddress,
  ])

  const positionDisplay =
    positionLoading && position === null
      ? '…'
      : position?.assetsInVaultDisplay ?? `0 ${assetSymbol}`

  const showDisclaimer = activeTab === 'deposit' && !disclaimerAccepted
  const morphoBeta = !isLedgity ? (beta as PortalMorphoBetaPortalFlags | undefined) : undefined
  const ledgityBeta = isLedgity ? (beta as PortalLedgityBetaPortalFlags | undefined) : undefined
  const depositsDisabled = Boolean(morphoBeta?.depositsDisabled ?? ledgityBeta?.depositsDisabled)
  const withdrawsDisabled = Boolean(morphoBeta?.withdrawsDisabled ?? ledgityBeta?.withdrawsDisabled)
  const depositBlocked = activeTab === 'deposit' && depositsDisabled
  const withdrawBlocked = activeTab === 'withdraw' && withdrawsDisabled
  const operationBlocked = depositBlocked || withdrawBlocked
  const betaLimits = morphoBeta?.limits ?? ledgityBeta?.limits

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

            {showDisclaimer ? (
              <div className="mb-4 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-950">
                <p className="m-0 font-semibold">Warning — first deposit</p>
                <p className="m-0 mt-2 leading-relaxed">{disclaimer}</p>
                <Button
                  type="button"
                  className="mt-3 h-10 rounded-full font-ui text-[14px]"
                  onClick={acceptDisclaimer}
                  disabled={executing}
                >
                  I understand and wish to continue
                </Button>
              </div>
            ) : null}

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
              <p className="m-0 mt-1 font-semibold text-v-fg">{positionDisplay}</p>
              {position && position.yieldSyncStatus !== 'pending' && position.earnedYieldDisplay ? (
                <p className="m-0 mt-1 text-v-green">+{position.earnedYieldDisplay} yield</p>
              ) : position?.yieldSyncStatus === 'pending' ? (
                <p className="m-0 mt-1 text-v-fg-muted">{position.earnedYieldDisplay}</p>
              ) : null}
            </div>

            <label className="flex flex-col gap-2 font-ui text-[13px] text-v-fg-muted">
              Amount ({assetSymbol})
              <input
                type="text"
                inputMode="decimal"
                value={amount}
                disabled={executing || showDisclaimer || operationBlocked}
                onChange={(e) => setAmount(e.target.value)}
                placeholder={activeTab === 'withdraw' && maxWithdraw ? `Max ${maxWithdraw}` : '0.00'}
                className="h-12 rounded-v-control border border-v-border bg-white px-4 font-ui text-[16px] text-v-fg outline-none focus:border-v-fg"
              />
            </label>

            {activeTab === 'withdraw' && maxWithdraw ? (
              <button
                type="button"
                disabled={executing}
                onClick={() => setAmount(maxWithdraw)}
                className="mt-2 v-text-link border-0 bg-transparent p-0 font-ui text-[13px]"
              >
                Withdraw maximum ({maxWithdraw} {assetSymbol})
              </button>
            ) : null}

            {executing && executionPhase !== 'idle' ? (
              <p className="mt-3 mb-0 font-ui text-[13px] text-v-fg-muted">
                {executionPhaseLabel(executionPhase)}
              </p>
            ) : null}

            {error ? (
              <p className="mt-3 mb-0 rounded-v-control bg-red-50 px-3 py-2 font-ui text-[13px] text-v-error">
                {error}
              </p>
            ) : null}
            {success ? (
              <p className="mt-3 mb-0 rounded-v-control bg-emerald-50 px-3 py-2 font-ui text-[13px] text-emerald-800">
                {success}
              </p>
            ) : null}

            <Button
              type="button"
              disabled={executing || showDisclaimer || operationBlocked}
              className="mt-4 h-[52px] w-full rounded-full font-ui text-[16px] font-semibold"
              onClick={() => void onSubmit()}
            >
              {executing ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {executionPhaseLabel(executionPhase)}
                </span>
              ) : activeTab === 'deposit' ? (
                'Confirm deposit'
              ) : (
                'Confirm withdrawal'
              )}
            </Button>
          </>
        </PortalExecutionScopeGate>
      </div>
    </article>
  )
}
