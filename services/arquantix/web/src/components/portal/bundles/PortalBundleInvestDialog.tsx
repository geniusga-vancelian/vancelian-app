'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { useBundleLifiInvest } from '@/components/portal/bundles/useBundleLifiInvest'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  fetchActiveBundleInvestLock,
  previewBundleInvest,
  type BundleInvestPreviewPayload,
} from '@/lib/portal/bundleClient'
import {
  displayBundleAssetSymbol,
  formatBundleTargetWeight,
  formatBundleUsdcAmount,
} from '@/lib/portal/bundleFormat'
import {
  bundleExecutionPhaseLabel,
  bundleLockStatusLabel,
} from '@/lib/portal/bundleInvestLabels'
import {
  clearBundleInvestSession,
  loadBundleInvestSession,
  type BundleInvestSession,
} from '@/lib/portal/bundleInvestSession'
import type { PortalCryptoBundle } from '@/lib/portal/marketsTypes'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'

const PILOT_ENTRY_ASSETS = ['USDC', 'EURC'] as const

type Props = {
  bundle: PortalCryptoBundle
  open: boolean
  onOpenChange: (open: boolean) => void
}

type Step = 'form' | 'preview' | 'executing' | 'done' | 'error' | 'blocked'

export function PortalBundleInvestDialog({ bundle, open, onOpenChange }: Props) {
  const [step, setStep] = useState<Step>('form')
  const [fundingAsset, setFundingAsset] = useState<string>(bundle.entryAssetDefault ?? 'USDC')
  const [amount, setAmount] = useState('')
  const [preview, setPreview] = useState<BundleInvestPreviewPayload | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [legLabel, setLegLabel] = useState<string | null>(null)
  const [swapMockMode, setSwapMockMode] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [remoteLockStatus, setRemoteLockStatus] = useState<string | null>(null)
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)
  const [resumeSession, setResumeSession] = useState<BundleInvestSession | null>(null)
  const submitGuardRef = useRef(false)

  const entryOptions = useMemo(() => {
    const allowed = bundle.entryAssetsAllowed?.length
      ? bundle.entryAssetsAllowed
      : [...PILOT_ENTRY_ASSETS]
    return allowed
      .map((a) => a.toUpperCase())
      .filter((a) => PILOT_ENTRY_ASSETS.includes(a as (typeof PILOT_ENTRY_ASSETS)[number]))
  }, [bundle.entryAssetsAllowed])

  const batchInProgress = step === 'executing' || submitGuardRef.current

  const reset = useCallback(() => {
    setStep('form')
    setPreview(null)
    setError(null)
    setLegLabel(null)
    setExecutionPhase('idle')
    setRemoteLockStatus(null)
    setBlockedMessage(null)
    setResumeSession(null)
    submitGuardRef.current = false
    setAmount('')
    setFundingAsset(bundle.entryAssetDefault ?? entryOptions[0] ?? 'USDC')
  }, [bundle.entryAssetDefault, entryOptions])

  const { runInvest, resumeSession: resumeInvest, inFlightRef } = useBundleLifiInvest(
    swapMockMode,
    fundingAsset,
    setExecutionPhase,
    (current, total, asset) => {
      setLegLabel(`Leg ${current}/${total} — ${asset}`)
    },
  )

  const portfolioReady = Boolean(bundle.portfolioId?.trim())

  const refreshLockState = useCallback(async () => {
    if (!portfolioReady) return
    const active = await fetchActiveBundleInvestLock(bundle.portfolioId!)
    if (active.status === 'active' && active.lock) {
      setRemoteLockStatus(active.lock.status)
      const stored = loadBundleInvestSession(bundle.portfolioId!)
      if (stored && stored.batchId === active.lock.batch_id) {
        setResumeSession(stored)
        setBlockedMessage(null)
        return
      }
      setBlockedMessage(
        'Un investissement bundle est déjà en cours sur ce portefeuille. Terminez-le ou attendez la finalisation.',
      )
      setStep('blocked')
      return
    }
    setRemoteLockStatus(null)
    setBlockedMessage(null)
    const stored = loadBundleInvestSession(bundle.portfolioId!)
    if (stored) {
      setResumeSession(stored)
    }
  }, [bundle.portfolioId, portfolioReady])

  useEffect(() => {
    if (!open) {
      reset()
      return
    }
    let cancelled = false
    fetchSupportedSwapAssets()
      .then((catalog) => {
        if (!cancelled) setSwapMockMode(Boolean(catalog.mock_mode))
      })
      .catch(() => {
        if (!cancelled) setSwapMockMode(false)
      })
    refreshLockState().catch(() => {
      if (!cancelled) setError('Impossible de vérifier un investissement en cours.')
    })
    return () => {
      cancelled = true
    }
  }, [open, refreshLockState, reset])

  const handleOpenChange = useCallback(
    (next: boolean) => {
      if (!next && batchInProgress) {
        const ok = window.confirm(
          'Un investissement bundle est en cours. Fermer maintenant peut laisser un batch incomplet. Continuer ?',
        )
        if (!ok) return
      }
      onOpenChange(next)
    },
    [batchInProgress, onOpenChange],
  )

  const handlePreview = async () => {
    if (!portfolioReady || batchInProgress || inFlightRef.current) return
    const parsed = Number(amount)
    if (!Number.isFinite(parsed) || parsed <= 0) {
      setError('Montant invalide.')
      return
    }
    setPreviewLoading(true)
    setError(null)
    try {
      const result = await previewBundleInvest({
        portfolio_id: bundle.portfolioId!,
        funding_asset: fundingAsset,
        funding_amount: parsed,
      })
      setPreview(result)
      setStep('preview')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prévisualisation impossible')
    } finally {
      setPreviewLoading(false)
    }
  }

  const runExecution = async (runner: () => Promise<unknown>) => {
    setStep('executing')
    setError(null)
    setExecutionPhase('preparing')
    submitGuardRef.current = true
    try {
      await runner()
      invalidatePortalCache('portal:markets')
      invalidatePortalCache('portal:crypto-wallet')
      invalidatePortalCache('portal:dashboard')
      if (portfolioReady) {
        clearBundleInvestSession(bundle.portfolioId!)
      }
      setStep('done')
    } catch (err) {
      setExecutionPhase('failed')
      setError(err instanceof Error ? err.message : 'Investissement impossible')
      setStep('error')
    } finally {
      submitGuardRef.current = false
    }
  }

  const handleInvest = async () => {
    if (!portfolioReady || submitGuardRef.current || inFlightRef.current) return
    const parsed = Number(amount)
    if (!Number.isFinite(parsed) || parsed <= 0) return

    await runExecution(async () => {
      const outcome = await runInvest({
        portfolio_id: bundle.portfolioId!,
        funding_asset: fundingAsset,
        funding_amount: parsed,
      })
      if (outcome && typeof outcome === 'object' && 'kind' in outcome && outcome.kind === 'already_pending') {
        setRemoteLockStatus(outcome.payload.lock_status ?? 'pending_signature')
        setBlockedMessage(outcome.payload.message)
        setStep('blocked')
        return
      }
    })
  }

  const handleResume = async () => {
    if (!resumeSession || submitGuardRef.current || inFlightRef.current) return
    await runExecution(() => resumeInvest(resumeSession))
  }

  const statusLabel = useMemo(() => {
    if (legLabel) return legLabel
    if (remoteLockStatus && step === 'blocked') {
      return bundleLockStatusLabel(remoteLockStatus)
    }
    return bundleExecutionPhaseLabel(executionPhase)
  }, [executionPhase, legLabel, remoteLockStatus, step])

  const investDisabled =
    !portfolioReady ||
    previewLoading ||
    batchInProgress ||
    inFlightRef.current ||
    step === 'blocked' ||
    (step === 'preview' && preview?.preview_status === 'invalid')

  const entryAssetLabel = preview?.entry_asset_used ?? fundingAsset

  const previewWarning = useMemo(() => {
    if (!preview || preview.preview_status === 'ok') return null
    if (preview.preview_status === 'partial') {
      return 'Certains actifs ne sont pas disponibles pour la cotation — l’allocation pourrait être partielle.'
    }
    if (preview.warnings?.length) {
      return preview.warnings[0]
    }
    return 'Prévisualisation indisponible pour ce montant.'
  }, [preview])

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Investir — {bundle.title}</DialogTitle>
          <DialogDescription>
            Pilote Base · LI.FI · signature Privy dans le navigateur.
          </DialogDescription>
        </DialogHeader>

        {step === 'form' ? (
          <div className="flex flex-col gap-4">
            {!portfolioReady ? (
              <p className="m-0 font-ui text-[13px] text-v-error">
                Ce bundle n’est pas encore provisionné sur votre compte. Rechargez la page Marchés.
              </p>
            ) : null}
            {resumeSession ? (
              <div className="rounded-v-input border border-amber-200 bg-amber-50 px-3 py-2 font-ui text-[13px] text-amber-900">
                <p className="m-0 font-medium">Investissement en cours détecté</p>
                <p className="mt-1 mb-0 text-[12px]">
                  Batch {resumeSession.batchId.slice(0, 8)}… — vous pouvez reprendre la signature.
                </p>
                <Button
                  type="button"
                  size="sm"
                  className="mt-2 h-8"
                  disabled={investDisabled}
                  onClick={handleResume}
                >
                  Reprendre
                </Button>
              </div>
            ) : null}
            <div className="flex flex-col gap-2">
              <Label htmlFor="bundle-entry-asset">Actif d’entrée</Label>
              <select
                id="bundle-entry-asset"
                className="h-10 rounded-v-input border border-v-border bg-v-bg px-3 font-ui text-[14px] text-v-fg"
                value={fundingAsset}
                onChange={(e) => setFundingAsset(e.target.value)}
                disabled={!portfolioReady || batchInProgress}
              >
                {entryOptions.map((asset) => (
                  <option key={asset} value={asset}>
                    {asset}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="bundle-amount">Montant ({fundingAsset})</Label>
              <Input
                id="bundle-amount"
                type="number"
                min="0"
                step="any"
                placeholder="100"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                disabled={!portfolioReady || batchInProgress}
              />
            </div>
            {error ? <p className="m-0 text-[13px] text-v-error">{error}</p> : null}
          </div>
        ) : null}

        {step === 'blocked' ? (
          <div className="flex flex-col gap-3">
            <p className="m-0 font-ui text-[14px] text-v-fg">{blockedMessage}</p>
            <p className="m-0 font-ui text-[13px] text-v-fg-muted">{statusLabel}</p>
            {resumeSession ? (
              <Button type="button" disabled={investDisabled} onClick={handleResume}>
                Reprendre l’investissement
              </Button>
            ) : null}
          </div>
        ) : null}

        {step === 'preview' && preview ? (
          <div className="flex max-h-[40vh] flex-col gap-2 overflow-y-auto">
            <p className="m-0 font-ui text-[13px] text-v-fg-muted">
              Entrée estimée : {formatBundleUsdcAmount(preview.estimated_entry_asset_amount)}{' '}
              {entryAssetLabel}
            </p>
            {previewWarning ? (
              <p className="m-0 rounded-v-input border border-amber-200 bg-amber-50 px-3 py-2 font-ui text-[12px] text-amber-900">
                {previewWarning}
              </p>
            ) : null}
            <ul className="m-0 list-none space-y-1 p-0">
              {(preview.allocations ?? []).map((row) => {
                const label =
                  row.asset_display?.trim() ||
                  displayBundleAssetSymbol(row.asset)
                const inputUsdc = formatBundleUsdcAmount(row.estimated_input_amount)
                return (
                  <li
                    key={`${row.asset}-${row.target_weight}`}
                    className="flex justify-between gap-3 font-ui text-[12px] text-v-fg-body"
                  >
                    <span>
                      {label}{' '}
                      <span className="text-v-fg-muted">
                        ({formatBundleTargetWeight(row.target_weight)})
                      </span>
                    </span>
                    <span className="shrink-0 tabular-nums">
                      {inputUsdc} {entryAssetLabel}
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>
        ) : null}

        {step === 'executing' ? (
          <div className="flex flex-col items-center gap-3 py-6">
            <Loader2 className="h-8 w-8 animate-spin text-v-fg-muted" />
            <p className="m-0 text-center font-ui text-[14px] text-v-fg">{statusLabel}</p>
          </div>
        ) : null}

        {step === 'done' ? (
          <p className="m-0 font-ui text-[14px] text-v-fg">
            Investissement bundle terminé. Les positions seront visibles après rafraîchissement.
          </p>
        ) : null}

        {step === 'error' ? (
          <p className="m-0 font-ui text-[14px] text-v-error">{error ?? 'Erreur'}</p>
        ) : null}

        <DialogFooter className="gap-2 sm:gap-2">
          {step === 'form' ? (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => handleOpenChange(false)}
                disabled={batchInProgress}
              >
                Annuler
              </Button>
              <Button type="button" onClick={handlePreview} disabled={investDisabled}>
                {previewLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Estimation…
                  </>
                ) : (
                  'Prévisualiser'
                )}
              </Button>
            </>
          ) : null}
          {step === 'preview' ? (
            <>
              <Button
                type="button"
                variant="outline"
                onClick={() => setStep('form')}
                disabled={batchInProgress}
              >
                Retour
              </Button>
              <Button type="button" onClick={handleInvest} disabled={investDisabled}>
                Confirmer et investir
              </Button>
            </>
          ) : null}
          {step === 'done' || step === 'error' || step === 'blocked' ? (
            <Button
              type="button"
              onClick={() => handleOpenChange(false)}
              disabled={step === 'blocked' && batchInProgress}
            >
              Fermer
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
