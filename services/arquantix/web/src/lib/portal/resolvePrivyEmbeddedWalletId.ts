import type { ConnectedWallet, User } from '@privy-io/react-auth'

function isPrivyEmbeddedLinkedAccount(account: Record<string, unknown>): boolean {
  const client = String(account.walletClientType ?? account.wallet_client_type ?? '').toLowerCase()
  const connector = String(account.connectorType ?? account.connector_type ?? '').toLowerCase()
  return client === 'privy' || client === 'privy-v2' || connector === 'embedded'
}

function readLinkedAccountId(account: Record<string, unknown>): string | null {
  const id = account.id ?? account.wallet_id ?? account.walletId
  if (typeof id !== 'string' || !id.trim()) return null
  return id.trim()
}

/** Résout le wallet ID Privy (serveur) depuis la session SDK React. */
export function resolvePrivyEmbeddedWalletId(args: {
  user: User | null | undefined
  wallets: ConnectedWallet[]
  walletAddress: string
}): string | null {
  const target = args.walletAddress.trim().toLowerCase()
  if (!target) return null

  for (const account of args.user?.linkedAccounts ?? []) {
    if (!account || typeof account !== 'object') continue
    const row = account as unknown as Record<string, unknown>
    if (row.type !== 'wallet') continue
    const address = typeof row.address === 'string' ? row.address.trim().toLowerCase() : ''
    if (address !== target) continue
    if (!isPrivyEmbeddedLinkedAccount(row)) continue
    const id = readLinkedAccountId(row)
    if (id) return id
  }

  for (const wallet of args.wallets) {
    if (wallet.address.toLowerCase() !== target) continue
    const client = wallet.walletClientType.toLowerCase()
    if (client !== 'privy' && client !== 'privy-v2') continue
    const metaId = (wallet as ConnectedWallet & { id?: string | null }).id
    if (typeof metaId === 'string' && metaId.trim()) return metaId.trim()
  }

  return null
}
