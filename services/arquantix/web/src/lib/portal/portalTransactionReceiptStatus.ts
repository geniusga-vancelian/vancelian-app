import { decodeAbiParameters, keccak256, toHex, type Hash, type TransactionReceipt } from 'viem'

/** EntryPoint v0.7 — transactions sponsorisées Privy (ERC-4337). */
export const PORTAL_ENTRYPOINT_V07_ADDRESS =
  '0x0000000071727de22e5e9d8baf0edac6f37da032' as const

const USER_OPERATION_EVENT_TOPIC = keccak256(
  toHex('UserOperationEvent(bytes32,address,address,uint256,bool,uint256,uint256)'),
)

type ReceiptLike = Pick<TransactionReceipt, 'to' | 'status' | 'logs'>

/** Décode le bool `success` des logs UserOperationEvent (EntryPoint v0.7). */
export function readEntryPointUserOperationSuccess(receipt: ReceiptLike): boolean | null {
  const entryPoint = PORTAL_ENTRYPOINT_V07_ADDRESS.toLowerCase()
  if (receipt.to?.toLowerCase() !== entryPoint) return null

  let sawEvent = false
  for (const log of receipt.logs) {
    if (log.address.toLowerCase() !== entryPoint) continue
    if (log.topics[0]?.toLowerCase() !== USER_OPERATION_EVENT_TOPIC.toLowerCase()) continue

    sawEvent = true
    const [, success] = decodeAbiParameters(
      [{ type: 'uint256' }, { type: 'bool' }, { type: 'uint256' }, { type: 'uint256' }],
      log.data,
    )
    if (!success) return false
  }

  return sawEvent ? true : null
}

/** Statut métier d'une tx portail — tient compte des UserOps Privy reverties dans un bundle réussi. */
export function resolvePortalTransactionReceiptStatus(receipt: ReceiptLike): 'success' | 'reverted' {
  if (receipt.status !== 'success') return 'reverted'

  const userOpSuccess = readEntryPointUserOperationSuccess(receipt)
  if (userOpSuccess === null) return 'success'
  return userOpSuccess ? 'success' : 'reverted'
}

export type VerifiedPortalTxReceipt = {
  txHash: Hash
  chainId: number
  blockNumber: bigint
  status: 'success' | 'reverted'
}
