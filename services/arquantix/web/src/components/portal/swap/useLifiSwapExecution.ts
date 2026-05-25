'use client'

import { useCallback } from 'react'

import {
  fetchSwapStatus,
  submitSwapTx,
  type SwapExecutePayload,
} from '@/lib/portal/swapClient'
import {
  parseSwapChainId,
  parseSwapGasLimit,
} from '@/lib/portal/swapTxFormat'
import { generateMockExternalWalletTxHash, isLocalMockExternalWallet } from '@/lib/wallet/externalWalletMock'
import { usePortalTxSigner } from '@/lib/wallet/usePortalTxSigner'

const TERMINAL_STATUSES = new Set(['CONFIRMED', 'FAILED', 'EXPIRED'])
const POLL_INTERVAL_MS = 5_000
const POLL_TIMEOUT_MS = 300_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function useLifiSwapExecution(swapMockMode = false) {
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
      )

      await submitSwapTx(exec.swap_id, hash)
      return hash
    },
    [resolveWallet, sendPortalTransaction, swapMockMode],
  )

  const pollUntilTerminal = useCallback(async (swapId: string) => {
    const started = Date.now()
    while (Date.now() - started < POLL_TIMEOUT_MS) {
      const status = await fetchSwapStatus(swapId)
      if (TERMINAL_STATUSES.has(status.status)) {
        return status
      }
      await sleep(POLL_INTERVAL_MS)
    }
    return fetchSwapStatus(swapId)
  }, [])

  return { signAndSubmit, pollUntilTerminal }
}
