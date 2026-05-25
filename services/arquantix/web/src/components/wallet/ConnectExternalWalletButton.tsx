'use client'

import { useCallback, useMemo, useState } from 'react'
import { ConnectButton } from '@rainbow-me/rainbowkit'
import { Loader2, Unlink } from 'lucide-react'
import { useAccount, useDisconnect, useSignMessage } from 'wagmi'

import { Button } from '@/components/ui/button'
import { formatEvmNetworkShort } from '@/lib/portal/evmNetworkLabel'
import {
  fetchExternalWalletNonce,
  unlinkExternalWallet,
  unlinkLocalMockExternalWalletDev,
  verifyExternalWalletLink,
} from '@/lib/wallet/externalWalletClient'
import { LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS } from '@/lib/wallet/externalWalletMock'
import { getExternalWalletBaseChainId, isWalletConnectConfigured } from '@/lib/wallet/externalWalletConstants'
import type { ExternalWalletConnector } from '@/lib/wallet/executionWalletTypes'
import { useExecutionWallet } from '@/lib/wallet/useExecutionWallet'
import { cn } from '@/lib/utils'

function formatWalletProvider(provider: string): string {
  if (provider === 'local_mock') return 'Local mock (dev)'
  if (provider === 'walletconnect') return 'WalletConnect'
  return provider
}

function formatAddress(address: string): string {
  const trimmed = address.trim()
  if (trimmed.length <= 12) return trimmed
  return `${trimmed.slice(0, 6)}…${trimmed.slice(-4)}`
}

function inferConnector(id?: string): ExternalWalletConnector {
  const normalized = (id || '').toLowerCase()
  if (normalized.includes('metamask')) return 'metamask'
  if (normalized.includes('walletconnect')) return 'walletconnect'
  return 'injected'
}

type Props = {
  className?: string
  compact?: boolean
}

export function ConnectExternalWalletButton({ className, compact = false }: Props) {
  const { address, chain, connector, isConnected } = useAccount()
  const { disconnect } = useDisconnect()
  const { signMessageAsync } = useSignMessage()
  const {
    externalWallets,
    refreshExternalWallets,
    selectedExternalWalletId,
    mockWalletAvailable,
    mockWalletLinked,
    linkLocalMockWallet,
    selectLocalMockWallet,
  } = useExecutionWallet()

  const [linking, setLinking] = useState(false)
  const [linkingMock, setLinkingMock] = useState(false)
  const [unlinkingId, setUnlinkingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const linkedWallet = useMemo(
    () =>
      externalWallets.find(
        (row) =>
          row.id === selectedExternalWalletId ||
          (address && row.address.toLowerCase() === address.toLowerCase()),
      ) ?? null,
    [address, externalWallets, selectedExternalWalletId],
  )

  const verifyCurrentWallet = useCallback(async () => {
    if (!address) {
      setError('Connectez d’abord un wallet via MetaMask ou WalletConnect.')
      return
    }

    setLinking(true)
    setError(null)
    setSuccess(null)
    try {
      const noncePayload = await fetchExternalWalletNonce()
      const signature = await signMessageAsync({
        message: noncePayload.message,
      })
      const wallet = await verifyExternalWalletLink({
        walletAddress: address,
        signature,
        nonce: noncePayload.nonce,
        walletProvider: inferConnector(connector?.id),
        chainId: chain?.id,
      })
      await refreshExternalWallets()
      setSuccess(`Wallet ${formatAddress(wallet.address)} lié et vérifié.`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Vérification impossible.')
    } finally {
      setLinking(false)
    }
  }, [address, chain?.id, connector?.id, refreshExternalWallets, signMessageAsync])

  const onUnlink = useCallback(
    async (walletId: string) => {
      setUnlinkingId(walletId)
      setError(null)
      setSuccess(null)
      try {
        await unlinkExternalWallet(walletId)
        await refreshExternalWallets()
        if (isConnected) disconnect()
        setSuccess('Wallet externe dissocié.')
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Dissociation impossible.')
      } finally {
        setUnlinkingId(null)
      }
    },
    [disconnect, isConnected, refreshExternalWallets],
  )

  const onLinkMockWallet = useCallback(async () => {
    setLinkingMock(true)
    setError(null)
    setSuccess(null)
    try {
      const wallet = await linkLocalMockWallet()
      setSuccess(`Wallet mock ${formatAddress(wallet.address)} lié et sélectionné.`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Liaison mock impossible.')
    } finally {
      setLinkingMock(false)
    }
  }, [linkLocalMockWallet])

  const onUnlinkMockWallet = useCallback(async () => {
    const mockWallet = externalWallets.find((row) => row.walletProvider === 'local_mock')
    if (!mockWallet) return
    setUnlinkingId(mockWallet.id)
    setError(null)
    setSuccess(null)
    try {
      await unlinkLocalMockExternalWalletDev()
      await refreshExternalWallets()
      setSuccess('Wallet mock dissocié.')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Dissociation mock impossible.')
    } finally {
      setUnlinkingId(null)
    }
  }, [externalWallets, refreshExternalWallets])

  if (!isWalletConnectConfigured() && !mockWalletAvailable) {
    return (
      <div className={cn('rounded-v-card border border-amber-200 bg-amber-50 px-4 py-3 font-ui text-[13px] text-amber-950', className)}>
        Configurez <code className="text-[12px]">NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID</code> pour activer MetaMask / WalletConnect.
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col gap-3', className)}>
      <div>
        <p className="m-0 font-ui text-[15px] font-semibold text-v-fg">Connecter un wallet externe</p>
        {!compact ? (
          <p className="m-0 mt-1 font-ui text-[13px] leading-relaxed text-v-fg-muted">
            MetaMask / WalletConnect — signez vos transactions DeFi (Morpho, LI.FI). Les frais réseau sont payés depuis ce wallet.
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {mockWalletAvailable ? (
          <>
            {!mockWalletLinked ? (
              <Button type="button" size="sm" disabled={linkingMock} onClick={() => void onLinkMockWallet()}>
                {linkingMock ? (
                  <span className="inline-flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Liaison mock…
                  </span>
                ) : (
                  'Use Local Mock Wallet'
                )}
              </Button>
            ) : (
              <>
                <Button type="button" size="sm" variant="outline" onClick={() => selectLocalMockWallet()}>
                  Sélectionner mock
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={unlinkingId !== null}
                  onClick={() => void onUnlinkMockWallet()}
                >
                  Reset mock wallet
                </Button>
              </>
            )}
          </>
        ) : null}
        {isWalletConnectConfigured() ? (
          <ConnectButton chainStatus="icon" showBalance={false} accountStatus="address" />
        ) : null}
        {isConnected && !linkedWallet && isWalletConnectConfigured() ? (
          <Button type="button" size="sm" disabled={linking} onClick={() => void verifyCurrentWallet()}>
            {linking ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                Vérification…
              </span>
            ) : (
              'Vérifier ce wallet'
            )}
          </Button>
        ) : null}
      </div>

      {mockWalletLinked ? (
        <div className="rounded-v-card border border-emerald-200 bg-emerald-50 px-4 py-3 font-ui text-[13px] text-emerald-900">
          <p className="m-0 font-medium">Local Mock Wallet actif</p>
          <p className="m-0 mt-1 font-mono">{formatAddress(LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS)}</p>
          <p className="m-0 mt-2 text-emerald-800">
            Aucune extension MetaMask ni WalletConnect requis. Sélectionnez « MetaMask / externe » dans Invest ou Swap.
          </p>
        </div>
      ) : null}

      {isConnected && address ? (
        <div className="rounded-v-card border border-v-border bg-v-card px-4 py-3 font-ui text-[13px]">
          <p className="m-0 text-v-fg-muted">Wallet connecté</p>
          <p className="m-0 mt-1 font-medium text-v-fg">{formatAddress(address)}</p>
          <p className="m-0 mt-2 text-v-fg-muted">
            Réseau : {chain ? formatEvmNetworkShort(chain.id) : '—'}
            {chain?.id !== getExternalWalletBaseChainId() ? (
              <span className="ml-1 text-amber-700">(Base recommandé pour Morpho)</span>
            ) : null}
          </p>
          {linkedWallet ? (
            <p className="m-0 mt-2 text-v-green">Wallet vérifié pour votre compte Vancelian.</p>
          ) : (
            <p className="m-0 mt-2 text-v-fg-muted">
              Signez le message de vérification pour lier ce wallet à votre compte.
            </p>
          )}
        </div>
      ) : null}

      {externalWallets.length > 0 ? (
        <ul className="m-0 list-none space-y-2 p-0">
          {externalWallets.map((wallet) => (
            <li
              key={wallet.id}
              className="flex items-center justify-between gap-3 rounded-v-card border border-v-border bg-v-card px-4 py-3 font-ui text-[13px]"
            >
              <div className="min-w-0">
                <p className="m-0 font-medium text-v-fg">{formatAddress(wallet.address)}</p>
                <p className="m-0 mt-1 text-v-fg-muted">{formatWalletProvider(wallet.walletProvider)}</p>
              </div>
              <Button
                type="button"
                size="sm"
                variant="outline"
                disabled={unlinkingId === wallet.id}
                onClick={() => void onUnlink(wallet.id)}
              >
                {unlinkingId === wallet.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <span className="inline-flex items-center gap-1">
                    <Unlink className="h-3.5 w-3.5" />
                    Dissocier
                  </span>
                )}
              </Button>
            </li>
          ))}
        </ul>
      ) : null}

      {error ? (
        <p className="m-0 rounded-v-control bg-red-50 px-3 py-2 font-ui text-[13px] text-v-error">{error}</p>
      ) : null}
      {success ? (
        <p className="m-0 rounded-v-control bg-emerald-50 px-3 py-2 font-ui text-[13px] text-emerald-800">{success}</p>
      ) : null}
    </div>
  )
}
