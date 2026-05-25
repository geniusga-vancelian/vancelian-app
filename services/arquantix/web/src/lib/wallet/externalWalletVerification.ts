import { randomBytes, randomUUID } from 'node:crypto'

import type { Prisma } from '@prisma/client'
import { getAddress, verifyMessage } from 'viem'

import { prisma } from '@/lib/prisma'
import { isValidEvmAddress } from '@/lib/portal/morphoConstants'
import type { ExternalWalletConnector } from '@/lib/wallet/executionWalletTypes'
import { isAllowedExternalWalletChainId } from '@/lib/wallet/externalWalletConfig'

const NONCE_TTL_MS = 10 * 60 * 1000
const MAX_NONCES_PER_PERSON = 5
const VERIFY_RATE_LIMIT_WINDOW_MS = 60_000
const MAX_VERIFY_ATTEMPTS_PER_WINDOW = 10

const verifyAttempts = new Map<string, { count: number; windowStart: number }>()

export class ExternalWalletError extends Error {
  readonly httpStatus: number
  readonly code: string

  constructor(code: string, message: string, httpStatus = 400) {
    super(message)
    this.name = 'ExternalWalletError'
    this.code = code
    this.httpStatus = httpStatus
  }
}

function normalizeAddress(address: string): string {
  return address.trim().toLowerCase()
}

function toChecksumAddress(address: string): `0x${string}` {
  if (!isValidEvmAddress(address)) {
    throw new ExternalWalletError('wallet.invalid_address', 'Adresse EVM invalide.')
  }
  return getAddress(address.trim())
}

export function buildExternalWalletVerificationMessage(args: {
  personId: string
  nonce: string
  timestamp: string
}): string {
  return [
    'I confirm that I control this wallet for Vancelian.',
    `Person ID: ${args.personId}`,
    `Timestamp: ${args.timestamp}`,
    `Nonce: ${args.nonce}`,
  ].join('\n')
}

function assertVerifyRateLimit(personId: string): void {
  const now = Date.now()
  const row = verifyAttempts.get(personId)
  if (!row || now - row.windowStart > VERIFY_RATE_LIMIT_WINDOW_MS) {
    verifyAttempts.set(personId, { count: 1, windowStart: now })
    return
  }
  row.count += 1
  if (row.count > MAX_VERIFY_ATTEMPTS_PER_WINDOW) {
    throw new ExternalWalletError(
      'wallet.verify_rate_limited',
      'Trop de tentatives. Réessayez dans une minute.',
      429,
    )
  }
}

export async function createExternalWalletNonce(personId: string): Promise<{
  nonce: string
  message: string
  expiresAt: string
}> {
  await prisma.portalExternalWalletNonce.deleteMany({
    where: {
      personId,
      OR: [{ expiresAt: { lt: new Date() } }, { usedAt: { not: null } }],
    },
  })

  const activeCount = await prisma.portalExternalWalletNonce.count({
    where: { personId, usedAt: null, expiresAt: { gt: new Date() } },
  })
  if (activeCount >= MAX_NONCES_PER_PERSON) {
    throw new ExternalWalletError(
      'wallet.nonce_limit',
      'Trop de demandes de signature en cours. Réessayez plus tard.',
      429,
    )
  }

  const nonce = randomBytes(16).toString('hex')
  const expiresAt = new Date(Date.now() + NONCE_TTL_MS)

  const row = await prisma.portalExternalWalletNonce.create({
    data: {
      personId,
      nonce,
      expiresAt,
    },
  })

  const timestamp = row.createdAt.toISOString()

  return {
    nonce,
    message: buildExternalWalletVerificationMessage({ personId, nonce, timestamp }),
    expiresAt: expiresAt.toISOString(),
  }
}

function normalizeWalletProvider(value: unknown): ExternalWalletConnector {
  if (
    value === 'metamask' ||
    value === 'walletconnect' ||
    value === 'injected' ||
    value === 'local_mock'
  ) {
    return value
  }
  return 'injected'
}

export async function verifyAndLinkExternalWallet(args: {
  personId: string
  walletAddress: string
  signature: `0x${string}`
  nonce: string
  walletProvider?: unknown
  chainId?: number | null
}): Promise<{
  id: string
  address: string
  walletProvider: ExternalWalletConnector
  isVerified: boolean
  verifiedAt: string
}> {
  assertVerifyRateLimit(args.personId)

  const checksumAddress = toChecksumAddress(args.walletAddress)
  const normalized = normalizeAddress(checksumAddress)

  if (args.chainId != null && !isAllowedExternalWalletChainId(args.chainId)) {
    throw new ExternalWalletError('wallet.chain_not_allowed', 'Réseau non autorisé.')
  }

  const nonceRow = await prisma.portalExternalWalletNonce.findFirst({
    where: {
      personId: args.personId,
      nonce: args.nonce.trim(),
      usedAt: null,
      expiresAt: { gt: new Date() },
    },
  })
  if (!nonceRow) {
    throw new ExternalWalletError('wallet.invalid_nonce', 'Nonce invalide ou expiré.', 401)
  }

  const message = buildExternalWalletVerificationMessage({
    personId: args.personId,
    nonce: args.nonce.trim(),
    timestamp: nonceRow.createdAt.toISOString(),
  })

  const valid = await verifyMessage({
    address: checksumAddress,
    message,
    signature: args.signature,
  })
  if (!valid) {
    throw new ExternalWalletError('wallet.invalid_signature', 'Signature invalide.', 401)
  }

  await prisma.portalExternalWalletNonce.update({
    where: { id: nonceRow.id },
    data: { usedAt: new Date() },
  })

  const walletProvider = normalizeWalletProvider(args.walletProvider)
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
  if (existingOtherPerson && existingOtherPerson.personId !== args.personId) {
    throw new ExternalWalletError(
      'wallet.already_linked',
      'Cette adresse est déjà liée à un autre compte.',
      409,
    )
  }

  const metadata: Prisma.InputJsonValue = {
    wallet_provider: walletProvider,
    is_verified: true,
    verified_at: verifiedAt.toISOString(),
    sync_source: 'external_wallet_verify',
  }

  const existing = await prisma.personCryptoWallet.findFirst({
    where: {
      personId: args.personId,
      provider: 'external',
      chainType: 'evm',
      address: normalized,
      revokedAt: null,
    },
  })

  const row =
    existing ??
    (await prisma.personCryptoWallet.create({
      data: {
        id: randomUUID(),
        personId: args.personId,
        provider: 'external',
        walletType: 'external',
        chainType: 'evm',
        chainId: args.chainId ?? null,
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
    address: checksumAddress,
    walletProvider,
    isVerified: true,
    verifiedAt: verifiedAt.toISOString(),
  }
}

export async function listVerifiedExternalWallets(personId: string) {
  const rows = await prisma.personCryptoWallet.findMany({
    where: {
      personId,
      provider: 'external',
      chainType: 'evm',
      revokedAt: null,
    },
    orderBy: { createdAt: 'desc' },
    select: {
      id: true,
      address: true,
      metadataJson: true,
      createdAt: true,
    },
  })

  return rows
    .map((row) => {
      const meta =
        row.metadataJson && typeof row.metadataJson === 'object'
          ? (row.metadataJson as Record<string, unknown>)
          : {}
      const isVerified = meta.is_verified === true
      if (!isVerified) return null
      return {
        id: row.id,
        address: getAddress(row.address) as `0x${string}`,
        walletProvider: normalizeWalletProvider(meta.wallet_provider),
        isVerified: true,
        verifiedAt: typeof meta.verified_at === 'string' ? meta.verified_at : null,
        createdAt: row.createdAt.toISOString(),
      }
    })
    .filter((row): row is NonNullable<typeof row> => row !== null)
}

export async function revokeExternalWallet(args: { personId: string; walletId: string }): Promise<void> {
  const row = await prisma.personCryptoWallet.findFirst({
    where: {
      id: args.walletId,
      personId: args.personId,
      provider: 'external',
      revokedAt: null,
    },
  })
  if (!row) {
    throw new ExternalWalletError('wallet.not_found', 'Wallet externe introuvable.', 404)
  }

  await prisma.personCryptoWallet.update({
    where: { id: row.id },
    data: { revokedAt: new Date() },
  })
}

export function isExternalWalletVerified(metadataJson: unknown): boolean {
  if (!metadataJson || typeof metadataJson !== 'object') return false
  return (metadataJson as Record<string, unknown>).is_verified === true
}

export function readExternalWalletProvider(metadataJson: unknown): ExternalWalletConnector {
  if (!metadataJson || typeof metadataJson !== 'object') return 'injected'
  return normalizeWalletProvider((metadataJson as Record<string, unknown>).wallet_provider)
}
