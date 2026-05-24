import { prisma } from '@/lib/prisma'
import { MORPHO_CHAIN_ID, normalizeVaultAddress } from '@/lib/portal/morphoConstants'
import { fetchMorphoVaultPosition } from '@/lib/portal/morphoGraphql'
import { listPublishedPortalMorphoVaultConfigs } from '@/lib/portal/morphoVaultConfigStore'
import { loadPrincipalNetRaw } from '@/lib/portal/morphoVaultLedger'
import { resolvePortalEarnWalletIdentity } from '@/lib/portal/resolvePortalEarnWalletIdentity'
import { fetchPrivyEarnVaultPosition } from '@/lib/portal/privyServerClient'

export type MorphoVaultBackfillResult = {
  walletsScanned: number
  positionsUpserted: number
  costBasisUnknown: number
  skipped: number
  errors: Array<{ personId: string; vaultAddress: string; message: string }>
}

async function fetchPositionForConfig(args: {
  config: Awaited<ReturnType<typeof listPublishedPortalMorphoVaultConfigs>>[number]
  walletAddress: string
  privyWalletId: string | null
}) {
  if (args.config.integrationMode === 'privy_earn' && args.privyWalletId && args.config.privyVaultId) {
    const row = await fetchPrivyEarnVaultPosition(args.privyWalletId, args.config.privyVaultId)
    const assetRaw = (row.asset ?? {}) as Record<string, unknown>
    return {
      assetsRaw: String(row.assets_in_vault ?? row.assetsInVault ?? '0'),
      sharesRaw: String(row.shares_in_vault ?? row.sharesInVault ?? '0'),
      assetSymbol: String(assetRaw.symbol ?? 'USDC').toUpperCase(),
      assetDecimals: Number(assetRaw.decimals ?? 6),
    }
  }

  const row = await fetchMorphoVaultPosition({
    vaultAddress: args.config.vaultAddress,
    walletAddress: args.walletAddress,
    chainId: args.config.chainId,
  })
  if (!row) return null
  return {
    assetsRaw: row.assets || '0',
    sharesRaw: row.shares || '0',
    assetSymbol: row.asset.symbol,
    assetDecimals: row.asset.decimals,
  }
}

/** Backfill positions Morpho USDC depuis positions on-chain. */
export async function backfillMorphoVaultPositions(): Promise<MorphoVaultBackfillResult> {
  const configs = await listPublishedPortalMorphoVaultConfigs()
  const wallets = await prisma.personCryptoWallet.findMany({
    where: {
      revokedAt: null,
      chainType: 'ethereum',
    },
    select: {
      personId: true,
      address: true,
      chainId: true,
      metadataJson: true,
    },
  })

  const result: MorphoVaultBackfillResult = {
    walletsScanned: wallets.length,
    positionsUpserted: 0,
    costBasisUnknown: 0,
    skipped: 0,
    errors: [],
  }

  for (const wallet of wallets) {
    let identity
    try {
      identity = await resolvePortalEarnWalletIdentity({ personId: wallet.personId })
    } catch {
      result.skipped += 1
      continue
    }

    for (const config of configs) {
      if (!config.vaultAddress?.trim()) continue
      const vaultAddress = normalizeVaultAddress(config.vaultAddress)

      try {
        const position = await fetchPositionForConfig({
          config,
          walletAddress: identity.walletAddress,
          privyWalletId: identity.privyWalletId,
        })
        if (!position || BigInt(position.assetsRaw || '0') === BigInt(0)) {
          result.skipped += 1
          continue
        }

        const principalNetRaw = await loadPrincipalNetRaw({
          personId: wallet.personId,
          vaultAddress,
          chainId: config.chainId ?? MORPHO_CHAIN_ID,
          walletAddress: identity.walletAddress,
        })

        const costBasisUnknown = principalNetRaw == null

        await prisma.userVaultPosition.upsert({
          where: {
            personId_chainId_vaultAddress_walletAddress: {
              personId: wallet.personId,
              chainId: config.chainId ?? MORPHO_CHAIN_ID,
              vaultAddress,
              walletAddress: identity.walletAddress,
            },
          },
          create: {
            personId: wallet.personId,
            vaultAddress,
            chainId: config.chainId ?? MORPHO_CHAIN_ID,
            chainType: 'evm',
            walletAddress: identity.walletAddress,
            privyWalletId: identity.privyWalletId,
            assetSymbol: position.assetSymbol,
            assetDecimals: position.assetDecimals,
            principalNetRaw: principalNetRaw ?? '0',
            costBasisUnknown,
            lastAssetsRaw: position.assetsRaw,
            lastSharesRaw: position.sharesRaw,
            lastSyncedAt: new Date(),
          },
          update: {
            privyWalletId: identity.privyWalletId,
            assetSymbol: position.assetSymbol,
            assetDecimals: position.assetDecimals,
            principalNetRaw: principalNetRaw ?? '0',
            costBasisUnknown,
            lastAssetsRaw: position.assetsRaw,
            lastSharesRaw: position.sharesRaw,
            lastSyncedAt: new Date(),
          },
        })

        result.positionsUpserted += 1
        if (costBasisUnknown) result.costBasisUnknown += 1
      } catch (error) {
        result.errors.push({
          personId: wallet.personId,
          vaultAddress,
          message: error instanceof Error ? error.message : 'Erreur inconnue.',
        })
      }
    }
  }

  return result
}
