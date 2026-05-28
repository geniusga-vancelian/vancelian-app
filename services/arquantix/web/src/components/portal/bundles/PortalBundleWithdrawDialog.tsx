'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'

import { useBundleLifiWithdraw } from '@/components/portal/bundles/useBundleLifiWithdraw'
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
import { fetchActiveBundleWithdrawLock } from '@/lib/portal/bundleClient'
import { formatBundleUsdcAmount } from '@/lib/portal/bundleFormat'
import {
  mapWithdrawStatusToDisplayPhase,
  splitBundleHoldings,
} from '@/lib/portal/bundleWithdrawFormat'
import {
  bundleWithdrawLockStatusLabel,
  bundleWithdrawPhaseLabel,
} from '@/lib/portal/bundleWithdrawLabels'
import {
  clearBundleWithdrawSession,
  loadBundleWithdrawSession,
  type BundleWithdrawSession,
} from '@/lib/portal/bundleWithdrawSession'
import type { PortalBundlePosition } from '@/lib/portal/cryptoWalletTypes'
import { formatCryptoMoney } from '@/lib/portal/cryptoWalletFormat'
import { invalidatePortalCache } from '@/lib/portal/portalClientCache'
import { fetchSupportedSwapAssets } from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'

type Props = {
  portfolioId: string
  portfolioName: string
  positions: PortalBundlePosition[] | undefined
  currency: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onCompleted?: () => void
}

type Step = 'form' | 'confirm' | 'executing' | 'done' | 'error' | 'blocked'

export function PortalBundleWithdrawDialog({
  portfolioId,
  portfolioName,
  positions,
  currency,
  open,
  onOpenChange,
  onCompleted,
}: Props) {
  const [step, setStep] = useState<Step>('form')
  const [fullWithdraw, setFullWithdraw] = useState(false)
  const [amount, setAmount] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [legLabel, setLegLabel] = useState<string | null>(null)
  const [swapMockMode, setSwapMockMode] = useState(false)
  const [executionPhase, setExecutionPhase] = useState<SwapExecutionPhase>('idle')
  const [remoteLockStatus, setRemoteLockStatus] = useState<string | null>(null)
  const [remoteLockPhase, setRemoteLockPhase] = useState<string | null>(null)
  const [blockedMessage, setBlockedMessage] = useState<string | null>(null)
  const [resumeSession, setResumeSession] = useState<BundleWithdrawSession | null>(null)
  const [lastPhase, setLastPhase] = useState<string | null>(null)
  const submitGuardRef = useRef(false)

  const holdings = useMemo(() => splitBundleHoldings(positions), [positions])
  const entryAsset = holdings.cashLeg?.asset ?? 'USDC'
  const maxAmount = holdings.totalWithdrawableEstimate

  const batchInProgress = step === 'executing' || submitGuardRef.current

  const reset = useCallback(() => {
    setStep('form')
    setError(null)
    setLegLabel(null)
    setExecutionPhase('idle')
    setRemoteLockStatus(null)
    setRemoteLockPhase(null)
    setBlockedMessage(null)
    setResumeSession(null)
    setLastPhase(null)
    submitGuardRef.current = false
    setFullWithdraw(false)
    setAmount('')
  }, [])

  const { runWithdraw, resumeSession: resumeWithdraw, inFlightRef } = useBundleLifiWithdraw(
    swapMockMode,
    entryAsset,
    setExecutionPhase,
    (current, total, asset) => {
      setLegLabel(`Vente ${current}/${total} — ${asset}`)
    },
  )

  const refreshLockState = useCallback(async () => {
    const active = await fetchActiveBundleWithdrawLock(portfolioId)
    if (active.status === 'active' && active.lock) {
      setRemoteLockStatus(active.lock.status)
      setRemoteLockPhase(active.lock.withdraw_phase ?? null)
      const stored = loadBundleWithdrawSession(portfolioId)
      if (stored && stored.batchId === active.lock.batch_id) {
        setResumeSession(stored)
        setBlockedMessage(null)
        return
      }
      setBlockedMessage(
        'Un retrait bundle est déjà en cours sur ce portefeuille. Terminez-le ou attendez la finalisation.',
      )
      setStep('blocked')
      return
    }
    setRemoteLockStatus(null)
    setRemoteLockPhase(null)
    setBlockedMessage(null)
    const stored = loadBundleWithdrawSession(portfolioId)
    if (stored) {
      setResumeSession(stored)
    }
  }, [portfolioId])

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
      if (!cancelled) setError('Impossible de vérifier un retrait en cours.')
    })
    return () => {
      cancelled = true
    }
  }, [open, refreshLockState, reset])

  const handleOpenChange = useCallback(
    (next: boolean) => {
      if (!next && batchInProgress) {
        const ok = window.confirm(
          'Un retrait bundle est en cours. Fermer maintenant peut laisser un batch incomplet. Continuer ?',
        )
        if (!ok) return
      }
      onOpenChange(next)
    },
    [batchInProgress, onOpenChange],
  )

  const parsedAmount = useMemo(() => {
    if (fullWithdraw) return maxAmount
    const n = Number(amount)
    return Number.isFinite(n) ? n : 0
  }, [amount, fullWithdraw, maxAmount])

  const cashCoversWithdraw = parsedAmount > 0 && parsedAmount <= holdings.cashLegQuantity + 0.0001

  const handleConfirmStep = () => {
    if (batchInProgress || inFlightRef.current) return
    if (maxAmount <= 0) {
      setError('Aucune valeur disponible à retirer.')
      return
    }
    if (!fullWithdraw) {
      const parsed = Number(amount)
      if (!Number.isFinite(parsed) || parsed <= 0) {
        setError('Montant invalide.')
        return
      }
      if (parsed > maxAmount + 0.0001) {
        setError('Montant supérieur à la valeur disponible.')
        return
      }
    }
    setError(null)
    setStep('confirm')
  }

  const runExecution = async (runner: () => Promise<unknown>) => {
    setStep('executing')
    setError(null)
    setExecutionPhase('preparing')
    submitGuardRef.current = true
    try {
      await runner()
      invalidatePortalCache('portal:crypto-wallet')
      invalidatePortalCache(`portal:crypto-wallet:bundle:${portfolioId}`)
      invalidatePortalCache('portal:dashboard')
      invalidatePortalCache('portal:markets')
      clearBundleWithdrawSession(portfolioId)
      setStep('done')
      onCompleted?.()
    } catch (err) {
      setExecutionPhase('failed')
      setError(err instanceof Error ? err.message : 'Retrait impossible')
      setStep('error')
    } finally {
      submitGuardRef.current = false
    }
  }

  const handleWithdraw = async () => {
    if (submitGuardRef.current || inFlightRef.current) return
    await runExecution(async () => {
      const outcome = await runWithdraw({
        portfolio_id: portfolioId,
        full_withdraw: fullWithdraw,
        withdraw_amount: fullWithdraw ? undefined : parsedAmount,
      })
      if (
        outcome &&
        typeof outcome === 'object' &&
        'kind' in outcome &&
        outcome.kind === 'already_pending'
      ) {
        setRemoteLockStatus(outcome.payload.lock_status ?? 'pending_signature')
        setBlockedMessage(outcome.payload.message)
        setStep('blocked')
        return
      }
      const result = outcome as { withdraw?: { status?: string; release?: { released?: boolean } } }
      const phase = mapWithdrawStatusToDisplayPhase(
        result.withdraw?.status,
        remoteLockPhase,
        result.withdraw?.release ?? null,
      )
      setLastPhase(phase)
    })
  }

  const handleResume = async () => {
    if (!resumeSession || submitGuardRef.current || inFlightRef.current) return
    await runExecution(() => resumeWithdraw(resumeSession))
  }

  const statusLabel = useMemo(() => {
    if (legLabel) return legLabel
    if (remoteLockStatus && step === 'blocked') {
      return bundleWithdrawLockStatusLabel(remoteLockStatus)
    }
    if (remoteLockPhase) {
      return bundleWithdrawPhaseLabel(
        mapWithdrawStatusToDisplayPhase(undefined, remoteLockPhase, null),
      )
    }
    if (executionPhase === 'signing') return 'Signature Privy…'
    if (executionPhase === 'submitting') return 'Soumission transaction…'
    if (executionPhase === 'bridging') return 'Transfert comptable vers Mon Trading…'
    if (executionPhase === 'completed') return 'Terminé'
    return 'Préparation…'
  }, [executionPhase, legLabel, remoteLockPhase, remoteLockStatus, step])

  const withdrawDisabled =
    batchInProgress ||
    inFlightRef.current ||
    step === 'blocked' ||
    maxAmount <= 0

  const donePhaseLabel = lastPhase
    ? bundleWithdrawPhaseLabel(lastPhase as ReturnType<typeof mapWithdrawStatusToDisplayPhase>)
    : bundleWithdrawPhaseLabel('RELEASED')

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Retirer — {portfolioName}</DialogTitle>
          <DialogDescription>
            Transfert comptable vers Mon Trading · Privy inchangé tant que le release n’est pas
            confirmé.
          </DialogDescription>
        </DialogHeader>

        {step === 'form' ? (
          <div className="flex flex-col gap-4">
            <div className="rounded-v-input border border-v-border bg-v-fg-5 px-3 py-2 font-ui text-[13px]">
              <p className="m-0 font-medium text-v-fg">Valeur disponible</p>
              <div className="mt-2 flex flex-col gap-1 text-v-fg-muted">
                <div className="flex justify-between gap-2">
                  <span>Cash leg ({entryAsset})</span>
                  <span className="text-v-fg">
                    {formatBundleUsdcAmount(holdings.cashLegQuantity)} {entryAsset}
                  </span>
                </div>
                <div className="flex justify-between gap-2">
                  <span>Actifs alloués</span>
                  <span className="text-v-fg">
                    {formatCryptoMoney(holdings.spotNotional, currency)}
                  </span>
                </div>
                <div className="mt-1 flex justify-between gap-2 border-t border-v-border pt-1 font-medium text-v-fg">
                  <span>Total estimé</span>
                  <span>{formatCryptoMoney(maxAmount, currency)}</span>
                </div>
              </div>
            </div>

            {resumeSession ? (
              <div className="rounded-v-input border border-amber-200 bg-amber-50 px-3 py-2 font-ui text-[13px] text-amber-900">
                <p className="m-0 font-medium">Retrait en cours détecté</p>
                <p className="mt-1 mb-0 text-[12px]">
                  Batch {resumeSession.batchId.slice(0, 8)}… — vous pouvez reprendre la signature.
                </p>
                <Button
                  type="button"
                  size="sm"
                  className="mt-2 h-8"
                  disabled={withdrawDisabled}
                  onClick={handleResume}
                >
                  Reprendre
                </Button>
              </div>
            ) : null}

            <div className="flex items-center gap-2">
              <input
                id="bundle-full-withdraw"
                type="checkbox"
                checked={fullWithdraw}
                onChange={(e) => setFullWithdraw(e.target.checked)}
                disabled={withdrawDisabled}
              />
              <Label htmlFor="bundle-full-withdraw" className="font-ui text-[13px]">
                Retrait total
              </Label>
            </div>

            {!fullWithdraw ? (
              <div className="flex flex-col gap-2">
                <Label htmlFor="bundle-withdraw-amount">Montant à retirer ({entryAsset})</Label>
                <Input
                  id="bundle-withdraw-amount"
                  type="number"
                  min={0}
                  step="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  disabled={withdrawDisabled}
                  placeholder={formatBundleUsdcAmount(maxAmount)}
                />
              </div>
            ) : null}

            {error ? (
              <p className="m-0 font-ui text-[13px] text-v-error">{error}</p>
            ) : null}

            <p className="m-0 font-ui text-[12px] text-v-fg-muted">
              Les fonds n’apparaîtront pas dans Mon Trading tant que le statut n’est pas{' '}
              <strong>Transféré vers Mon Trading</strong> (RELEASED).
            </p>
          </div>
        ) : null}

        {step === 'confirm' ? (
          <div className="flex flex-col gap-3 font-ui text-[13px]">
            <p className="m-0">
              Montant demandé :{' '}
              <strong>
                {fullWithdraw
                  ? `Total (${formatCryptoMoney(maxAmount, currency)})`
                  : `${formatBundleUsdcAmount(parsedAmount)} ${entryAsset}`}
              </strong>
            </p>
            {cashCoversWithdraw ? (
              <p className="m-0 rounded-v-input border border-emerald-200 bg-emerald-50 px-3 py-2 text-emerald-900">
                Le cash leg couvre le montant — release direct vers Mon Trading (sans vente spot).
              </p>
            ) : (
              <p className="m-0 rounded-v-input border border-amber-200 bg-amber-50 px-3 py-2 text-amber-900">
                Des actifs spot seront vendus via Li.FI avant le release comptable. Statuts : UNWINDING
                → READY_TO_RELEASE → RELEASED.
              </p>
            )}
            {error ? <p className="m-0 text-v-error">{error}</p> : null}
          </div>
        ) : null}

        {(step === 'executing' || step === 'blocked') && (
          <div className="flex flex-col items-center gap-3 py-4">
            {step === 'executing' ? (
              <Loader2 className="h-8 w-8 animate-spin text-v-blue" aria-hidden />
            ) : null}
            <p className="m-0 text-center font-ui text-[13px] text-v-fg">{statusLabel}</p>
            {blockedMessage ? (
              <p className="m-0 text-center font-ui text-[12px] text-v-fg-muted">{blockedMessage}</p>
            ) : null}
          </div>
        )}

        {step === 'done' ? (
          <div className="flex flex-col gap-2 font-ui text-[13px]">
            <p className="m-0 font-medium text-v-fg">{donePhaseLabel}</p>
            <p className="m-0 text-v-fg-muted">
              Mon Trading sera mis à jour au prochain rafraîchissement. Privy n’a pas bougé pour le
              release comptable.
            </p>
          </div>
        ) : null}

        {step === 'error' ? (
          <p className="m-0 font-ui text-[13px] text-v-error">{error}</p>
        ) : null}

        <DialogFooter className="gap-2 sm:gap-0">
          {step === 'form' ? (
            <>
              <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
                Annuler
              </Button>
              <Button type="button" disabled={withdrawDisabled} onClick={handleConfirmStep}>
                Continuer
              </Button>
            </>
          ) : null}
          {step === 'confirm' ? (
            <>
              <Button type="button" variant="outline" onClick={() => setStep('form')}>
                Retour
              </Button>
              <Button type="button" disabled={withdrawDisabled} onClick={() => void handleWithdraw()}>
                Confirmer le retrait
              </Button>
            </>
          ) : null}
          {(step === 'done' || step === 'error' || step === 'blocked') && (
            <Button type="button" onClick={() => handleOpenChange(false)}>
              Fermer
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
