'use client'

import { useCallback } from 'react'
import type { ConnectedWallet, User } from '@privy-io/react-auth'
import { useAuthorizationSignature, useCreateWallet } from '@privy-io/react-auth'
import { useAccount, useSendTransaction as useWagmiSendTransaction, useSwitchChain } from 'wagmi'

import { getPrivyAppId } from '@/lib/portal/privyConfig'
import {
  buildPrivyAuthorizationSignatureInput,
  buildPrivyEthSendTransactionRpcBody,
} from '@/lib/portal/privySponsoredRpcRequest'
import { resolvePortalSwapSigningWallet } from '@/lib/portal/resolvePortalSwapSigningWallet'
import { resolvePrivyEmbeddedWalletId } from '@/lib/portal/resolvePrivyEmbeddedWalletId'
import { sendPortalPrivySponsoredTransaction } from '@/lib/portal/privySponsoredTxClient'
import { normalizeTxHash } from '@/lib/portal/swapTxFormat'
import { usePrivyLiveSession } from '@/lib/portal/usePrivyLiveSession'
import type { ExecutionWallet } from '@/lib/wallet/executionWalletTypes'
import {
  generateMockExternalWalletTxHash,
  isLocalMockExternalWallet,
} from '@/lib/wallet/externalWalletMock'
import {
  requireExternalWalletChain,
  waitForWagmiChainId,
  portalEvmChainLabel,
} from '@/lib/wallet/portalEvmChain'
import {
  formatPortalWalletError,
  isPortalWalletRequestExpiredError,
  type PortalWalletErrorContext,
} from '@/lib/wallet/portalWalletErrors'
import { useExecutionWallet, type ExecutionWalletMode } from '@/lib/wallet/useExecutionWallet'

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

function isAlreadyOnTargetChainError(error: unknown): boolean {
  const haystack = `${error instanceof Error ? error.message : String(error)}`.toLowerCase()
  return (
    haystack.includes('same network') ||
    haystack.includes('already on') ||
    (haystack.includes('already') && haystack.includes('chain'))
  )
}

export function usePortalTxSigner() {
  const privyLive = usePrivyLiveSession()
  const { generateAuthorizationSignature } = useAuthorizationSignature()
  const { createWallet } = useCreateWallet()
  const { sendTransactionAsync: sendWagmiTransaction } = useWagmiSendTransaction()
  const { switchChainAsync } = useSwitchChain()
  const { address: wagmiAddress } = useAccount()
  const { mode, resolveExecutionWallet } = useExecutionWallet()

  const resolveWallet = useCallback(
    async (
      override?: ExecutionWallet | null,
      options?: { expectedAddress?: string | null; forceMode?: ExecutionWalletMode },
    ): Promise<ExecutionWallet> => {
      if (
        override &&
        (override.type !== 'privy_embedded' || Boolean(override.privyWalletId?.trim()))
      ) {
        return override
      }
      const effectiveMode = options?.forceMode ?? mode
      if (effectiveMode === 'external_evm') {
        const external = await resolveExecutionWallet()
        if (external?.type === 'external_evm') return external
        throw new Error(
          'Aucun wallet externe vérifié. Connectez MetaMask depuis Mon wallet et signez le message de vérification.',
        )
      }

      const session = privyLive.current
      const privyWallet = await resolvePortalSwapSigningWallet({
        ready: session.ready,
        authenticated: session.authenticated,
        user: session.user,
        wallets: session.wallets,
        expectedAddress: options?.expectedAddress,
        createWallet: async () => {
          const created = await createWallet()
          return { address: created.address }
        },
      })

      return {
        type: 'privy_embedded',
        address: privyWallet.address,
        privyWalletId: resolvePrivyEmbeddedWalletId({
          user: privyLive.current.user,
          wallets: privyLive.current.wallets,
          walletAddress: privyWallet.address,
        }),
      }
    },
    [createWallet, mode, privyLive, resolveExecutionWallet],
  )

  const switchToChain = useCallback(
    async (wallet: ExecutionWallet, chainId: number) => {
      if (wallet.type === 'external_evm' && isLocalMockExternalWallet(wallet)) {
        return
      }

      if (wallet.type === 'external_evm') {
        requireExternalWalletChain(chainId)
        await switchChainAsync({ chainId })
        await waitForWagmiChainId(chainId)
        return
      }

      const wallets = privyLive.current.wallets
      const connected = wallets.find(
        (row) => row.address.toLowerCase() === wallet.address.toLowerCase(),
      ) as ConnectedWallet | undefined
      if (connected?.switchChain) {
        try {
          await connected.switchChain(chainId)
        } catch (error) {
          if (!isAlreadyOnTargetChainError(error)) {
            throw new Error(
              `Impossible de basculer le wallet Vancelian sur ${portalEvmChainLabel(chainId)}. Changez de réseau dans la navbar puis réessayez.`,
            )
          }
        }
      }
    },
    [privyLive, switchChainAsync],
  )

  const sendExternalWalletTransaction = useCallback(
    async (tx: PortalTxRequest, wallet: ExecutionWallet) => {
      if (isLocalMockExternalWallet(wallet)) {
        return { hash: generateMockExternalWalletTxHash(), wallet }
      }

      if (!wagmiAddress || wagmiAddress.toLowerCase() !== wallet.address.toLowerCase()) {
        throw new Error(
          'Le wallet MetaMask connecté ne correspond pas au wallet externe vérifié. Reconnectez le bon wallet.',
        )
      }

      requireExternalWalletChain(tx.chainId)

      const submit = async () => {
        const hash = await sendWagmiTransaction({
          chainId: tx.chainId,
          to: tx.to,
          data: tx.data,
          value: normalizeTxValueBigInt(tx.value),
          ...(tx.gasLimit !== undefined ? { gas: tx.gasLimit } : {}),
        })
        return normalizeTxHash(hash)
      }

      try {
        const hash = await submit()
        return { hash, wallet }
      } catch (error) {
        if (!isPortalWalletRequestExpiredError(error)) {
          throw error
        }
        const hash = await submit()
        return { hash, wallet }
      }
    },
    [sendWagmiTransaction, wagmiAddress],
  )

  const sendPortalTransaction = useCallback(
    async (
      tx: PortalTxRequest,
      overrideWallet?: ExecutionWallet | null,
      errorContext?: Omit<PortalWalletErrorContext, 'walletMode' | 'chainId'>,
    ) => {
      let wallet: ExecutionWallet | null = null
      try {
        wallet = await resolveWallet(overrideWallet)
        await switchToChain(wallet, tx.chainId)

        if (wallet.type === 'external_evm') {
          return await sendExternalWalletTransaction(tx, wallet)
        }

        const privyWalletId = wallet.privyWalletId?.trim()
        if (!privyWalletId) {
          throw new Error(
            'Wallet Vancelian introuvable pour cette session. Déconnectez-vous puis reconnectez-vous.',
          )
        }

        const rpcBody = buildPrivyEthSendTransactionRpcBody({
          chainId: tx.chainId,
          to: tx.to,
          data: tx.data,
          value: tx.value,
          gasLimit: tx.gasLimit,
        })
        const { signature } = await generateAuthorizationSignature(
          buildPrivyAuthorizationSignatureInput({
            appId: getPrivyAppId(),
            privyWalletId,
            rpcBody,
          }),
        )

        const { hash } = await sendPortalPrivySponsoredTransaction({
          chainId: tx.chainId,
          to: tx.to,
          data: tx.data,
          value: tx.value,
          gasLimit: tx.gasLimit,
          walletAddress: wallet.address,
          privyWalletId,
          authorizationSignature: signature,
        })
        return { hash: normalizeTxHash(hash), wallet }
      } catch (error) {
        throw new Error(
          formatPortalWalletError(error, {
            walletMode: wallet?.type,
            chainId: tx.chainId,
            ...errorContext,
          }),
        )
      }
    },
    [generateAuthorizationSignature, resolveWallet, sendExternalWalletTransaction, switchToChain],
  )

  return { sendPortalTransaction, resolveWallet, mode }
}

export type { ConnectedWallet, User }
