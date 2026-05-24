import {
  MORPHO_CHAIN_ID,
  MORPHO_GRAPHQL_URL,
  normalizeVaultAddress,
  type MorphoVaultVersion,
} from '@/lib/portal/morphoConstants'
import type { PortalMorphoCatalogVault } from '@/lib/portal/morphoVaultTypes'

type GraphqlError = { message?: string }

async function morphoGraphqlRequest<T>(query: string, variables?: Record<string, unknown>): Promise<T> {
  const res = await fetch(MORPHO_GRAPHQL_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({ query, variables }),
    cache: 'no-store',
  })
  const payload = (await res.json().catch(() => ({}))) as {
    data?: T
    errors?: GraphqlError[]
  }
  if (!res.ok || payload.errors?.length) {
    const message = payload.errors?.map((e) => e.message).filter(Boolean).join('; ') || `Morpho GraphQL HTTP ${res.status}`
    throw new Error(message)
  }
  if (!payload.data) {
    throw new Error('Morpho GraphQL: réponse vide.')
  }
  return payload.data
}

async function morphoGraphqlRequestSafe<T>(query: string, variables?: Record<string, unknown>): Promise<T | null> {
  try {
    return await morphoGraphqlRequest<T>(query, variables)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    if (message.includes('No results matching') || message.includes('NOT_FOUND')) {
      return null
    }
    throw error
  }
}

const CATALOG_V1_QUERY = `
  query MorphoBaseVaultCatalogV1($chainId: Int!) {
    vaults(first: 1000, where: { chainId_in: [$chainId], listed: true }) {
      items {
        address
        name
        symbol
        listed
        asset {
          address
          symbol
          decimals
        }
        state {
          netApy
          totalAssetsUsd
          curators {
            name
          }
        }
        metadata {
          description
        }
      }
    }
  }
`

const CATALOG_V2_QUERY = `
  query MorphoBaseVaultCatalogV2($chainId: Int!) {
    vaultV2s(first: 1000, where: { chainId_in: [$chainId], listed: true }) {
      items {
        address
        name
        symbol
        listed
        asset {
          address
          symbol
          decimals
        }
        avgNetApy
        totalAssetsUsd
        liquidityUsd
        metadata {
          description
        }
        curators {
          items {
            name
          }
        }
      }
    }
  }
`

const VAULTS_V1_BY_ADDRESSES_QUERY = `
  query MorphoVaultsV1ByAddresses($chainId: Int!, $addresses: [String!]!, $first: Int!) {
    vaults(first: $first, where: { chainId_in: [$chainId], address_in: $addresses }) {
      items {
        address
        name
        symbol
        listed
        asset {
          address
          symbol
          decimals
        }
        state {
          netApy
          totalAssetsUsd
          curators {
            name
          }
        }
        metadata {
          description
        }
      }
    }
  }
`

const VAULTS_V2_BY_ADDRESSES_QUERY = `
  query MorphoVaultsV2ByAddresses($chainId: Int!, $addresses: [String!]!, $first: Int!) {
    vaultV2s(first: $first, where: { chainId_in: [$chainId], address_in: $addresses }) {
      items {
        address
        name
        symbol
        listed
        asset {
          address
          symbol
          decimals
        }
        avgNetApy
        totalAssetsUsd
        liquidityUsd
        metadata {
          description
        }
        curators {
          items {
            name
          }
        }
      }
    }
  }
`

const VAULT_V1_POSITION_QUERY = `
  query MorphoVaultV1Position($chainId: Int!, $vaultAddress: String!, $userAddress: String!) {
    vaultPosition(
      userAddress: $userAddress
      vaultAddress: $vaultAddress
      chainId: $chainId
    ) {
      state {
        assets
        shares
        assetsUsd
      }
      vault {
        asset {
          address
          symbol
          decimals
        }
      }
    }
  }
`

const VAULT_V2_POSITION_QUERY = `
  query MorphoVaultV2Position($chainId: Int!, $vaultAddress: String!, $userAddress: String!) {
    vaultV2PositionByAddress(
      userAddress: $userAddress
      vaultAddress: $vaultAddress
      chainId: $chainId
    ) {
      assets
      shares
      assetsUsd
      vault {
        asset {
          address
          symbol
          decimals
        }
      }
    }
  }
`

const RESOLVE_VAULT_V1_QUERY = `
  query ResolveMorphoVaultV1($chainId: Int!, $address: String!) {
    vaultByAddress(address: $address, chainId: $chainId) {
      address
    }
  }
`

const RESOLVE_VAULT_V2_QUERY = `
  query ResolveMorphoVaultV2($chainId: Int!, $address: String!) {
    vaultV2ByAddress(address: $address, chainId: $chainId) {
      address
    }
  }
`

type RawCatalogV1Item = {
  address: string
  name: string
  symbol: string
  listed: boolean
  asset?: { address?: string; symbol?: string; decimals?: number }
  state?: {
    netApy?: number | null
    totalAssetsUsd?: number | null
    curators?: Array<{ name?: string | null }>
  }
  metadata?: { description?: string | null }
}

type RawCatalogV2Item = {
  address: string
  name: string
  symbol: string
  listed: boolean
  asset?: { address?: string; symbol?: string; decimals?: number }
  avgNetApy?: number | null
  totalAssetsUsd?: number | null
  liquidityUsd?: number | null
  metadata?: { description?: string | null }
  curators?: { items?: Array<{ name?: string | null }> }
}

function mapCatalogV1Item(row: RawCatalogV1Item): PortalMorphoCatalogVault {
  return {
    address: row.address,
    name: row.name,
    symbol: row.symbol,
    listed: Boolean(row.listed),
    version: 'v1',
    asset: {
      address: row.asset?.address ?? '',
      symbol: (row.asset?.symbol ?? 'USDC').toUpperCase(),
      decimals: row.asset?.decimals ?? 6,
    },
    netApy: row.state?.netApy ?? null,
    tvlUsd: row.state?.totalAssetsUsd ?? null,
    liquidityUsd: row.state?.totalAssetsUsd ?? null,
    curator: row.state?.curators?.[0]?.name ?? null,
    description: row.metadata?.description ?? null,
  }
}

function mapCatalogV2Item(row: RawCatalogV2Item): PortalMorphoCatalogVault {
  return {
    address: row.address,
    name: row.name,
    symbol: row.symbol,
    listed: Boolean(row.listed),
    version: 'v2',
    asset: {
      address: row.asset?.address ?? '',
      symbol: (row.asset?.symbol ?? 'USDC').toUpperCase(),
      decimals: row.asset?.decimals ?? 6,
    },
    netApy: row.avgNetApy ?? null,
    tvlUsd: row.totalAssetsUsd ?? null,
    liquidityUsd: row.liquidityUsd ?? null,
    curator: row.curators?.items?.[0]?.name ?? null,
    description: row.metadata?.description ?? null,
  }
}

function mergeCatalogItems(v1: PortalMorphoCatalogVault[], v2: PortalMorphoCatalogVault[]): PortalMorphoCatalogVault[] {
  const byAddress = new Map<string, PortalMorphoCatalogVault>()
  for (const row of v1) {
    byAddress.set(normalizeVaultAddress(row.address), row)
  }
  for (const row of v2) {
    byAddress.set(normalizeVaultAddress(row.address), row)
  }
  return [...byAddress.values()].sort((a, b) => a.name.localeCompare(b.name, 'fr'))
}

export async function resolveMorphoVaultVersion(args: {
  vaultAddress: string
  chainId?: number
}): Promise<MorphoVaultVersion | null> {
  const chainId = args.chainId ?? MORPHO_CHAIN_ID
  const address = args.vaultAddress

  const [v2, v1] = await Promise.all([
    morphoGraphqlRequestSafe<{ vaultV2ByAddress?: { address?: string } | null }>(RESOLVE_VAULT_V2_QUERY, {
      chainId,
      address,
    }),
    morphoGraphqlRequestSafe<{ vaultByAddress?: { address?: string } | null }>(RESOLVE_VAULT_V1_QUERY, {
      chainId,
      address,
    }),
  ])

  if (v2?.vaultV2ByAddress?.address) return 'v2'
  if (v1?.vaultByAddress?.address) return 'v1'
  return null
}

export async function fetchMorphoBaseVaultCatalog(
  chainId = MORPHO_CHAIN_ID,
): Promise<PortalMorphoCatalogVault[]> {
  const [v1Data, v2Data] = await Promise.all([
    morphoGraphqlRequest<{ vaults: { items: RawCatalogV1Item[] } }>(CATALOG_V1_QUERY, { chainId }),
    morphoGraphqlRequest<{ vaultV2s: { items: RawCatalogV2Item[] } }>(CATALOG_V2_QUERY, { chainId }),
  ])
  return mergeCatalogItems(
    (v1Data.vaults?.items ?? []).map(mapCatalogV1Item),
    (v2Data.vaultV2s?.items ?? []).map(mapCatalogV2Item),
  )
}

function catalogFetchLimit(count: number): number {
  return Math.min(Math.max(count, 1), 50)
}

export async function fetchMorphoVaultsByAddresses(args: {
  addresses: string[]
  chainId?: number
}): Promise<PortalMorphoCatalogVault[]> {
  const chainId = args.chainId ?? MORPHO_CHAIN_ID
  const addresses = [...new Set(args.addresses.map(normalizeVaultAddress).filter(Boolean))]
  if (!addresses.length) return []

  const first = catalogFetchLimit(addresses.length)

  const [v1Data, v2Data] = await Promise.all([
    morphoGraphqlRequest<{ vaults: { items: RawCatalogV1Item[] } }>(VAULTS_V1_BY_ADDRESSES_QUERY, {
      chainId,
      addresses,
      first,
    }),
    morphoGraphqlRequest<{ vaultV2s: { items: RawCatalogV2Item[] } }>(VAULTS_V2_BY_ADDRESSES_QUERY, {
      chainId,
      addresses,
      first,
    }),
  ])

  return mergeCatalogItems(
    (v1Data.vaults?.items ?? []).map(mapCatalogV1Item),
    (v2Data.vaultV2s?.items ?? []).map(mapCatalogV2Item),
  )
}

export type MorphoVaultPositionRow = {
  assets: string
  shares: string
  assetsUsd: number | null
  asset: { address: string; symbol: string; decimals: number }
}

async function fetchMorphoVaultV1Position(args: {
  vaultAddress: string
  walletAddress: string
  chainId: number
}): Promise<MorphoVaultPositionRow | null> {
  const data = await morphoGraphqlRequestSafe<{
    vaultPosition?: {
      state?: { assets?: string; shares?: string; assetsUsd?: number | null }
      vault?: { asset?: { address?: string; symbol?: string; decimals?: number } }
    }
  }>(VAULT_V1_POSITION_QUERY, {
    chainId: args.chainId,
    vaultAddress: args.vaultAddress,
    userAddress: args.walletAddress,
  })
  const state = data?.vaultPosition?.state
  const assetRaw = data?.vaultPosition?.vault?.asset
  if (!state?.assets) return null
  return {
    assets: String(state.assets),
    shares: String(state.shares ?? '0'),
    assetsUsd: state.assetsUsd ?? null,
    asset: {
      address: assetRaw?.address ?? '',
      symbol: (assetRaw?.symbol ?? 'USDC').toUpperCase(),
      decimals: assetRaw?.decimals ?? 6,
    },
  }
}

async function fetchMorphoVaultV2Position(args: {
  vaultAddress: string
  walletAddress: string
  chainId: number
}): Promise<MorphoVaultPositionRow | null> {
  const data = await morphoGraphqlRequestSafe<{
    vaultV2PositionByAddress?: {
      assets?: string
      shares?: string
      assetsUsd?: number | null
      vault?: { asset?: { address?: string; symbol?: string; decimals?: number } }
    }
  }>(VAULT_V2_POSITION_QUERY, {
    chainId: args.chainId,
    vaultAddress: args.vaultAddress,
    userAddress: args.walletAddress,
  })
  const row = data?.vaultV2PositionByAddress
  const assetRaw = row?.vault?.asset
  if (!row?.assets) return null
  return {
    assets: String(row.assets),
    shares: String(row.shares ?? '0'),
    assetsUsd: row.assetsUsd ?? null,
    asset: {
      address: assetRaw?.address ?? '',
      symbol: (assetRaw?.symbol ?? 'USDC').toUpperCase(),
      decimals: assetRaw?.decimals ?? 6,
    },
  }
}

export async function fetchMorphoVaultPosition(args: {
  vaultAddress: string
  walletAddress: string
  chainId?: number
  version?: MorphoVaultVersion | null
}): Promise<MorphoVaultPositionRow | null> {
  const chainId = args.chainId ?? MORPHO_CHAIN_ID
  const version = args.version ?? (await resolveMorphoVaultVersion({ vaultAddress: args.vaultAddress, chainId }))

  if (version === 'v2') {
    return fetchMorphoVaultV2Position({ ...args, chainId })
  }
  if (version === 'v1') {
    return fetchMorphoVaultV1Position({ ...args, chainId })
  }
  return null
}
