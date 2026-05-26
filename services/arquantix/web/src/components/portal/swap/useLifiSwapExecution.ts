'use client'

import { useCallback } from 'react'

import {
  fetchSwapStatus,
  submitSwapTx,
  type SwapExecutePayload,
} from '@/lib/portal/swapClient'
import type { SwapExecutionPhase } from '@/lib/portal/swapFlowTypes'
import {
  parseSwapChainId,
  parseSwapGasLimit,
} from '@/lib/portal/swapTxFormat'
import { ensureSwapTokenApproval, assertSwapTokenApprovalPayload } from '@/lib/portal/swapTokenApproval'
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

export function useLifiSwapExecution(
  swapMockMode = false,
  onPhaseChange?: (phase: SwapExecutionPhase) => void,
  fromAsset?: string,
) {
  const { sendPortalTransaction, resolveWallet } = usePortalTxSigner()

  const signAndSubmit = useCallback(
    async (exec: SwapExecutePayload) => {
      const tx = exec.transaction
      if (!tx?.to || !tx.data) {
        throw new Error('Transaction LI.FI incomplète')
      }

      if (swapMockMode) {
        const hash = generateMockExternalWalletTxHash()
        await submitSwapTx(exec.swap_id, hash)
        return hash
      }

      const chainId = parseSwapChainId(tx.chain_id)
      const wallet = await resolveWallet()

      if (
        exec.signing_wallet_address &&
        wallet.address.toLowerCase() !== exec.signing_wallet_address.toLowerCase()
      ) {
        throw new Error(
          'Le wallet connecté ne correspond pas au quote LI.FI. Revenez à l’étape montant et refaites une estimation.',
        )
      }

      if (isLocalMockExternalWallet(wallet)) {
        const hash = generateMockExternalWalletTxHash()
        await submitSwapTx(exec.swap_id, hash)
        return hash
      }

      if (exec.token_approval?.required) {
        assertSwapTokenApprovalPayload(exec.token_approval)
        onPhaseChange?.('approving')
        await ensureSwapTokenApproval({
          chainId,
          walletAddress: wallet.address as `0x${string}`,
          approval: exec.token_approval,
          assetSymbol: fromAsset,
          sendTransaction: (approveTx, errorContext) =>
            sendPortalTransaction(approveTx, wallet, errorContext),
        })
      }

      onPhaseChange?.('signing')
      const gasLimit = parseSwapGasLimit(tx.gas_limit)

      const { hash } = await sendPortalTransaction(
        {
          chainId,
          to: tx.to as `0x${string}`,
          data: tx.data as `0x${string}`,
          value: tx.value,
          ...(gasLimit !== undefined ? { gasLimit } : {}),
        },
        wallet,
        { phase: 'swap', assetSymbol: fromAsset },
      )

      onPhaseChange?.('submitting')
      await submitSwapTx(exec.swap_id, hash)
      return hash
    },
    [fromAsset, onPhaseChange, resolveWallet, sendPortalTransaction, swapMockMode],
  )

  const pollUntilTerminal = useCallback(async (swapId: string) => {
    const started = Date.now()
    while (Date.now() - started < POLL_TIMEOUT_MS) {
      const status = await fetchSwapStatus(swapId)
      if (TERMINAL_STATUSES.has(status.status)) {
        if (status.status === 'CONFIRMED') {
          return status
        }
        throw new Error(swapStatusErrorMessage(status))
      }
      await sleep(POLL_INTERVAL_MS)
    }
    const last = await fetchSwapStatus(swapId)
    if (last.status === 'CONFIRMED') {
      return last
    }
    if (TERMINAL_STATUSES.has(last.status)) {
      throw new Error(swapStatusErrorMessage(last))
    }
    return last
  }, [])

  return { signAndSubmit, pollUntilTerminal }
}
