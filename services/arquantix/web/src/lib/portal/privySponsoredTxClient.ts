import { normalizeTxHash } from '@/lib/portal/swapTxFormat'

export async function sendPortalPrivySponsoredTransaction(args: {
  chainId: number
  to: `0x${string}`
  data: `0x${string}`
  value?: string | number | bigint
  gasLimit?: string | number | bigint
  walletAddress: `0x${string}`
  privyWalletId?: string | null
}): Promise<{ hash: string }> {
  const res = await fetch('/api/portal/privy/send-sponsored-transaction', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      chain_id: args.chainId,
      to: args.to,
      data: args.data,
      value: args.value !== undefined ? String(args.value) : undefined,
      gas_limit: args.gasLimit !== undefined ? String(args.gasLimit) : undefined,
      wallet_address: args.walletAddress,
      privy_wallet_id: args.privyWalletId ?? undefined,
    }),
    cache: 'no-store',
  })

  const payload = (await res.json().catch(() => ({}))) as {
    hash?: string
    message?: string
    code?: string
  }

  if (!res.ok) {
    throw new Error(payload.message ?? 'Envoi transaction Privy sponsorisée impossible.')
  }

  const hash = payload.hash?.trim()
  if (!hash) {
    throw new Error('Réponse Privy invalide — hash transaction manquant.')
  }

  return { hash: normalizeTxHash(hash) }
}
