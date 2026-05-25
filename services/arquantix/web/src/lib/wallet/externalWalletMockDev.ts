import { randomUUID } from 'node:crypto'

import type { Prisma } from '@prisma/client'
import { getAddress } from 'viem'

import { prisma } from '@/lib/prisma'
import {
  buildLocalMockExternalWalletMetadata,
  LOCAL_MOCK_EXTERNAL_WALLET,
  LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS,
} from '@/lib/wallet/externalWalletMock'
import {
  isExternalWalletLocalMockEnabled,
  isExternalWalletMockDevRouteAvailable,
} from '@/lib/wallet/externalWalletMockConfig'

export class ExternalWalletMockDevError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'ExternalWalletMockDevError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

export function assertExternalWalletMockDevRouteAvailable(): void {
  if (process.env.NODE_ENV === 'production') {
    throw new ExternalWalletMockDevError(
      'wallet.mock.dev_forbidden',
      'Route dev indisponible en production.',
      403,
    )
  }
  if (!isExternalWalletLocalMockEnabled()) {
    throw new ExternalWalletMockDevError(
      'wallet.mock.disabled',
      'EXTERNAL_WALLET_LOCAL_MOCK_ENABLED=true requis avec MORPHO_LOCAL_SANDBOX_ENABLED ou LIFI_LOCAL_SANDBOX_ENABLED.',
      403,
    )
  }
}

export function externalWalletMockDevErrorResponse(error: unknown): { status: number; body: Record<string, unknown> } {
  if (error instanceof ExternalWalletMockDevError) {
    return { status: error.httpStatus, body: { error: error.code, message: error.message } }
  }
  const message = error instanceof Error ? error.message : 'Erreur inattendue.'
  return { status: 500, body: { error: 'wallet.mock.internal', message } }
}

function normalizeAddress(address: string): string {
  return address.trim().toLowerCase()
}

async function findLinkedLocalMockWallet(personId: string) {
  return prisma.personCryptoWallet.findFirst({
    where: {
      personId,
      provider: 'external',
      chainType: 'evm',
      address: normalizeAddress(LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS),
      revokedAt: null,
    },
    select: {
      id: true,
      address: true,
      metadataJson: true,
      createdAt: true,
    },
  })
}

export async function linkLocalMockExternalWallet(personId: string) {
  assertExternalWalletMockDevRouteAvailable()

  const metadata = buildLocalMockExternalWalletMetadata() as Prisma.InputJsonValue
  const normalized = normalizeAddress(LOCAL_MOCK_EXTERNAL_WALLET_ADDRESS)
  const verifiedAt = new Date()

  const existingOtherPerson = await prisma.personCryptoWallet.findFirst({
    where: {
      provider: 'external',
      chainType: 'evm',
      address: normalized,
      revokedAt: null,
    },
    select: { id: true, personId: true },
  })
  if (existingOtherPerson && existingOtherPerson.personId !== personId) {
    throw new ExternalWalletMockDevError(
      'wallet.mock.already_linked',
      'Le wallet mock est déjà lié à un autre compte.',
      409,
    )
  }

  const existing = await findLinkedLocalMockWallet(personId)
  const row =
    existing ??
    (await prisma.personCryptoWallet.create({
      data: {
        id: randomUUID(),
        personId,
        provider: 'external',
        walletType: 'external',
        chainType: 'evm',
        chainId: LOCAL_MOCK_EXTERNAL_WALLET.chainId,
        address: normalized,
        isPrimary: false,
        metadataJson: metadata,
      },
    }))

  if (existing) {
    await prisma.personCryptoWallet.update({
      where: { id: existing.id },
      data: { metadataJson: metadata },
    })
  }

  return {
    id: row.id,
    address: getAddress(row.address) as `0x${string}`,
    walletProvider: LOCAL_MOCK_EXTERNAL_WALLET.walletProvider,
    isVerified: true,
    verifiedAt: verifiedAt.toISOString(),
    createdAt: row.createdAt.toISOString(),
  }
}

export async function unlinkLocalMockExternalWallet(personId: string): Promise<void> {
  assertExternalWalletMockDevRouteAvailable()

  const row = await findLinkedLocalMockWallet(personId)
  if (!row) {
    throw new ExternalWalletMockDevError('wallet.mock.not_linked', 'Wallet mock non lié.', 404)
  }

  await prisma.personCryptoWallet.update({
    where: { id: row.id },
    data: { revokedAt: new Date() },
  })
}

export async function getLocalMockExternalWalletStatus(args: { personId: string | null }) {
  const mockEnabled = isExternalWalletLocalMockEnabled()
  const devRouteAvailable = isExternalWalletMockDevRouteAvailable()

  if (!args.personId) {
    return {
      mockEnabled,
      devRouteAvailable,
      session: { authenticated: false, personId: null },
      linked: false,
      wallet: null,
    }
  }

  const row = mockEnabled ? await findLinkedLocalMockWallet(args.personId) : null

  return {
    mockEnabled,
    devRouteAvailable,
    session: { authenticated: true, personId: args.personId },
    linked: Boolean(row),
    wallet: row
      ? {
          id: row.id,
          address: getAddress(row.address),
          walletProvider: LOCAL_MOCK_EXTERNAL_WALLET.walletProvider,
          isVerified: true,
        }
      : null,
  }
}
