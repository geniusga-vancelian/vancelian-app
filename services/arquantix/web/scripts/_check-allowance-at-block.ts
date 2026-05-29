import { createPublicClient, erc20Abi, formatUnits, http } from 'viem'
import { base } from 'viem/chains'

const rpc = process.env.ALCHEMY_RPC!
const wallet = '0x7ae683c429ec2bc66bf1eb93713b5644dd265a44' as const
const cbbtc = '0xcbB7C0000aB88B473b1f5aFd9ef808440eed33Bf' as const
const morpho = '0xBBBBBbbBBb9cC5e90e3b3Af64bdAF62C37EEFFCb' as const
const block = BigInt(process.argv[2] || '46586425')

async function main() {
  const client = createPublicClient({ chain: base, transport: http(rpc) })
  const [bal, allow] = await Promise.all([
    client.readContract({
      address: cbbtc,
      abi: erc20Abi,
      functionName: 'balanceOf',
      args: [wallet],
      blockNumber: block,
    }),
    client.readContract({
      address: cbbtc,
      abi: erc20Abi,
      functionName: 'allowance',
      args: [wallet, morpho],
      blockNumber: block,
    }),
  ])
  console.log(
    JSON.stringify({
      block: block.toString(),
      balanceCbbtc: formatUnits(bal, 8),
      allowanceMorpho: formatUnits(allow, 8),
      needGuarantee: '0.000258',
      balanceOk: bal >= BigInt(25800),
      allowanceOk: allow >= BigInt(25800),
    }),
  )
}

main()
