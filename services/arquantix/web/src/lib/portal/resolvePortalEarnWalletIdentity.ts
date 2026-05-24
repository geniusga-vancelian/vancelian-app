import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'
import { PortalForbiddenError } from '@/lib/portal/portalWalletOwnership'
import { prisma } from '@/lib/prisma'

export type PortalEarnWalletIdentity = {
  personId: string
  privyWalletId: string | null
  walletAddress: string
  chainType: 'evm'
  chainId: number
}

function normalizeAddress(address: string): string {
  return address.trim().toLowerCase()
}

function readPrivyWalletIdFromMetadata(metadataJson: unknown): string | null {
  if (!metadataJson || typeof metadataJson !== 'object') return null
  const row = metadataJson as Record<string, unknown>
  for (const key of ['privy_wallet_id', 'privyWalletId', 'wallet_id', 'walletId']) {
    const value = row[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return null
}

function isEvmAddress(value: string): boolean {
  return /^0x[0-9a-fA-F]{40}$/.test(value.trim())
}

type PersonWalletRow = {
  id: string
  address: string
  chainId: number | null
  metadataJson: unknown
}

/** Pure helper — résout un wallet personne à partir d’un privyWalletId (testable). */
export function matchPersonWalletToPrivyId(
  wallets: PersonWalletRow[],
  privyWalletId: string,
): PersonWalletRow | null {
  const target = privyWalletId.trim()
  for (const wallet of wallets) {
    const privyId = readPrivyWalletIdFromMetadata(wallet.metadataJson)
    if (wallet.id === target || privyId === target) return wallet
  }
  return null
}

/** Résout l’identité wallet portail (Privy + adresse EVM) pour une personne. */
export async function resolvePortalEarnWalletIdentity(args: {
  personId: string
  privyWalletId?: string | null
}): Promise<PortalEarnWalletIdentity> {
  const wallets = await prisma.personCryptoWallet.findMany({
    where: {
      personId: args.personId,
      revokedAt: null,
      chainType: 'ethereum',
    },
    orderBy: [{ isPrimary: 'desc' }, { createdAt: 'asc' }],
    select: {
      id: true,
      address: true,
      chainId: true,
      metadataJson: true,
    },
  })

  if (wallets.length === 0) {
    throw new PortalForbiddenError('Aucun wallet EVM lié à cette personne.')
  }

  const targetPrivyId = args.privyWalletId?.trim() || null

  if (targetPrivyId) {
    const matched = matchPersonWalletToPrivyId(wallets, targetPrivyId)
    if (matched) {
      return {
        personId: args.personId,
        privyWalletId: targetPrivyId,
        walletAddress: normalizeAddress(matched.address),
        chainType: 'evm',
        chainId: matched.chainId ?? MORPHO_CHAIN_ID,
      }
    }
    throw new PortalForbiddenError('Wallet Privy non autorisé pour cette session.')
  }

  const primary = wallets[0]
  return {
    personId: args.personId,
    privyWalletId: readPrivyWalletIdFromMetadata(primary.metadataJson),
    walletAddress: normalizeAddress(primary.address),
    chainType: 'evm',
    chainId: primary.chainId ?? MORPHO_CHAIN_ID,
  }
}

export function normalizeWalletIdentityFields(args: {
  walletAddress: string
  privyWalletId?: string | null
}): { walletAddress: string; privyWalletId: string | null } {
  const raw = args.walletAddress.trim()
  if (isEvmAddress(raw)) {
    return {
      walletAddress: normalizeAddress(raw),
      privyWalletId: args.privyWalletId?.trim() || null,
    }
  }
  return {
    walletAddress: normalizeAddress(raw),
    privyWalletId: args.privyWalletId?.trim() || raw,
  }
}
