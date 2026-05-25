'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { ExecutionWalletSelector } from '@/components/wallet/ExecutionWalletSelector'
import { PortalNavLink } from '@/components/portal/PortalNavLink'
import { Button } from '@/components/ui/button'
import { fetchPortalMorphoPosition } from '@/lib/portal/morphoVaultClient'
import { getPortalMorphoIntegrationLabel } from '@/lib/portal/morphoConstants'
import { formatEarnApyFromBps, formatEarnTokenAmount } from '@/lib/portal/morphoVaultFormat'
import { PORTAL_ROUTES } from '@/lib/portal/portalRouting'
import type {
  PortalMorphoBetaPortalFlags,
  PortalMorphoVaultDetails,
  PortalMorphoVaultPosition,
} from '@/lib/portal/morphoVaultTypes'
import {
  type PortalMorphoExecutionPhase,
  usePortalMorphoVaultExecution,
} from '@/lib/portal/usePortalMorphoVaultExecution'
import { useExecutionWallet } from '@/lib/wallet/useExecutionWallet'

type Tab = 'deposit' | 'withdraw'

type Props = {
  vault: PortalMorphoVaultDetails
  beta?: PortalMorphoBetaPortalFlags
  activeTab: Tab
  onSuccess?: () => void
}

const MORPHO_DISCLAIMER =
  'Ce produit place vos USDC dans un vault Morpho sur Base. Le rendement provient d’un protocole DeFi tiers et n’est pas garanti. L’APY est variable. Vous êtes exposé aux risques de smart contract, de liquidité et de marché.'

function executionPhaseLabel(phase: PortalMorphoExecutionPhase): string {
  switch (phase) {
    case 'preparing':
      return 'Préparation…'
    case 'approval_pending':
      return 'Approbation en cours…'
    case 'deposit_pending':
      return 'Dépôt en cours…'
    case 'withdraw_pending':
      return 'Retrait en cours…'
    case 'confirming':
      return 'Confirmation on-chain…'
    case 'confirmed':
      return 'Confirmé'
    case 'failed':
      return 'Échec'
    default:
      return 'Traitement…'
  }
}

function createIdempotencyKey(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `morpho-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

export function PortalSavingsVaultOperationPanel({ vault, beta, activeTab, onSuccess }: Props) {
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
  const {
    mode: executionMode,
    privyEmbeddedAddress,
    externalWallets,
    selectedExternalWalletId,
  } = useExecutionWallet()

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

  const displayWalletAddress = useMemo(() => {
    if (executionMode === 'external_evm') {
      const selected =
        externalWallets.find((row) => row.id === selectedExternalWalletId) ?? externalWallets[0]
      return selected?.address ?? privyEmbeddedAddress
    }
    return privyEmbeddedAddress
  }, [executionMode, externalWallets, privyEmbeddedAddress, selectedExternalWalletId])

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
      setError('Veuillez accepter les avertissements avant votre premier dépôt.')
      return
    }

    const normalized = amount.trim().replace(',', '.')
    if (!normalized || Number(normalized) <= 0) {
      setError('Indiquez un montant valide.')
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
        operation: activeTab,
        amount: normalized,
        idempotencyKey,
        onPhaseChange: setExecutionPhase,
      })
      setSuccess(
        activeTab === 'deposit'
          ? `Dépôt de ${normalized} ${vault.asset.symbol} confirmé.${txHash ? ` Tx: ${txHash}` : ''}`
          : `Retrait de ${normalized} ${vault.asset.symbol} confirmé.${txHash ? ` Tx: ${txHash}` : ''}`,
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
      setError(e instanceof Error ? e.message : 'Opération impossible.')
    } finally {
      setExecuting(false)
    }
  }, [
    activeTab,
    amount,
    disclaimerAccepted,
    displayWalletAddress,
    executeMorpho,
    executing,
    loadPosition,
    onSuccess,
    vault.asset.symbol,
    vault.vaultAddress,
  ])

  const walletReady =
    executionMode === 'external_evm'
      ? externalWallets.length > 0
      : Boolean(privyEmbeddedAddress)

  const positionDisplay =
    positionLoading && position === null
      ? '…'
      : position?.assetsInVaultDisplay ?? `0 ${vault.asset.symbol}`

  const showDisclaimer = activeTab === 'deposit' && !disclaimerAccepted
  const depositsDisabled = Boolean(beta?.depositsDisabled)
  const withdrawsDisabled = Boolean(beta?.withdrawsDisabled)
  const depositBlocked = activeTab === 'deposit' && depositsDisabled
  const withdrawBlocked = activeTab === 'withdraw' && withdrawsDisabled
  const operationBlocked = depositBlocked || withdrawBlocked
  const betaLimits = beta?.limits

  return (
    <article className="overflow-hidden rounded-v-card border border-v-fg-10 bg-v-card shadow-v-subtle">
      <div className="border-b border-v-fg-10 px-4 py-3">
        <h2 className="m-0 font-ui text-[16px] font-semibold text-v-fg">
          {activeTab === 'deposit' ? 'Déposer' : 'Retirer'}
        </h2>
        <p className="m-0 mt-1 font-ui text-[13px] text-v-fg-muted">
          APY {formatEarnApyFromBps(vault.userApyBps)} · {getPortalMorphoIntegrationLabel(vault.integrationMode)}
        </p>
      </div>

      <div className="px-4 py-4">
        {!walletReady ? (
          <div className="flex flex-col gap-3">
            <p className="m-0 font-ui text-[14px] text-v-fg-body">
              Choisissez un wallet Vancelian embedded ou liez MetaMask depuis Mon wallet pour déposer ou retirer.
            </p>
            <Button type="button" asChild className="rounded-full">
              <PortalNavLink href={PORTAL_ROUTES.walletCreate}>Créer mon wallet crypto</PortalNavLink>
            </Button>
            <Button type="button" asChild variant="outline" className="rounded-full">
              <PortalNavLink href={PORTAL_ROUTES.myWallets}>Lier MetaMask</PortalNavLink>
            </Button>
          </div>
        ) : (
          <>
            <ExecutionWalletSelector className="mb-4" />

            {showDisclaimer ? (
              <div className="mb-4 rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-950">
                <p className="m-0 font-semibold">Avertissement — premier dépôt</p>
                <p className="m-0 mt-2 leading-relaxed">{MORPHO_DISCLAIMER}</p>
                <Button
                  type="button"
                  className="mt-3 h-10 rounded-full font-ui text-[14px]"
                  onClick={acceptDisclaimer}
                  disabled={executing}
                >
                  J’ai compris et je souhaite continuer
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
                  ? 'Les dépôts sont temporairement suspendus. Vous pouvez retirer vos fonds.'
                  : 'Les retraits sont temporairement suspendus.'}
              </p>
            ) : null}

            {betaLimits && activeTab === 'deposit' ? (
              <p className="mb-4 font-ui text-[12px] text-v-fg-muted">
                Beta : min {betaLimits.minDepositUsdc} · max {betaLimits.maxDepositUsdc} USDC / tx · exposition max{' '}
                {betaLimits.maxUserExposureUsdc} USDC
              </p>
            ) : null}

            <div className="mb-4 rounded-v-card border border-v-border bg-v-card px-4 py-3 font-ui text-[13px]">
              <p className="m-0 text-v-fg-muted">Wallet</p>
              <p className="m-0 mt-1 font-medium text-v-fg">{displayWalletAddress}</p>
              <p className="m-0 mt-3 text-v-fg-muted">Position dans le vault</p>
              <p className="m-0 mt-1 font-semibold text-v-fg">{positionDisplay}</p>
              {position && position.yieldSyncStatus !== 'pending' && position.earnedYieldDisplay ? (
                <p className="m-0 mt-1 text-v-green">+{position.earnedYieldDisplay} de rendement</p>
              ) : position?.yieldSyncStatus === 'pending' ? (
                <p className="m-0 mt-1 text-v-fg-muted">{position.earnedYieldDisplay}</p>
              ) : null}
            </div>

            <label className="flex flex-col gap-2 font-ui text-[13px] text-v-fg-muted">
              Montant ({vault.asset.symbol})
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
                Retirer le maximum ({maxWithdraw} {vault.asset.symbol})
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
                'Confirmer le dépôt'
              ) : (
                'Confirmer le retrait'
              )}
            </Button>
          </>
        )}
      </div>
    </article>
  )
}
