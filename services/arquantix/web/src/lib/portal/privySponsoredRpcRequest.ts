import { normalizeSwapTxValue } from '@/lib/portal/swapTxFormat'

export const PRIVY_API_BASE = 'https://api.privy.io'

export type PrivyEthSendTransactionRpcBody = {
  method: 'eth_sendTransaction'
  caip2: string
  chain_type: 'ethereum'
  sponsor: true
  params: {
    transaction: Record<string, string>
  }
}

export type PrivyAuthorizationSignatureInput = {
  version: 1
  method: 'POST'
  url: string
  body: PrivyEthSendTransactionRpcBody
  headers: {
    'privy-app-id': string
  }
}

export function normalizePrivyTxValueHex(value?: string | number | bigint): `0x${string}` {
  if (value === undefined) return '0x0'
  if (typeof value === 'bigint') return `0x${value.toString(16)}` as `0x${string}`
  return normalizeSwapTxValue(String(value))
}

export function buildPrivyWalletRpcUrl(privyWalletId: string): string {
  const id = privyWalletId.trim()
  if (!id) throw new Error('Wallet Privy introuvable pour cette session.')
  return `${PRIVY_API_BASE}/v1/wallets/${encodeURIComponent(id)}/rpc`
}

/** Corps RPC Privy identique côté client (signature) et serveur (relay). */
export function buildPrivyEthSendTransactionRpcBody(args: {
  chainId: number
  to: string
  data: string
  value?: string | number | bigint
  gasLimit?: string | number | bigint
}): PrivyEthSendTransactionRpcBody {
  const transaction: Record<string, string> = {
    to: args.to.trim().toLowerCase(),
    data: args.data.trim().toLowerCase(),
    value: normalizePrivyTxValueHex(args.value),
  }

  if (args.gasLimit !== undefined && `${args.gasLimit}`.trim()) {
    transaction.gas_limit = normalizePrivyTxValueHex(args.gasLimit)
  }

  return {
    method: 'eth_sendTransaction',
    caip2: `eip155:${args.chainId}`,
    chain_type: 'ethereum',
    sponsor: true,
    params: { transaction },
  }
}

export function buildPrivyAuthorizationSignatureInput(args: {
  appId: string
  privyWalletId: string
  rpcBody: PrivyEthSendTransactionRpcBody
}): PrivyAuthorizationSignatureInput {
  const appId = args.appId.trim()
  if (!appId) {
    throw new Error('Privy App ID manquant — impossible de signer la transaction.')
  }

  return {
    version: 1,
    method: 'POST',
    url: buildPrivyWalletRpcUrl(args.privyWalletId),
    body: args.rpcBody,
    headers: {
      'privy-app-id': appId,
    },
  }
}
