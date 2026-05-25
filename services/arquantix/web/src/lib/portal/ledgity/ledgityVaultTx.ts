import { encodeFunctionData, type Address } from 'viem'

import { LEDGITY_CHAIN_ID } from '@/lib/portal/ledgity/ledgityConstants'
import {
  LEDGITY_ERC20_APPROVE_ABI,
  LEDGITY_ERC4626_ABI,
} from '@/lib/portal/ledgity/ledgityVaultAbi'
import { parseHumanAmountToRaw } from '@/lib/portal/ledgity/ledgityVaultFormat'
import type { PortalLedgityPreparedTx } from '@/lib/portal/ledgity/ledgityVaultTypes'

function mapPreparedTx(args: {
  to: Address
  data: `0x${string}`
  chainId: number
  operation: PortalLedgityPreparedTx['operation']
}): PortalLedgityPreparedTx {
  return {
    to: args.to,
    data: args.data,
    value: '0x0',
    chainId: args.chainId,
    operation: args.operation,
  }
}

export async function buildLedgityVaultTransactions(args: {
  vaultAddress: string
  assetAddress: string
  walletAddress: string
  operation: 'deposit' | 'withdraw'
  amount: string
  assetDecimals: number
}): Promise<PortalLedgityPreparedTx[]> {
  const chainId = LEDGITY_CHAIN_ID
  const vaultAddress = args.vaultAddress as Address
  const assetAddress = args.assetAddress as Address
  const userAddress = args.walletAddress as Address
  const rawAmount = parseHumanAmountToRaw(args.amount, args.assetDecimals)

  if (rawAmount <= BigInt(0)) {
    throw new Error('Montant invalide.')
  }

  if (args.operation === 'withdraw') {
    const data = encodeFunctionData({
      abi: LEDGITY_ERC4626_ABI,
      functionName: 'withdraw',
      args: [rawAmount, userAddress, userAddress],
    })
    return [mapPreparedTx({ to: vaultAddress, data, chainId, operation: 'withdraw' })]
  }

  const approveData = encodeFunctionData({
    abi: LEDGITY_ERC20_APPROVE_ABI,
    functionName: 'approve',
    args: [vaultAddress, rawAmount],
  })
  const depositData = encodeFunctionData({
    abi: LEDGITY_ERC4626_ABI,
    functionName: 'deposit',
    args: [rawAmount, userAddress],
  })

  return [
    mapPreparedTx({ to: assetAddress, data: approveData, chainId, operation: 'approve' }),
    mapPreparedTx({ to: vaultAddress, data: depositData, chainId, operation: 'deposit' }),
  ]
}
