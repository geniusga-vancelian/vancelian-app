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
import type { ExecutionWalletMode } from '@/lib/wallet/useExecutionWallet'
import { generateMockExternalWalletTxHash, isLocalMockExternalWallet } from '@/lib/wallet/externalWalletMock'
import { usePortalTxSigner } from '@/lib/wallet/usePortalTxSigner'

const TERMINAL_STATUSES = new Set(['CONFIRMED', 'FAILED', 'EXPIRED'])
const POLL_INTERVAL_MS = 5_000
const POLL_TIMEOUT_MS = 300_000

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

      if (!isExternalSigning) {
        await waitForPrivyClientReady(
          () => {
            const session = privyLive.current
            return session.ready && session.authenticated
          },
          { timeoutMs: 30_000 },
        )
      }

      const wallet = await resolveWallet(null, {
        expectedAddress: exec.signing_wallet_address ?? undefined,
        // Scope navbar (Privy par défaut), pas le mode stale en localStorage.
        forceMode: signingMode,
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
          wrapPhaseError(error, 'approving', true)
        }
      }

      onPhaseChange?.('signing')
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
      } catch (error) {
        wrapPhaseError(error, 'signing')
      }

      onPhaseChange?.('submitting')
      try {
        await submitTxFn(exec.swap_id, hash!, wallet.address)
      } catch (error) {
        wrapPhaseError(error, 'submitting')
      }
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

  return { signAndSubmit, pollUntilTerminal }
}
