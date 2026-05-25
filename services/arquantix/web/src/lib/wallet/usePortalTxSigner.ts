'use client'

import { useCallback } from 'react'
import type { ConnectedWallet, User } from '@privy-io/react-auth'
import { useCreateWallet, usePrivy, useSendTransaction, useWallets } from '@privy-io/react-auth'
import { useAccount, useSendTransaction as useWagmiSendTransaction, useSwitchChain } from 'wagmi'

import { resolvePortalSwapSigningWallet } from '@/lib/portal/resolvePortalSwapSigningWallet'
import { normalizeSwapTxValue, normalizeTxHash } from '@/lib/portal/swapTxFormat'
import type { ExecutionWallet } from '@/lib/wallet/executionWalletTypes'
import {
  generateMockExternalWalletTxHash,
  isLocalMockExternalWallet,
} from '@/lib/wallet/externalWalletMock'
import { useExecutionWallet } from '@/lib/wallet/useExecutionWallet'

export type PortalTxRequest = {
  chainId: number
  to: `0x${string}`
  data: `0x${string}`
  value?: bigint | string | number
  gasLimit?: bigint
}

function normalizeTxValueBigInt(value?: bigint | string | number): bigint {
  if (value === undefined) return BigInt(0)
  if (typeof value === 'bigint') return value
  if (typeof value === 'number') return BigInt(value)
  const raw = value.trim()
  if (!raw) return BigInt(0)
  if (raw.startsWith('0x')) return BigInt(raw)
  return BigInt(raw)
}

function normalizeTxValueHex(value?: bigint | string | number): `0x${string}` {
  return normalizeSwapTxValue(normalizeTxValueBigInt(value).toString())
}

export function usePortalTxSigner() {
  const { ready, authenticated, user } = usePrivy()
  const { sendTransaction: sendPrivyTransaction } = useSendTransaction()
  const { wallets } = useWallets()
  const { createWallet } = useCreateWallet()
  const { sendTransactionAsync: sendWagmiTransaction } = useWagmiSendTransaction()
  const { switchChainAsync } = useSwitchChain()
  const { address: wagmiAddress } = useAccount()
  const { mode, resolveExecutionWallet } = useExecutionWallet()

  const resolveWallet = useCallback(
    async (override?: ExecutionWallet | null): Promise<ExecutionWallet> => {
      if (override) return override
      if (mode === 'external_evm') {
        const external = await resolveExecutionWallet()
        if (external?.type === 'external_evm') return external
        throw new Error(
          'Aucun wallet externe vérifié. Connectez MetaMask depuis Mon wallet et signez le message de vérification.',
        )
      }

      const privyWallet = await resolvePortalSwapSigningWallet({
        ready,
        authenticated,
        user,
        wallets,
        createWallet: async () => {
          const created = await createWallet()
          return { address: created.address }
        },
      })

      return {
        type: 'privy_embedded',
        address: privyWallet.address,
      }
    },
    [authenticated, createWallet, mode, ready, resolveExecutionWallet, user, wallets],
  )

  const switchToChain = useCallback(
    async (wallet: ExecutionWallet, chainId: number) => {
      if (wallet.type === 'external_evm' && isLocalMockExternalWallet(wallet)) {
        return
      }

      if (wallet.type === 'external_evm') {
        await switchChainAsync({ chainId })
        return
      }

      const connected = wallets.find(
        (row) => row.address.toLowerCase() === wallet.address.toLowerCase(),
      ) as ConnectedWallet | undefined
      if (connected?.switchChain) {
        try {
          await connected.switchChain(chainId)
        } catch {
          /* déjà sur la bonne chaîne */
        }
      }
    },
    [switchChainAsync, wallets],
  )

  const sendPortalTransaction = useCallback(
    async (tx: PortalTxRequest, overrideWallet?: ExecutionWallet | null) => {
      const wallet = await resolveWallet(overrideWallet)
      await switchToChain(wallet, tx.chainId)

      if (wallet.type === 'external_evm') {
        if (isLocalMockExternalWallet(wallet)) {
          return { hash: generateMockExternalWalletTxHash(), wallet }
        }

        if (!wagmiAddress || wagmiAddress.toLowerCase() !== wallet.address.toLowerCase()) {
          throw new Error(
            'Le wallet MetaMask connecté ne correspond pas au wallet externe vérifié. Reconnectez le bon wallet.',
          )
        }

        const hash = await sendWagmiTransaction({
          chainId: tx.chainId,
          to: tx.to,
          data: tx.data,
          value: normalizeTxValueBigInt(tx.value),
          ...(tx.gasLimit !== undefined ? { gas: tx.gasLimit } : {}),
        })
        return { hash: normalizeTxHash(hash), wallet }
      }

      const { hash } = await sendPrivyTransaction(
        {
          chainId: tx.chainId,
          to: tx.to,
          data: tx.data,
          value: normalizeTxValueHex(tx.value),
          ...(tx.gasLimit !== undefined ? { gasLimit: tx.gasLimit } : {}),
        },
        {
          address: wallet.address,
          sponsor: true,
          uiOptions: { showWalletUIs: false },
        },
      )
      return { hash: normalizeTxHash(hash), wallet }
    },
    [resolveWallet, sendPrivyTransaction, sendWagmiTransaction, switchToChain, wagmiAddress],
  )

  return { sendPortalTransaction, resolveWallet, mode }
}

export type { ConnectedWallet, User }
