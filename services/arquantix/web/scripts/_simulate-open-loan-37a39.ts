import { createPublicClient, http } from 'viem'
import { base } from 'viem/chains'

import { buildLombardOpenLoanTransactions } from '@/lib/portal/lombard/lombardTx'

const rpc = process.env.BASE_RPC_URL_PRIMARY || process.env.ALCHEMY_RPC
if (!rpc) throw new Error('Set ALCHEMY_RPC')

const wallet = '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44' as const
const block = BigInt('46586425')
const guaranteeRaw = BigInt('25800') // 0.000258 cbBTC @ 8 decimals
const borrowRaw = BigInt('10000000') // 10 USDC

async function main() {
  const client = createPublicClient({ chain: base, transport: http(rpc) })
  const txs = await buildLombardOpenLoanTransactions({
    collateral: 'cbBTC',
    walletAddress: wallet,
    guaranteeAmountRaw: guaranteeRaw,
    borrowAmountRaw: borrowRaw,
  })
  console.log('prepared_ops', txs.map((t) => t.operation))
  const open = txs.find((t) => t.operation === 'open_loan')
  if (!open) throw new Error('no open_loan')

  try {
    await client.call({
      account: wallet,
      to: open.to,
      data: open.data,
      blockNumber: block,
    })
    console.log('eth_call_at_block', 'OK')
  } catch (e) {
    const err = e as { shortMessage?: string; details?: string; cause?: unknown }
    console.log('eth_call_at_block', 'REVERT')
    console.log(String(err.shortMessage || err))
    console.log(String(err.details || ''))
  }

  try {
    await client.call({
      account: wallet,
      to: open.to,
      data: open.data,
    })
    console.log('eth_call_latest', 'OK')
  } catch (e) {
    const err = e as { shortMessage?: string; details?: string }
    console.log('eth_call_latest', 'REVERT')
    console.log(String(err.shortMessage || err))
    console.log(String(err.details || ''))
  }
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
