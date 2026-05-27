import { MORPHO_GRAPHQL_URL } from '@/lib/portal/morphoConstants'

type GraphqlError = { message?: string }

export type LombardMorphoMarketRow = {
  marketId: string
  loanAsset: { address: string; symbol: string; decimals: number }
  collateralAsset: { address: string; symbol: string; decimals: number }
  lltv: string
  oracle: { address: string }
  irmAddress: string
  state: {
    borrowApy: number | null
    borrowAssets: string | null
    liquidityAssets: string | null
  } | null
}

const MARKET_BY_ID_QUERY = `
  query LombardMarketById($chainId: Int!, $marketId: String!) {
    marketByUniqueKey(uniqueKey: $marketId, chainId: $chainId) {
      uniqueKey
      loanAsset {
        address
        symbol
        decimals
      }
      collateralAsset {
        address
        symbol
        decimals
      }
      lltv
      oracle {
        address
      }
      irmAddress
      state {
        borrowApy
        borrowAssets
        liquidityAssets
      }
    }
  }
`

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
    const message =
      payload.errors?.map((e) => e.message).filter(Boolean).join('; ') || `Morpho GraphQL HTTP ${res.status}`
    throw new Error(message)
  }
  if (!payload.data) {
    throw new Error('Morpho GraphQL: empty response.')
  }
  return payload.data
}

export async function fetchLombardMorphoMarket(args: {
  marketId: string
  chainId: number
}): Promise<LombardMorphoMarketRow | null> {
  const data = await morphoGraphqlRequest<{
    marketByUniqueKey?: {
      uniqueKey?: string
      loanAsset?: { address?: string; symbol?: string; decimals?: number }
      collateralAsset?: { address?: string; symbol?: string; decimals?: number }
      lltv?: string
      oracle?: { address?: string }
      irmAddress?: string
      state?: {
        borrowApy?: number | null
        borrowAssets?: string | null
        liquidityAssets?: string | null
      } | null
    } | null
  }>(MARKET_BY_ID_QUERY, {
    chainId: args.chainId,
    marketId: args.marketId,
  })

  const row = data.marketByUniqueKey
  if (!row?.uniqueKey || !row.loanAsset?.address || !row.collateralAsset?.address) {
    return null
  }
  if (!row.oracle?.address || !row.irmAddress) {
    return null
  }

  return {
    marketId: row.uniqueKey,
    loanAsset: {
      address: row.loanAsset.address,
      symbol: row.loanAsset.symbol ?? 'USDC',
      decimals: row.loanAsset.decimals ?? 6,
    },
    collateralAsset: {
      address: row.collateralAsset.address,
      symbol: row.collateralAsset.symbol ?? '',
      decimals: row.collateralAsset.decimals ?? 18,
    },
    lltv: String(row.lltv ?? '0'),
    oracle: { address: row.oracle.address },
    irmAddress: row.irmAddress,
    state: row.state
      ? {
          borrowApy: row.state.borrowApy ?? null,
          borrowAssets: row.state.borrowAssets != null ? String(row.state.borrowAssets) : null,
          liquidityAssets: row.state.liquidityAssets != null ? String(row.state.liquidityAssets) : null,
        }
      : null,
  }
}
