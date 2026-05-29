import { erc20Abi, formatUnits } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { computeMaxIncrementalBorrowRaw, readLombardPositionBorrowSnapshot } from '@/lib/portal/lombard/lombardBorrowMath'
import { lombardMaxUserLtvWad } from '@/lib/portal/lombard/lombardConfig'
import { resolveLombardMarket } from '@/lib/portal/lombard/lombardMarket'
import { MorphoClient } from '@morpho-org/morpho-sdk'

const wallet = (process.env.WALLET_ADDRESS?.trim() || '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44') as `0x${string}`

async function main() {
  const client = createBasePublicClient({ side: 'server' })
  const morpho = new MorphoClient(client, { supportSignature: false })

  for (const col of ['cbBTC', 'cbETH'] as const) {
    const resolved = await resolveLombardMarket({ collateral: col })
    const { gql, morphoMarket } = resolved
    const [marketData, balance, positionData] = await Promise.all([
      morphoMarket.getMarketData(),
      client.readContract({
        address: gql.collateralAsset.address as `0x${string}`,
        abi: erc20Abi,
        functionName: 'balanceOf',
        args: [wallet],
      }),
      morphoMarket.getPositionData(wallet),
    ])
    const pos = readLombardPositionBorrowSnapshot(positionData)
    const max70 = computeMaxIncrementalBorrowRaw({
      marketData,
      position: pos,
      walletCollateralRaw: balance,
      maxLtvWad: lombardMaxUserLtvWad(),
    })
    console.log(
      JSON.stringify({
        collateral: col,
        walletCollateral: formatUnits(balance, gql.collateralAsset.decimals),
        positionCollateral: formatUnits(pos.collateralRaw, gql.collateralAsset.decimals),
        positionBorrowUsdc: formatUnits(pos.borrowAssetsRaw, gql.loanAsset.decimals),
        maxIncrementalBorrowUsdc: max70 != null ? formatUnits(max70, gql.loanAsset.decimals) : null,
        liquidityUsdc: gql.state?.liquidityAssets
          ? formatUnits(BigInt(gql.state.liquidityAssets), gql.loanAsset.decimals)
          : null,
      }),
    )
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
