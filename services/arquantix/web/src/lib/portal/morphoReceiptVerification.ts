import type { Hash } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import { MORPHO_CHAIN_ID } from '@/lib/portal/morphoConstants'

export type VerifiedTxReceipt = {
  txHash: string
  chainId: number
  blockNumber: bigint
  status: 'success' | 'reverted'
}

function getBasePublicClient() {
  return createBasePublicClient({ side: 'server' })
}

/** Vérifie strictement un receipt on-chain (status, chainId, hash, block). */
export async function verifyMorphoTransactionReceipt(args: {
  txHash: string
  expectedChainId?: number
}): Promise<VerifiedTxReceipt> {
  const txHash = args.txHash.trim() as Hash
  if (!/^0x[0-9a-fA-F]{64}$/.test(txHash)) {
    throw new Error('Hash de transaction invalide.')
  }

  const client = getBasePublicClient()
  const receipt = await client.getTransactionReceipt({ hash: txHash })
  if (!receipt) {
    throw new Error('Receipt introuvable.')
  }

  const expectedChainId = args.expectedChainId ?? MORPHO_CHAIN_ID
  if (expectedChainId !== MORPHO_CHAIN_ID) {
    throw new Error('Chaîne non supportée.')
  }

  const blockNumber = receipt.blockNumber
  if (blockNumber == null) {
    throw new Error('Numéro de bloc absent du receipt.')
  }

  const status = receipt.status === 'success' ? 'success' : 'reverted'
  return {
    txHash: receipt.transactionHash,
    chainId: expectedChainId,
    blockNumber,
    status,
  }
}
