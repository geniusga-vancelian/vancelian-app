import { prisma } from '@/lib/prisma'
import {
  assertPortalPrivyWalletOwnership,
  assertPortalWalletAddressOwnership,
} from '@/lib/portal/portalWalletOwnership'

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

export async function resolvePrivyWalletIdForPerson(args: {
  personId: string
  walletAddress: string
  privyWalletIdHint?: string | null
}): Promise<string> {
  const address = normalizeAddress(args.walletAddress)
  if (!/^0x[0-9a-f]{40}$/.test(address)) {
    throw new Error('Adresse wallet invalide.')
  }

  await assertPortalWalletAddressOwnership({ personId: args.personId, walletAddress: address })

  const hint = args.privyWalletIdHint?.trim()
  if (hint) {
    await assertPortalPrivyWalletOwnership({
      personId: args.personId,
      privyWalletId: hint,
      walletAddress: address,
    })
    return hint
  }

  const wallets = await prisma.personCryptoWallet.findMany({
    where: { personId: args.personId, revokedAt: null, provider: 'privy' },
    select: { address: true, metadataJson: true },
  })

  for (const wallet of wallets) {
    if (normalizeAddress(wallet.address) !== address) continue
    const privyWalletId = readPrivyWalletIdFromMetadata(wallet.metadataJson)
    if (privyWalletId) {
      await assertPortalPrivyWalletOwnership({
        personId: args.personId,
        privyWalletId,
        walletAddress: address,
      })
      return privyWalletId
    }
  }

  throw new Error(
    'Wallet Privy introuvable pour cette adresse — reconnectez-vous ou rouvrez Mon wallet crypto.',
  )
}
