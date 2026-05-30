import { encodeFunctionData, erc20Abi, maxUint256, type Address } from 'viem'

import { createSwapPublicClient } from '@/lib/portal/swapEvmRpc'
import { portalEvmChainLabel } from '@/lib/wallet/portalEvmChain'
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

export function assertSwapTokenApprovalPayload(
  approval: SwapTokenApprovalPayload | null | undefined,
): void {
  if (!approval?.required) return
  if (isSwapTokenApprovalRequired(approval)) return
  throw new Error(
    'Approbation ERC-20 requise mais incomplète côté serveur — refaites une estimation depuis l’étape montant.',
  )
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
}): PortalTxRequest {
  const data = encodeFunctionData({
    abi: erc20Abi,
    functionName: 'approve',
    args: [args.spenderAddress, maxUint256],
  })

  return {
    chainId: args.chainId,
    to: args.tokenAddress,
    data,
    value: BigInt(0),
  }
}

export type SwapTokenApprovalResult = {
  submitted: boolean
  approvalTxHash?: string
}

export async function ensureSwapTokenApproval(args: {
  chainId: number
  walletAddress: Address
  approval: SwapTokenApprovalPayload
  assetSymbol?: string
  sendTransaction: (
    tx: PortalTxRequest,
    errorContext?: { phase?: 'approve' | 'swap'; assetSymbol?: string },
  ) => Promise<{ hash: string }>
}): Promise<SwapTokenApprovalResult> {
  assertSwapTokenApprovalPayload(args.approval)
  if (!isSwapTokenApprovalRequired(args.approval)) {
    return { submitted: false }
  }

  const tokenAddress = args.approval.token_address as Address
  const spenderAddress = args.approval.spender_address as Address
  const requiredAmount = BigInt(args.approval.amount_atomic)
  const chainLabel = portalEvmChainLabel(args.chainId)

  const allowance = await readSwapTokenAllowance({
    chainId: args.chainId,
    owner: args.walletAddress,
    tokenAddress,
    spenderAddress,
  })

  if (allowance >= requiredAmount) {
    return { submitted: false }
  }

  const { hash } = await args.sendTransaction(
    buildSwapApproveTransaction({
      chainId: args.chainId,
      tokenAddress,
      spenderAddress,
    }),
    { phase: 'approve', assetSymbol: args.assetSymbol },
  )

  const client = createSwapPublicClient(args.chainId)
  const started = Date.now()
  while (Date.now() - started < 180_000) {
    const receipt = await client.getTransactionReceipt({ hash: hash as `0x${string}` }).catch(() => null)
    if (receipt) {
      if (receipt.status !== 'success') {
        throw new Error(
          `Approbation ${args.assetSymbol ?? 'ERC-20'} échouée on-chain sur ${chainLabel} — réessayez.`,
        )
      }
      return { submitted: true, approvalTxHash: hash }
    }
    await sleep(3_000)
  }

  throw new Error(
    `Approbation ${args.assetSymbol ?? 'ERC-20'} en attente trop longue sur ${chainLabel} — vérifiez votre wallet puis réessayez.`,
  )
}
