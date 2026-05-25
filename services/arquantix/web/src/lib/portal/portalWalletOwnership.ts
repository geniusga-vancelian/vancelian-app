import { randomUUID } from 'node:crypto'

import type { Prisma } from '@prisma/client'

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

type OwnedWalletRow = {
  id: string
  address: string
  metadataJson: unknown
}

/** Résolution pure ownership Privy id / adresse EVM (testable). */
export function resolveOwnedPrivyWallet(args: {
  wallets: OwnedWalletRow[]
  privyWalletId: string
  walletAddress?: string | null
}): OwnedWalletRow | null {
  const target = args.privyWalletId.trim()
  if (!target) return null

  for (const wallet of args.wallets) {
    if (wallet.id === target) return wallet
    const privyId = readPrivyWalletIdFromMetadata(wallet.metadataJson)
    if (privyId === target) return wallet
  }

  const addressTarget = args.walletAddress?.trim()
  if (!addressTarget) return null
  const normalized = normalizeAddress(addressTarget)
  return args.wallets.find((wallet) => normalizeAddress(wallet.address) === normalized) ?? null
}

async function backfillPrivyWalletIdMetadata(walletId: string, privyWalletId: string): Promise<void> {
  const wallet = await prisma.personCryptoWallet.findUnique({
    where: { id: walletId },
    select: { metadataJson: true },
  })
  if (!wallet) return

  const existing = readPrivyWalletIdFromMetadata(wallet.metadataJson)
  if (existing === privyWalletId) return

  const base =
    wallet.metadataJson && typeof wallet.metadataJson === 'object'
      ? { ...(wallet.metadataJson as Record<string, unknown>) }
      : {}
  base.privy_wallet_id = privyWalletId

  await prisma.personCryptoWallet.update({
    where: { id: walletId },
    data: { metadataJson: base as Prisma.InputJsonValue },
  })
}

async function ensurePersonPrivyWalletFromAddress(args: {
  personId: string
  privyWalletId: string
  walletAddress: string
}): Promise<OwnedWalletRow | null> {
  const address = normalizeAddress(args.walletAddress)
  if (!/^0x[0-9a-f]{40}$/.test(address)) return null

  const existing = await prisma.personCryptoWallet.findFirst({
    where: {
      provider: 'privy',
      chainType: 'evm',
      address,
      revokedAt: null,
    },
    select: { id: true, personId: true, address: true, metadataJson: true },
  })

  if (existing) {
    if (existing.personId !== args.personId) return null
    return existing
  }

  const created = await prisma.personCryptoWallet.create({
    data: {
      id: randomUUID(),
      personId: args.personId,
      provider: 'privy',
      walletType: 'embedded',
      chainType: 'evm',
      chainId: 8453,
      address,
      isPrimary: true,
      metadataJson: {
        privy_wallet_id: args.privyWalletId,
        sync_source: 'portal_earn_heal',
      } as Prisma.InputJsonValue,
    },
    select: { id: true, address: true, metadataJson: true },
  })
  return created
}

/** Vérifie que le wallet Privy appartient à la personne de la session. */
export async function assertPortalPrivyWalletOwnership(args: {
  personId: string
  privyWalletId: string
  walletAddress?: string | null
}): Promise<void> {
  const target = args.privyWalletId.trim()
  if (!target) {
    throw new PortalForbiddenError('Wallet Privy non autorisé pour cette session.')
  }

  const wallets = await prisma.personCryptoWallet.findMany({
    where: { personId: args.personId, revokedAt: null },
    select: { id: true, address: true, metadataJson: true },
  })

  let matched = resolveOwnedPrivyWallet({
    wallets,
    privyWalletId: target,
    walletAddress: args.walletAddress,
  })

  if (!matched && args.walletAddress?.trim()) {
    matched = await ensurePersonPrivyWalletFromAddress({
      personId: args.personId,
      privyWalletId: target,
      walletAddress: args.walletAddress,
    })
  }

  if (!matched) {
    throw new PortalForbiddenError('Wallet Privy non autorisé pour cette session.')
  }

  const storedPrivyId = readPrivyWalletIdFromMetadata(matched.metadataJson)
  if (storedPrivyId !== target) {
    await backfillPrivyWalletIdMetadata(matched.id, target)
  }
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
