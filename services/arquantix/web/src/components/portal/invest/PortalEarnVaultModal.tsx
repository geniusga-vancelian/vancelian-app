'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2, X } from 'lucide-react'

import { PortalCryptoAvatar } from '@/components/portal/markets/PortalCryptoAvatar'
import { PortalExecutionScopeBanner } from '@/components/portal/PortalExecutionScopeBanner'
import { PortalExecutionScopeGate } from '@/components/portal/PortalExecutionScopeGate'
import { Button } from '@/components/ui/button'
import { fetchPortalMorphoPosition } from '@/lib/portal/morphoVaultClient'
import { getPortalMorphoIntegrationLabel } from '@/lib/portal/morphoConstants'
import { formatEarnApyFromBps, formatEarnTokenAmount } from '@/lib/portal/morphoVaultFormat'
import type {
  PortalMorphoVaultDetails,
  PortalMorphoVaultPosition,
  PortalMorphoBetaPortalFlags,
} from '@/lib/portal/morphoVaultTypes'
import {
  type PortalMorphoExecutionPhase,
  usePortalMorphoVaultExecution,
} from '@/lib/portal/usePortalMorphoVaultExecution'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { cn } from '@/lib/utils'

type Tab = 'deposit' | 'withdraw'

type Props = {
  vault: PortalMorphoVaultDetails
  beta?: PortalMorphoBetaPortalFlags
  /** Page dédiée (`/app/invest/vault/...`) — sans overlay modal ni second PrivyProvider. */
  embedded?: boolean
  onClose: () => void
}

const MORPHO_DISCLAIMER =
  'This product places your USDC in a Morpho vault on Base. Yield comes from a third-party DeFi protocol and is not guaranteed. APY is variable. You are exposed to smart contract, liquidity, and market risks.'

function executionPhaseLabel(phase: PortalMorphoExecutionPhase): string {
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

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `morpho-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function PortalEarnVaultModal({ vault, beta, embedded = false, onClose }: Props) {
  const [tab, setTab] = useState<Tab>('deposit')
  const [amount, setAmount] = useState('')
  const [position, setPosition] = useState<PortalMorphoVaultPosition | null>(null)
  const [positionLoading, setPositionLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<PortalMorphoExecutionPhase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false)
  const idempotencyKeyRef = useRef<string | null>(null)
  const positionRef = useRef<PortalMorphoVaultPosition | null>(null)
  positionRef.current = position

  const disclaimerStorageKey = `portal_morpho_disclaimer_${vault.vaultAddress.toLowerCase()}`
  const { execute: executeMorpho } = usePortalMorphoVaultExecution()
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
        const next = await fetchPortalMorphoPosition({
          vaultAddress: vault.vaultAddress,
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
    [vault.vaultAddress],
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

  const resetOperationState = useCallback(() => {
    idempotencyKeyRef.current = null
    setExecutionPhase('idle')
  }, [])

  const onSubmit = useCallback(async () => {
    if (executing) return
    setError(null)
    setSuccess(null)

    if (tab === 'deposit' && !disclaimerAccepted) {
      setError('Please accept the warnings before your first deposit.')
      return
    }

    const normalized = amount.trim().replace(',', '.')
    if (!normalized || Number(normalized) <= 0) {
      setError('Enter a valid amount.')
      return
    }

    if (!idempotencyKeyRef.current) {
      idempotencyKeyRef.current = createIdempotencyKey()
    }
    const idempotencyKey = idempotencyKeyRef.current

    setExecuting(true)
    setExecutionPhase('preparing')
    try {
      const txHash = await executeMorpho({
        vaultAddress: vault.vaultAddress,
        operation: tab,
        amount: normalized,
        idempotencyKey,
        onPhaseChange: setExecutionPhase,
      })
      setSuccess(
        tab === 'deposit'
          ? `Deposit of ${normalized} ${vault.asset.symbol} confirmed.${txHash ? ` Tx: ${txHash}` : ''}`
          : `Withdrawal of ${normalized} ${vault.asset.symbol} confirmed.${txHash ? ` Tx: ${txHash}` : ''}`,
      )
      setAmount('')
      resetOperationState()
      if (displayWalletAddress) {
        await loadPosition(displayWalletAddress, { background: true })
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
    displayWalletAddress,
    executeMorpho,
    executing,
    loadPosition,
    resetOperationState,
    tab,
    vault.asset.symbol,
    vault.vaultAddress,
  ])

  const positionDisplay =
    positionLoading && position === null
      ? '…'
      : position?.assetsInVaultDisplay ?? `0 ${vault.asset.symbol}`

  const showDisclaimer = tab === 'deposit' && !disclaimerAccepted
  const depositsDisabled = Boolean(beta?.depositsDisabled)
  const withdrawsDisabled = Boolean(beta?.withdrawsDisabled)
  const depositBlocked = tab === 'deposit' && depositsDisabled
  const withdrawBlocked = tab === 'withdraw' && withdrawsDisabled
  const operationBlocked = depositBlocked || withdrawBlocked
  const betaLimits = beta?.limits

  return (
    <div
      className={cn(
        embedded
          ? 'flex w-full flex-col'
          : 'fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-4 sm:items-center',
      )}
    >
      <div
        className={cn(
          'flex w-full flex-col overflow-hidden bg-v-bg',
          embedded
            ? 'min-h-0'
            : 'max-h-[90vh] max-w-lg rounded-v-card border border-v-border shadow-v-subtle',
        )}
        role={embedded ? undefined : 'dialog'}
        aria-modal={embedded ? undefined : true}
        aria-labelledby="earn-vault-modal-title"
      >
        <header className="flex items-center justify-between border-b border-v-border/70 px-5 py-4">
          <div className="flex min-w-0 items-center gap-3">
            <PortalCryptoAvatar ticker={vault.asset.symbol} symbol={vault.asset.symbol} size="sm" />
            <div className="min-w-0">
              <h2 id="earn-vault-modal-title" className="m-0 truncate font-ui text-[16px] font-semibold text-v-fg">
                {vault.name}
              </h2>
              <p className="m-0 font-ui text-[12px] text-v-fg-muted">
                APY {formatEarnApyFromBps(vault.userApyBps)} · {vault.asset.symbol} ·{' '}
                {getPortalMorphoIntegrationLabel(vault.integrationMode)}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={executing}
            className="inline-flex h-9 w-9 items-center justify-center rounded-full border border-v-border bg-v-card"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          <PortalExecutionScopeGate requirement="defi">
            <>
              <PortalExecutionScopeBanner context="defi" className="mb-4" />

              {showDisclaimer ? (
                <div className="mb-4 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-950">
                  <p className="m-0 font-semibold">Warning — first deposit</p>
                  <p className="m-0 mt-2 leading-relaxed">{MORPHO_DISCLAIMER}</p>
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

              {betaLimits && tab === 'deposit' ? (
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
                {position && maxWithdraw !== '0' ? (
                  <p className="m-0 mt-1 text-v-fg-muted">
                    Max withdrawable: {formatEarnTokenAmount(position.assetsInVault, position.asset.decimals)}{' '}
                    {vault.asset.symbol}
                  </p>
                ) : null}
              </div>

              <div className="mb-4 grid grid-cols-2 gap-2 rounded-v-card border border-v-border bg-v-card p-1">
                {(['deposit', 'withdraw'] as const).map((value) => (
                  <button
                    key={value}
                    type="button"
                    disabled={executing || (value === 'deposit' && depositsDisabled) || (value === 'withdraw' && withdrawsDisabled)}
                    onClick={() => {
                      setTab(value)
                      setError(null)
                      setSuccess(null)
                      resetOperationState()
                    }}
                    className={cn(
                      'rounded-v-control px-3 py-2 font-ui text-[14px] font-medium transition-colors',
                      tab === value ? 'bg-v-fg text-white' : 'text-v-fg-muted hover:text-v-fg',
                    )}
                  >
                    {value === 'deposit' ? 'Deposit' : 'Withdraw'}
                  </button>
                ))}
              </div>

              <label className="flex flex-col gap-2 font-ui text-[13px] text-v-fg-muted">
                Amount ({vault.asset.symbol})
                <input
                  type="text"
                  inputMode="decimal"
                  value={amount}
                  disabled={executing || showDisclaimer}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder={tab === 'withdraw' && maxWithdraw ? `Max ${maxWithdraw}` : '0.00'}
                  className="h-12 rounded-v-control border border-v-border bg-white px-4 font-ui text-[16px] text-v-fg outline-none focus:border-v-fg"
                />
              </label>

              {tab === 'withdraw' && maxWithdraw ? (
                <button
                  type="button"
                  disabled={executing}
                  onClick={() => setAmount(maxWithdraw)}
                  className="mt-2 v-text-link border-0 bg-transparent p-0 font-ui text-[13px]"
                >
                  Withdraw maximum ({maxWithdraw} {vault.asset.symbol})
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
            </>
          </PortalExecutionScopeGate>
        </div>

        {displayWalletAddress ? (
          <footer className="border-t border-v-border/70 px-5 py-4">
            <Button
              type="button"
              disabled={executing || showDisclaimer || operationBlocked}
              className="h-[52px] w-full rounded-full font-ui text-[16px] font-semibold"
              onClick={() => void onSubmit()}
            >
              {executing ? (
                <span className="inline-flex items-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  {executionPhaseLabel(executionPhase)}
                </span>
              ) : tab === 'deposit' ? (
                'Confirm deposit'
              ) : (
                'Confirm withdrawal'
              )}
            </Button>
          </footer>
        ) : null}
      </div>
    </div>
  )
}
