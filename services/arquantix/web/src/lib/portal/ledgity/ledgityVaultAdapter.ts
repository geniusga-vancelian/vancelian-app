import type { Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import {
  LEDGITY_CHAIN_ID,
  normalizeVaultAddress,
} from '@/lib/portal/ledgity/ledgityConstants'
import { isLedgityVaultsEnabled } from '@/lib/portal/ledgity/ledgityConfig'
import { isLedgityLocalSandboxEnabled } from '@/lib/portal/ledgity/ledgityLocalSandboxConfig'
import {
  getSandboxMockVaultCatalog,
  listSandboxMockVaultCatalogs,
} from '@/lib/portal/ledgity/mocks/ledgityLocalSandbox'
import {
  LEDGITY_ERC20_METADATA_ABI,
  LEDGITY_ERC4626_ABI,
} from '@/lib/portal/ledgity/ledgityVaultAbi'
import type {
  LedgityVaultMetrics,
  LedgityVaultPositionRow,
  PortalLedgityCatalogVault,
} from '@/lib/portal/ledgity/ledgityVaultTypes'

function getBasePublicClient() {
  return createBasePublicClient({ side: 'server' })
}

function stablecoinUsdFromRaw(raw: bigint, decimals: number): number | null {
  const value = Number(raw) / 10 ** decimals
  return Number.isFinite(value) ? value : null
}

function computePricePerShareFromRaw(assetsRaw: bigint, sharesRaw: bigint, assetDecimals: number): number | null {
  if (sharesRaw <= BigInt(0)) return null
  const assets = Number(assetsRaw) / 10 ** assetDecimals
  const shares = Number(sharesRaw) / 1e18
  if (!Number.isFinite(assets) || !Number.isFinite(shares) || shares <= 0) return null
  return assets / shares
}

async function readVaultAsset(vaultAddress: Address): Promise<{ address: string; symbol: string; decimals: number }> {
  const client = getBasePublicClient()
  const assetAddress = (await client.readContract({
    address: vaultAddress,
    abi: LEDGITY_ERC4626_ABI,
    functionName: 'asset',
  })) as Address

  const [symbol, decimals] = await Promise.all([
    client.readContract({
      address: assetAddress,
      abi: LEDGITY_ERC20_METADATA_ABI,
      functionName: 'symbol',
    }) as Promise<string>,
    client.readContract({
      address: assetAddress,
      abi: LEDGITY_ERC20_METADATA_ABI,
      functionName: 'decimals',
    }) as Promise<number>,
  ])

  return {
    address: assetAddress,
    symbol: (symbol || 'USDC').toUpperCase(),
    decimals: Number(decimals) || 6,
  }
}

export async function readLedgityVaultMetrics(args: {
  vaultAddress: string
  chainId?: number
}): Promise<LedgityVaultMetrics | null> {
  if (!isLedgityVaultsEnabled()) return null

  const chainId = args.chainId ?? LEDGITY_CHAIN_ID
  if (chainId !== LEDGITY_CHAIN_ID) return null

  const vaultAddress = args.vaultAddress as Address
  const client = getBasePublicClient()

  try {
    const asset = await readVaultAsset(vaultAddress)
    const totalAssetsRaw = (await client.readContract({
      address: vaultAddress,
      abi: LEDGITY_ERC4626_ABI,
      functionName: 'totalAssets',
    })) as bigint

    const oneShare = BigInt(10) ** BigInt(18)
    const assetsForOneShare = (await client.readContract({
      address: vaultAddress,
      abi: LEDGITY_ERC4626_ABI,
      functionName: 'convertToAssets',
      args: [oneShare],
    })) as bigint

    return {
      totalAssetsRaw,
      pricePerShare: computePricePerShareFromRaw(assetsForOneShare, oneShare, asset.decimals),
      asset,
      tvlUsd: stablecoinUsdFromRaw(totalAssetsRaw, asset.decimals),
    }
  } catch (error) {
    console.error('[ledgityVaultAdapter] readLedgityVaultMetrics failed', {
      vaultAddress: args.vaultAddress,
      error,
    })
    return null
  }
}

export async function fetchLedgityVaultCatalog(args: {
  addresses: string[]
  chainId?: number
}): Promise<PortalLedgityCatalogVault[]> {
  const addresses = [...new Set(args.addresses.map(normalizeVaultAddress).filter(Boolean))]
  if (!addresses.length) return []

  if (isLedgityLocalSandboxEnabled()) {
    return listSandboxMockVaultCatalogs(addresses)
  }

  if (!isLedgityVaultsEnabled()) {
    return addresses.map((address) => ({
      address,
      name: 'Vault Ledgity',
      symbol: 'vault',
      listed: true,
      asset: { address: '', symbol: 'USDC', decimals: 6 },
      netApy: null,
      pricePerShare: null,
      tvlUsd: null,
      liquidityUsd: null,
    }))
  }

  const catalogs: PortalLedgityCatalogVault[] = []
  for (const address of addresses) {
    const metrics = await readLedgityVaultMetrics({ vaultAddress: address, chainId: args.chainId })
    if (!metrics) {
      catalogs.push({
        address,
        name: 'Vault Ledgity',
        symbol: 'vault',
        listed: true,
        asset: { address: '', symbol: 'USDC', decimals: 6 },
        netApy: null,
        pricePerShare: null,
        tvlUsd: null,
        liquidityUsd: null,
      })
      continue
    }

    const sandboxMeta = getSandboxMockVaultCatalog(address)
    catalogs.push({
      address,
      name: sandboxMeta?.name ?? `Ledgity ${metrics.asset.symbol}`,
      symbol: sandboxMeta?.symbol ?? `ly${metrics.asset.symbol}`,
      listed: true,
      asset: metrics.asset,
      netApy: sandboxMeta?.netApy ?? null,
      pricePerShare: metrics.pricePerShare,
      tvlUsd: metrics.tvlUsd,
      liquidityUsd: metrics.tvlUsd,
      curator: sandboxMeta?.curator ?? 'Ledgity',
      description: sandboxMeta?.description ?? null,
    })
  }

  return catalogs
}

export async function fetchLedgityVaultPosition(args: {
  vaultAddress: string
  walletAddress: string
  chainId?: number
}): Promise<LedgityVaultPositionRow | null> {
  const chainId = args.chainId ?? LEDGITY_CHAIN_ID
  if (chainId !== LEDGITY_CHAIN_ID) return null

  if (isLedgityLocalSandboxEnabled()) {
    return null
  }

  if (!isLedgityVaultsEnabled()) return null

  const vaultAddress = args.vaultAddress as Address
  const walletAddress = args.walletAddress as Address
  const client = getBasePublicClient()

  try {
    const asset = await readVaultAsset(vaultAddress)
    const sharesRaw = (await client.readContract({
      address: vaultAddress,
      abi: LEDGITY_ERC4626_ABI,
      functionName: 'balanceOf',
      args: [walletAddress],
    })) as bigint

    if (sharesRaw <= BigInt(0)) return null

    const assetsRaw = (await client.readContract({
      address: vaultAddress,
      abi: LEDGITY_ERC4626_ABI,
      functionName: 'convertToAssets',
      args: [sharesRaw],
    })) as bigint

    return {
      assets: assetsRaw.toString(),
      shares: sharesRaw.toString(),
      assetsUsd: stablecoinUsdFromRaw(assetsRaw, asset.decimals),
      asset,
    }
  } catch (error) {
    console.error('[ledgityVaultAdapter] fetchLedgityVaultPosition failed', {
      vaultAddress: args.vaultAddress,
      walletAddress: args.walletAddress,
      error,
    })
    return null
  }
}
