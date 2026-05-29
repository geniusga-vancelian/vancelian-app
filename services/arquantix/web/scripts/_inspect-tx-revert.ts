import { decodeAbiParameters, keccak256, toHex } from 'viem'

import { createBasePublicClient } from '@/lib/blockchain/baseRpcProvider'
import {
  PORTAL_ENTRYPOINT_V07_ADDRESS,
  readEntryPointUserOperationSuccess,
  resolvePortalTransactionReceiptStatus,
} from '@/lib/portal/portalTransactionReceiptStatus'

const hash = (process.argv[2] ||
  '0x77a6e07850abe789fea8b2f60bfe92fcdca2c8beb7612293e159e35885395a3f') as `0x${string}`

const USER_OP_TOPIC = keccak256(
  toHex('UserOperationEvent(bytes32,address,address,uint256,bool,uint256,uint256)'),
)

async function main() {
  const client = createBasePublicClient({ side: 'server' })
  const [tx, receipt] = await Promise.all([
    client.getTransaction({ hash }),
    client.getTransactionReceipt({ hash }),
  ])

  const summary: Record<string, unknown> = {
    hash,
    from: tx.from,
    to: tx.to,
    blockNumber: receipt.blockNumber.toString(),
    receiptStatus: receipt.status,
    businessStatus: resolvePortalTransactionReceiptStatus(receipt),
    userOpSuccess: readEntryPointUserOperationSuccess(receipt),
    logs: receipt.logs.map((log) => ({
      address: log.address,
      topic0: log.topics[0],
    })),
  }

  for (const log of receipt.logs) {
    if (
      log.address.toLowerCase() === PORTAL_ENTRYPOINT_V07_ADDRESS.toLowerCase() &&
      log.topics[0]?.toLowerCase() === USER_OP_TOPIC.toLowerCase()
    ) {
      const [, success, actualGasCost, actualGasUsed] = decodeAbiParameters(
        [
          { type: 'uint256' },
          { type: 'bool' },
          { type: 'uint256' },
          { type: 'uint256' },
        ],
        log.data,
      )
      summary.userOpEvent = {
        success,
        actualGasCost: actualGasCost.toString(),
        actualGasUsed: actualGasUsed.toString(),
      }
    }
  }

  console.log(JSON.stringify(summary, null, 2))
}

main().catch((e) => {
  console.error(e)
  process.exit(1)
})
