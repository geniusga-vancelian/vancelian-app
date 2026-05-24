import { MorphoClient } from '@morpho-org/morpho-sdk'
import type { Address } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import {
  MORPHO_CHAIN_ID,
  type MorphoVaultVersion,
} from '@/lib/portal/morphoConstants'
import { resolveMorphoVaultVersion } from '@/lib/portal/morphoGraphql'
import { parseHumanAmountToRaw } from '@/lib/portal/morphoVaultFormat'
import type { PortalMorphoPreparedTx } from '@/lib/portal/morphoVaultTypes'

function getBasePublicClient() {
  return createBasePublicClient({ side: 'server' })
}

function mapSdkTx(
  tx: { to: Address; data: `0x${string}`; value?: bigint },
  chainId: number,
  operation: PortalMorphoPreparedTx['operation'],
): PortalMorphoPreparedTx {
  return {
    to: tx.to,
    data: tx.data,
    value: `0x${(tx.value ?? BigInt(0)).toString(16)}`,
    chainId,
    operation,
  }
}

function isApprovalTx(
  item: unknown,
): item is { to: Address; data: `0x${string}`; value?: bigint } {
  if (!item || typeof item !== 'object') return false
  const row = item as Record<string, unknown>
  if (row.type === 'permit' || row.type === 'permit2' || row.type === 'signature') return false
  return typeof row.to === 'string' && typeof row.data === 'string'
}

async function buildDepositTransactions(args: {
  morpho: MorphoClient
  version: MorphoVaultVersion
  vaultAddress: Address
  chainId: number
  rawAmount: bigint
  userAddress: Address
  assetAddress?: Address
}): Promise<PortalMorphoPreparedTx[]> {
  if (args.version === 'v2') {
    const vault = args.morpho.vaultV2(args.vaultAddress, args.chainId)
    const vaultData = await vault.getData()
    const { buildTx, getRequirements } = vault.deposit({
      amount: args.rawAmount,
      userAddress: args.userAddress,
      vaultData,
    })
    const requirements = await getRequirements()
    const approvalTxs: PortalMorphoPreparedTx[] = []
    for (const item of requirements) {
      if (isApprovalTx(item)) {
        approvalTxs.push(mapSdkTx(item, args.chainId, 'approve'))
      }
    }
    return [...approvalTxs, mapSdkTx(buildTx(), args.chainId, 'deposit')]
  }

  const vault = args.morpho.vaultV1(args.vaultAddress, args.chainId)
  const vaultData = await vault.getData()
  const { buildTx, getRequirements } = vault.deposit({
    amount: args.rawAmount,
    userAddress: args.userAddress,
    vaultData,
  })
  const requirements = await getRequirements()
  const approvalTxs: PortalMorphoPreparedTx[] = []
  for (const item of requirements) {
    if (isApprovalTx(item)) {
      approvalTxs.push(mapSdkTx(item, args.chainId, 'approve'))
    }
  }
  return [...approvalTxs, mapSdkTx(buildTx(), args.chainId, 'deposit')]
}

export async function buildMorphoVaultTransactions(args: {
  vaultAddress: string
  walletAddress: string
  operation: 'deposit' | 'withdraw'
  amount: string
  assetDecimals: number
  morphoVaultVersion?: MorphoVaultVersion | null
}): Promise<PortalMorphoPreparedTx[]> {
  const chainId = MORPHO_CHAIN_ID
  const publicClient = getBasePublicClient()
  const morpho = new MorphoClient(publicClient, { supportSignature: false })
  const vaultAddress = args.vaultAddress as Address
  const userAddress = args.walletAddress as Address
  const rawAmount = parseHumanAmountToRaw(args.amount, args.assetDecimals)
  const version =
    args.morphoVaultVersion ?? (await resolveMorphoVaultVersion({ vaultAddress: args.vaultAddress, chainId }))

  if (!version) {
    throw new Error('Vault Morpho introuvable sur Base.')
  }

  if (args.operation === 'withdraw') {
    const vault = version === 'v2' ? morpho.vaultV2(vaultAddress, chainId) : morpho.vaultV1(vaultAddress, chainId)
    const { buildTx } = vault.withdraw({ amount: rawAmount, userAddress })
    return [mapSdkTx(buildTx(), chainId, 'withdraw')]
  }

  return buildDepositTransactions({
    morpho,
    version,
    vaultAddress,
    chainId,
    rawAmount,
    userAddress,
  })
}
