'use client'

import { useCallback } from 'react'
import { useCreateWallet, usePrivy, useSendTransaction, useWallets } from '@privy-io/react-auth'

import { resolvePortalSwapSigningWallet } from '@/lib/portal/resolvePortalSwapSigningWallet'
import {
  fetchSwapStatus,
  submitSwapTx,
  type SwapExecutePayload,
} from '@/lib/portal/swapClient'
import {
  normalizeSwapTxValue,
  normalizeTxHash,
  parseSwapChainId,
  parseSwapGasLimit,
} from '@/lib/portal/swapTxFormat'

const TERMINAL_STATUSES = new Set(['CONFIRMED', 'FAILED', 'EXPIRED'])
const POLL_INTERVAL_MS = 5_000
const POLL_TIMEOUT_MS = 300_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function useLifiSwapExecution(swapMockMode = false) {
  const { ready, authenticated, user } = usePrivy()
  const { sendTransaction } = useSendTransaction()
  const { wallets } = useWallets()
  const { createWallet } = useCreateWallet()

  const signAndSubmit = useCallback(
    async (exec: SwapExecutePayload) => {
      const tx = exec.transaction
      if (!tx?.to || !tx.data) {
        throw new Error('Transaction LI.FI incomplète')
      }

      if (swapMockMode) {
        const hash = `0xmock${crypto.randomUUID().replace(/-/g, '')}`
        await submitSwapTx(exec.swap_id, hash)
        return hash
      }

      const chainId = parseSwapChainId(tx.chain_id)
      const wallet = await resolvePortalSwapSigningWallet({
        ready,
        authenticated,
        user,
        wallets,
        createWallet: async () => {
          const created = await createWallet()
          return { address: created.address }
        },
      })

      if (wallet.switchChain) {
        try {
          await wallet.switchChain(chainId)
        } catch {
          /* déjà sur la bonne chaîne ou switch géré par Privy */
        }
      }

      const gasLimit = parseSwapGasLimit(tx.gas_limit)
      const { hash } = await sendTransaction(
        {
          chainId,
          to: tx.to as `0x${string}`,
          data: tx.data as `0x${string}`,
          value: normalizeSwapTxValue(tx.value),
          ...(gasLimit !== undefined ? { gasLimit } : {}),
        },
        { address: wallet.address, sponsor: true },
      )

      const normalizedHash = normalizeTxHash(hash)
      await submitSwapTx(exec.swap_id, normalizedHash)
      return normalizedHash
    },
    [authenticated, createWallet, ready, sendTransaction, swapMockMode, user, wallets],
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
