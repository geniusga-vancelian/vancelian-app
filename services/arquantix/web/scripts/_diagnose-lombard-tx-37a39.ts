import { erc20Abi, formatUnits } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { buildLombardQuote } from '@/lib/portal/lombard/lombardQuote'
import { buildLombardOpenLoanTransactions } from '@/lib/portal/lombard/lombardTx'
import { computeMaxIncrementalBorrowRaw, readLombardPositionBorrowSnapshot } from '@/lib/portal/lombard/lombardBorrowMath'
import { lombardTargetLtvPercentToWad } from '@/lib/portal/lombard/lombardBorrowLtv'
import { lombardMaxUserLtvWad } from '@/lib/portal/lombard/lombardConfig'
import { resolveLombardMarket } from '@/lib/portal/lombard/lombardMarket'

const wallet = '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44' as const
const block = BigInt(process.argv[2] || '46586425')
const borrowAmount = '10'
const targetLtv = 55

async function readBalanceAtBlock(token: `0x${string}`, decimals: number) {
  const client = createBasePublicClient({ side: 'server' })
  const raw = await client.readContract({
    address: token,
    abi: erc20Abi,
    functionName: 'balanceOf',
    args: [wallet],
    blockNumber: block,
  })
  return { raw, human: formatUnits(raw, decimals) }
}

async function main() {
  const client = createBasePublicClient({ side: 'server' })
  const resolved = await resolveLombardMarket({ collateral: 'cbBTC' })
  const { gql, morphoMarket } = resolved
  const token = gql.collateralAsset.address as `0x${string}`

  const [walletAtBlock, walletNow, positionData, marketData] = await Promise.all([
    readBalanceAtBlock(token, gql.collateralAsset.decimals),
    client.readContract({
      address: token,
      abi: erc20Abi,
      functionName: 'balanceOf',
      args: [wallet],
    }),
    morphoMarket.getPositionData(wallet),
    morphoMarket.getMarketData(),
  ])

  const position = readLombardPositionBorrowSnapshot(positionData)
  const targetLtvWad = lombardTargetLtvPercentToWad(targetLtv)
  const maxAtTarget = computeMaxIncrementalBorrowRaw({
    marketData,
    position,
    walletCollateralRaw: walletAtBlock.raw,
    maxLtvWad: targetLtvWad,
  })
  const maxAt70 = computeMaxIncrementalBorrowRaw({
    marketData,
    position,
    walletCollateralRaw: walletAtBlock.raw,
    maxLtvWad: lombardMaxUserLtvWad(),
  })

  let quote
  try {
    quote = await buildLombardQuote({
      collateral: 'cbBTC',
      borrowAmount,
      walletAddress: wallet,
      targetLtvPercent: targetLtv,
    })
  } catch (e) {
    quote = { error: e instanceof Error ? e.message : String(e) }
  }

  let txs
  try {
    if (quote && !('error' in quote)) {
      txs = await buildLombardOpenLoanTransactions({
        collateral: 'cbBTC',
        walletAddress: wallet,
        guaranteeAmountRaw: BigInt(quote.guaranteeAmountRaw),
        borrowAmountRaw: BigInt(quote.borrowAmountRaw),
      })
    }
  } catch (e) {
    txs = { error: e instanceof Error ? e.message : String(e) }
  }

  const openLoan = Array.isArray(txs) ? txs.find((t) => t.operation === 'open_loan') : null
  let simulateRevert: string | null = null
  if (openLoan) {
    try {
      await client.call({
        account: wallet,
        to: openLoan.to,
        data: openLoan.data,
        blockNumber: block,
      })
      simulateRevert = 'call_ok_at_block'
    } catch (e) {
      simulateRevert = e instanceof Error ? e.message.slice(0, 500) : String(e)
    }
  }

  console.log(
    JSON.stringify(
      {
        block: block.toString(),
        position: {
          collateral: formatUnits(position.collateralRaw, gql.collateralAsset.decimals),
          borrowUsdc: formatUnits(position.borrowAssetsRaw, gql.loanAsset.decimals),
        },
        walletCbbtcAtBlock: walletAtBlock.human,
        walletCbbtcNow: formatUnits(walletNow, gql.collateralAsset.decimals),
        maxIncrementalUsdcAt55: maxAtTarget != null ? formatUnits(maxAtTarget, 6) : null,
        maxIncrementalUsdcAt70: maxAt70 != null ? formatUnits(maxAt70, 6) : null,
        quote,
        txCount: Array.isArray(txs) ? txs.length : txs,
        simulateOpenLoan: simulateRevert,
      },
      null,
      2,
    ),
  )
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
