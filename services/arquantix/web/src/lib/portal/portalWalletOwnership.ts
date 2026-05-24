import { prisma } from '@/lib/prisma'
import { normalizeVaultAddress } from '@/lib/portal/morphoConstants'

export class PortalForbiddenError extends Error {
  readonly httpStatus = 403

  constructor(message: string) {
    super(message)
    this.name = 'PortalForbiddenError'
  }
}

function normalizeAddress(address: string): string {
  return address.trim().toLowerCase()
}

function readPrivyWalletIdFromMetadata(metadataJson: unknown): string | null {
  if (!metadataJson || typeof metadataJson !== 'object') return null
  const row = metadataJson as Record<string, unknown>
  const candidates = [row.privy_wallet_id, row.privyWalletId, row.wallet_id, row.walletId]
  for (const value of candidates) {
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return null
}

/** Vérifie que le wallet Privy appartient à la personne de la session. */
export async function assertPortalPrivyWalletOwnership(args: {
  personId: string
  privyWalletId: string
}): Promise<void> {
  const target = args.privyWalletId.trim()
  if (!target) {
    throw new PortalForbiddenError('Wallet Privy non autorisé pour cette session.')
  }

  const wallets = await prisma.personCryptoWallet.findMany({
    where: { personId: args.personId, revokedAt: null },
    select: { id: true, address: true, metadataJson: true },
  })

  for (const wallet of wallets) {
    if (wallet.id === target) return
    const privyId = readPrivyWalletIdFromMetadata(wallet.metadataJson)
    if (privyId === target) return
  }

  throw new PortalForbiddenError('Wallet Privy non autorisé pour cette session.')
}

/** Vérifie qu’une adresse EVM appartient à la personne de la session. */
export async function assertPortalWalletAddressOwnership(args: {
  personId: string
  walletAddress: string
}): Promise<void> {
  const target = normalizeAddress(args.walletAddress)
  const wallets = await prisma.personCryptoWallet.findMany({
    where: { personId: args.personId, revokedAt: null },
    select: { address: true },
  })

  if (wallets.some((row) => normalizeAddress(row.address) === target)) {
    return
  }

  throw new PortalForbiddenError('Adresse wallet non autorisée pour cette session.')
}

export { normalizeVaultAddress }
