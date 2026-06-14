'use client'

import { useCallback } from 'react'

import {
  classifySwapError,
  executionPhaseToFailurePhase,
  SwapExecutionError,
} from '@/lib/portal/swapFailure'
import {
  fetchSwapStatus,
  submitSwapApproval,
  submitSwapTx,
  type SwapExecutePayload,
} from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import {
  parseSwapChainId,
  parseSwapGasLimit,
} from '@/lib/portal/swapTxFormat'
import {
  ensureSwapTokenApproval,
  assertSwapTokenApprovalPayload,
  isSwapTokenApprovalRequired,
  resolveSwapTokenApprovalForExecution,
} from '@/lib/portal/swapTokenApproval'
import { usePortalExecutionScope } from '@/lib/portal/usePortalExecutionScope'
import { usePrivyLiveSession } from '@/lib/portal/usePrivyLiveSession'
import { waitForPrivyClientReady } from '@/lib/portal/waitForPrivyClientReady'
import { recordSwapClientTrace } from '@/lib/portal/swapClientTrace'
import type { ExecutionWalletMode } from '@/lib/wallet/useExecutionWallet'
import { generateMockExternalWalletTxHash, isLocalMockExternalWallet } from '@/lib/wallet/externalWalletMock'
import { usePortalTxSigner } from '@/lib/wallet/usePortalTxSigner'

const TERMINAL_STATUSES = new Set(['CONFIRMED', 'FAILED', 'EXPIRED'])
const POLL_INTERVAL_MS = 5_000
const POLL_TIMEOUT_MS = 300_000

// PR4 — exécution serveur (file enqueue-and-wait) : le worker tourne par ticks (~10 min) et
// un swap peut attendre une opération en cours. Fenêtre de suivi plus longue, sondage plus doux.
const AUTHORITATIVE_POLL_INTERVAL_MS = 6_000
const AUTHORITATIVE_POLL_TIMEOUT_MS = 25 * 60_000

const QUEUE_STATE_TO_PHASE: Record<string, SwapExecutionPhase> = {
  waiting_for_previous: 'queued',
  preparing: 'preparing',
  executing: 'server_executing',
  confirming: 'confirming',
  completed: 'completed',
  failed: 'failed',
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function swapStatusErrorMessage(status: { status: string; error_message?: string | null }): string {
  if (status.status === 'EXPIRED') {
    return 'Quote expirée — revenez à l’étape montant et refaites une estimation.'
  }
  if (status.status === 'FAILED') {
    return status.error_message ?? 'Swap échoué'
  }
  return status.error_message ?? 'Exécution impossible'
}

type LifiSwapExecutionOptions = {
  /** Soumission tx (défaut : route swap portal `/api/portal/swaps/{id}`). */
  submitTx?: (swapId: string, txHash: string, signingWalletAddress?: string) => Promise<unknown>
}

export function useLifiSwapExecution(
  swapMockMode = false,
  onPhaseChange?: (phase: SwapExecutionPhase) => void,
  fromAsset?: string,
  options?: LifiSwapExecutionOptions,
) {
  const privyLive = usePrivyLiveSession()
  const { isExternalWallet } = usePortalExecutionScope()
  const { sendPortalTransaction, resolveWallet } = usePortalTxSigner()
  const submitTxFn = options?.submitTx ?? submitSwapTx
  const signingMode: ExecutionWalletMode = isExternalWallet ? 'external_evm' : 'privy_embedded'

  const wrapPhaseError = useCallback((error: unknown, phase: SwapExecutionPhase, approval = false) => {
    if (error instanceof SwapExecutionError) {
      throw error
    }
    throw classifySwapError(error, executionPhaseToFailurePhase(phase), {
      approvalPhase: approval,
    })
  }, [])

  const signAndSubmit = useCallback(
    async (exec: SwapExecutePayload, fromAssetOverride?: string) => {
      const approvalAsset = fromAssetOverride ?? fromAsset
      const tx = exec.transaction
      const trace = (step: string, extra?: { phase?: string; detail?: string }) =>
        void recordSwapClientTrace(exec.swap_id, {
          step,
          phase: extra?.phase,
          detail: extra?.detail,
        })

      if (!tx?.to || !tx.data) {
        throw new SwapExecutionError({
          code: 'lifi_error',
          failurePhase: 'signing',
          technicalMessage: 'Transaction LI.FI incomplète',
        })
      }

      if (swapMockMode) {
        const hash = generateMockExternalWalletTxHash()
        await submitTxFn(exec.swap_id, hash)
        return hash
      }

      const chainId = parseSwapChainId(tx.chain_id)
      const isExternalSigning = exec.signing_wallet_mode === 'external_evm'
      const execSigningMode: ExecutionWalletMode = isExternalSigning
        ? 'external_evm'
        : 'privy_embedded'

      if (!isExternalSigning) {
        trace('privy_ready_wait_start', { phase: 'signing' })
        await waitForPrivyClientReady(
          () => {
            const session = privyLive.current
            return session.ready && session.authenticated
          },
          { timeoutMs: 30_000 },
        )
        trace('privy_ready_wait_done', { phase: 'signing' })
      }

      trace('wallet_resolve_start', { phase: 'signing' })
      const wallet = await resolveWallet(null, {
        expectedAddress: exec.signing_wallet_address ?? undefined,
        // Legs bundle : toujours le wallet indiqué par l'API (Privy embedded), pas la navbar MetaMask.
        forceMode: execSigningMode,
      })
      trace('wallet_resolve_done', {
        phase: 'signing',
        detail: `${wallet.type}:${wallet.address.slice(0, 10)}`,
      })

      if (
        exec.signing_wallet_address &&
        wallet.address.toLowerCase() !== exec.signing_wallet_address.toLowerCase()
      ) {
        throw new SwapExecutionError({
          code: 'wallet_mismatch',
          failurePhase: 'signing',
          technicalMessage: `wallet_mismatch expected=${exec.signing_wallet_address} actual=${wallet.address}`,
        })
      }

      if (isLocalMockExternalWallet(wallet)) {
        const hash = generateMockExternalWalletTxHash()
        await submitTxFn(exec.swap_id, hash)
        return hash
      }

      const tokenApproval = await resolveSwapTokenApprovalForExecution({
        approval: exec.token_approval,
        transactionTo: tx.to,
        chainId,
        walletAddress: wallet.address as `0x${string}`,
        fromAsset: approvalAsset,
      })
      if (tokenApproval && isSwapTokenApprovalRequired(tokenApproval)) {
        assertSwapTokenApprovalPayload(tokenApproval)
        onPhaseChange?.('approving')
        trace('token_approval_start', { phase: 'approving' })
        try {
          const approvalResult = await ensureSwapTokenApproval({
            chainId,
            walletAddress: wallet.address as `0x${string}`,
            approval: tokenApproval,
            assetSymbol: approvalAsset,
            sendTransaction: (approveTx, errorContext) =>
              sendPortalTransaction(approveTx, wallet, errorContext),
          })
          if (approvalResult.submitted && approvalResult.approvalTxHash) {
            await submitSwapApproval(
              exec.swap_id,
              approvalResult.approvalTxHash,
              wallet.address,
            )
          }
        } catch (error) {
          trace('token_approval_failed', {
            phase: 'approving',
            detail: error instanceof Error ? error.message.slice(0, 200) : String(error),
          })
          wrapPhaseError(error, 'approving', true)
        }
        trace('token_approval_done', { phase: 'approving' })
      }

      onPhaseChange?.('signing')
      trace('privy_embedded_tx_start', { phase: 'signing' })
      const gasLimit = parseSwapGasLimit(tx.gas_limit)

      let hash: string
      try {
        const result = await sendPortalTransaction(
          {
            chainId,
            to: tx.to as `0x${string}`,
            data: tx.data as `0x${string}`,
            value: tx.value,
            ...(gasLimit !== undefined ? { gasLimit } : {}),
          },
          wallet,
          { phase: 'swap', assetSymbol: approvalAsset },
        )
        hash = result.hash
        trace('privy_embedded_tx_done', {
          phase: 'submitting',
          detail: `tx_hash=${hash.slice(0, 12)}`,
        })
      } catch (error) {
        trace('privy_embedded_tx_failed', {
          phase: 'signing',
          detail: error instanceof Error ? error.message.slice(0, 200) : String(error),
        })
        wrapPhaseError(error, 'signing')
      }

      onPhaseChange?.('submitting')
      try {
        await submitTxFn(exec.swap_id, hash!, wallet.address)
      } catch (error) {
        trace('submit_tx_failed', {
          phase: 'submitting',
          detail: error instanceof Error ? error.message.slice(0, 200) : String(error),
        })
        wrapPhaseError(error, 'submitting')
      }
      trace('submit_tx_done', { phase: 'submitting' })
      return hash!
    },
    [
      fromAsset,
      onPhaseChange,
      privyLive,
      resolveWallet,
      sendPortalTransaction,
      signingMode,
      submitTxFn,
      swapMockMode,
      wrapPhaseError,
    ],
  )

  const pollUntilTerminal = useCallback(async (swapId: string) => {
    const started = Date.now()
    while (Date.now() - started < POLL_TIMEOUT_MS) {
      const status = await fetchSwapStatus(swapId)
      if (TERMINAL_STATUSES.has(status.status)) {
        if (status.status === 'CONFIRMED') {
          return status
        }
        throw new SwapExecutionError({
          code: status.status === 'EXPIRED' ? 'quote_expired' : 'unknown_error',
          failurePhase: 'polling',
          technicalMessage: swapStatusErrorMessage(status),
        })
      }
      await sleep(POLL_INTERVAL_MS)
    }
    const last = await fetchSwapStatus(swapId)
    if (last.status === 'CONFIRMED') {
      return last
    }
    if (TERMINAL_STATUSES.has(last.status)) {
      throw new SwapExecutionError({
        code: last.status === 'EXPIRED' ? 'quote_expired' : 'unknown_error',
        failurePhase: 'polling',
        technicalMessage: swapStatusErrorMessage(last),
      })
    }
    throw new SwapExecutionError({
      code: 'unknown_error',
      failurePhase: 'polling',
      technicalMessage: 'Délai de confirmation dépassé — l’échange peut encore aboutir.',
    })
  }, [])

  /**
   * PR4 — suivi du swap exécuté côté serveur (file enqueue-and-wait). Aucune signature
   * client : on poll GET status et on mappe ``queue_state`` vers la phase d'affichage.
   */
  const pollAuthoritativeUntilTerminal = useCallback(
    async (swapId: string) => {
      const started = Date.now()
      while (Date.now() - started < AUTHORITATIVE_POLL_TIMEOUT_MS) {
        const status = await fetchSwapStatus(swapId)
        const phase = status.queue_state ? QUEUE_STATE_TO_PHASE[status.queue_state] : undefined
        if (phase) onPhaseChange?.(phase)
        if (TERMINAL_STATUSES.has(status.status)) {
          if (status.status === 'CONFIRMED') {
            return status
          }
          throw new SwapExecutionError({
            code: status.status === 'EXPIRED' ? 'quote_expired' : 'unknown_error',
            failurePhase: 'polling',
            technicalMessage: swapStatusErrorMessage(status),
          })
        }
        await sleep(AUTHORITATIVE_POLL_INTERVAL_MS)
      }
      const last = await fetchSwapStatus(swapId)
      if (last.status === 'CONFIRMED') {
        return last
      }
      if (TERMINAL_STATUSES.has(last.status)) {
        throw new SwapExecutionError({
          code: last.status === 'EXPIRED' ? 'quote_expired' : 'unknown_error',
          failurePhase: 'polling',
          technicalMessage: swapStatusErrorMessage(last),
        })
      }
      throw new SwapExecutionError({
        code: 'unknown_error',
        failurePhase: 'polling',
        technicalMessage:
          'Délai de traitement dépassé — l’échange peut encore aboutir. Vérifiez votre wallet dans quelques minutes.',
      })
    },
    [onPhaseChange],
  )

  return { signAndSubmit, pollUntilTerminal, pollAuthoritativeUntilTerminal }
}
