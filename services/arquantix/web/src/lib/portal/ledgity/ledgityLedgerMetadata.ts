import type { Prisma } from '@prisma/client'

import { resolveLedgityShareSymbol } from '@/lib/portal/ledgity/ledgityConstants'
import type { WalletSourceMetadata } from '@/lib/wallet/executionWalletTypes'

export type LedgityLedgerMetadataInput = {
  vaultAddress: string
  assetSymbol: string
  walletSource?: WalletSourceMetadata
  ppsAtTx?: string | number | null
  extra?: Record<string, unknown>
}

/** Metadata ledger standard pour les txs Ledgity (protocol, share_symbol, pps_at_tx). */
export function buildLedgityLedgerMetadata(args: LedgityLedgerMetadataInput): Prisma.InputJsonValue {
  const shareSymbol = resolveLedgityShareSymbol(args.vaultAddress, args.assetSymbol)
  const payload: Record<string, unknown> = {
    protocol: 'ledgity',
    integration_mode: 'ledgity_vault',
    asset_symbol: args.assetSymbol,
    share_symbol: shareSymbol,
    ...(args.walletSource?.wallet_source ? { wallet_source: args.walletSource.wallet_source } : {}),
    ...(args.walletSource?.external_wallet_id ? { external_wallet_id: args.walletSource.external_wallet_id } : {}),
    ...(args.walletSource?.wallet_provider ? { wallet_provider: args.walletSource.wallet_provider } : {}),
    ...(args.extra ?? {}),
  }

  if (args.ppsAtTx != null && args.ppsAtTx !== '') {
    payload.pps_at_tx = String(args.ppsAtTx)
  }

  return payload as Prisma.InputJsonValue
}

export function readLedgityPpsFromLedgerMetadata(metadata: unknown): string | null {
  if (!metadata || typeof metadata !== 'object') return null
  const row = metadata as Record<string, unknown>
  const value = row.pps_at_tx ?? row.ppsAtTx
  return typeof value === 'string' || typeof value === 'number' ? String(value) : null
}
