import { encodeFunctionData, erc20Abi, type Address } from 'viem'

import { createSwapPublicClient } from '@/lib/portal/swapEvmRpc'
import type { PortalTxRequest } from '@/lib/wallet/usePortalTxSigner'

export type SwapTokenApprovalPayload = {
  required: boolean
  token_address?: string | null
  spender_address?: string | null
  amount_atomic?: string | null
}

const NATIVE_TOKEN = '0x0000000000000000000000000000000000000000'

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function isSwapTokenApprovalRequired(
  approval?: SwapTokenApprovalPayload | null,
): approval is SwapTokenApprovalPayload & {
  token_address: string
  spender_address: string
  amount_atomic: string
} {
  if (!approval?.required) return false
  const token = approval.token_address?.trim()
  const spender = approval.spender_address?.trim()
  const amount = approval.amount_atomic?.trim()
  if (!token || !spender || !amount) return false
  if (token.toLowerCase() === NATIVE_TOKEN) return false
  return true
}

export async function readSwapTokenAllowance(args: {
  chainId: number
  owner: Address
  tokenAddress: Address
  spenderAddress: Address
}): Promise<bigint> {
  const client = createSwapPublicClient(args.chainId)
  return client.readContract({
    address: args.tokenAddress,
    abi: erc20Abi,
    functionName: 'allowance',
    args: [args.owner, args.spenderAddress],
  })
}

export function buildSwapApproveTransaction(args: {
  chainId: number
  tokenAddress: Address
  spenderAddress: Address
  amountAtomic: bigint
}): PortalTxRequest {
  const data = encodeFunctionData({
    abi: erc20Abi,
    functionName: 'approve',
    args: [args.spenderAddress, args.amountAtomic],
  })

  return {
    chainId: args.chainId,
    to: args.tokenAddress,
    data,
    value: BigInt(0),
  }
}

export async function ensureSwapTokenApproval(args: {
  chainId: number
  walletAddress: Address
  approval: SwapTokenApprovalPayload
  sendTransaction: (tx: PortalTxRequest) => Promise<{ hash: string }>
}): Promise<boolean> {
  if (!isSwapTokenApprovalRequired(args.approval)) {
    return false
  }

  const tokenAddress = args.approval.token_address as Address
  const spenderAddress = args.approval.spender_address as Address
  const requiredAmount = BigInt(args.approval.amount_atomic)

  const allowance = await readSwapTokenAllowance({
    chainId: args.chainId,
    owner: args.walletAddress,
    tokenAddress,
    spenderAddress,
  })

  if (allowance >= requiredAmount) {
    return false
  }

  const { hash } = await args.sendTransaction(
    buildSwapApproveTransaction({
      chainId: args.chainId,
      tokenAddress,
      spenderAddress,
      amountAtomic: requiredAmount,
    }),
  )

  const client = createSwapPublicClient(args.chainId)
  const started = Date.now()
  while (Date.now() - started < 180_000) {
    const receipt = await client.getTransactionReceipt({ hash: hash as `0x${string}` }).catch(() => null)
    if (receipt) {
      if (receipt.status !== 'success') {
        throw new Error('Approbation USDT/ERC-20 échouée on-chain — réessayez.')
      }
      return true
    }
    await sleep(3_000)
  }

  throw new Error('Approbation en attente trop longue — vérifiez MetaMask puis réessayez.')
}
