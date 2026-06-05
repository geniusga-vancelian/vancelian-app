import { encodeFunctionData, type Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { LEDGITY_CHAIN_ID } from '@/lib/portal/ledgity/ledgityConstants'
import { LEDGITY_VAULT_LOCK_ABI } from '@/lib/portal/ledgity/ledgityVaultExtendedAbi'
import type { LedgityVaultWithdrawMode } from '@/lib/portal/ledgity/ledgityVaultProfiles'
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
  value?: bigint
}): PortalLedgityPreparedTx {
  return {
    to: args.to,
    data: args.data,
    value: args.value != null ? `0x${args.value.toString(16)}` : '0x0',
    chainId: args.chainId,
    operation: args.operation,
  }
}

async function readWithdrawalGasFeeWei(vaultAddress: Address): Promise<bigint> {
  try {
    const client = createBasePublicClient({ side: 'server' })
    return (await client.readContract({
      address: vaultAddress,
      abi: LEDGITY_VAULT_LOCK_ABI,
      functionName: 'withdrawalGasFee',
    })) as bigint
  } catch {
    return BigInt(0)
  }
}

async function assetsToShares(vaultAddress: Address, assetsRaw: bigint): Promise<bigint> {
  const client = createBasePublicClient({ side: 'server' })
  return (await client.readContract({
    address: vaultAddress,
    abi: LEDGITY_VAULT_LOCK_ABI,
    functionName: 'convertToShares',
    args: [assetsRaw],
  })) as bigint
}

export async function buildLedgityWithdrawTransaction(args: {
  vaultAddress: string
  walletAddress: string
  amount: string
  assetDecimals: number
  withdrawMode: LedgityVaultWithdrawMode
}): Promise<PortalLedgityPreparedTx[]> {
  const chainId = LEDGITY_CHAIN_ID
  const vaultAddress = args.vaultAddress as Address
  const userAddress = args.walletAddress as Address
  const rawAmount = parseHumanAmountToRaw(args.amount, args.assetDecimals)

  if (rawAmount <= BigInt(0)) {
    throw new Error('Montant invalide.')
  }

  if (args.withdrawMode === 'async_request') {
    const sharesRaw = await assetsToShares(vaultAddress, rawAmount)
    if (sharesRaw <= BigInt(0)) {
      throw new Error('Montant de parts invalide pour la demande de retrait.')
    }
    const gasFee = await readWithdrawalGasFeeWei(vaultAddress)
    const data = encodeFunctionData({
      abi: LEDGITY_VAULT_LOCK_ABI,
      functionName: 'requestWithdrawal',
      args: [sharesRaw],
    })
    return [
      mapPreparedTx({
        to: vaultAddress,
        data,
        chainId,
        operation: 'withdraw',
        value: gasFee,
      }),
    ]
  }

  const data = encodeFunctionData({
    abi: LEDGITY_ERC4626_ABI,
    functionName: 'withdraw',
    args: [rawAmount, userAddress, userAddress],
  })
  return [mapPreparedTx({ to: vaultAddress, data, chainId, operation: 'withdraw' })]
}

export async function buildLedgityVaultTransactions(args: {
  vaultAddress: string
  assetAddress: string
  walletAddress: string
  operation: 'deposit' | 'withdraw'
  amount: string
  assetDecimals: number
  withdrawMode?: LedgityVaultWithdrawMode
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
    return buildLedgityWithdrawTransaction({
      vaultAddress: args.vaultAddress,
      walletAddress: args.walletAddress,
      amount: args.amount,
      assetDecimals: args.assetDecimals,
      withdrawMode: args.withdrawMode ?? 'instant',
    })
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
