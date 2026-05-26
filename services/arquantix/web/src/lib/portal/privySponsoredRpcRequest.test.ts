import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import {
  buildPrivyAuthorizationSignatureInput,
  buildPrivyEthSendTransactionRpcBody,
  buildPrivyWalletRpcUrl,
} from '@/lib/portal/privySponsoredRpcRequest'

describe('privySponsoredRpcRequest', () => {
  it('builds a stable sponsored eth_sendTransaction RPC body', () => {
    const body = buildPrivyEthSendTransactionRpcBody({
      chainId: 8453,
      to: '0xAbCdEf0123456789012345678901234567890AbCd',
      data: '0xAABBCC',
      value: '1000000',
      gasLimit: '21000',
    })

    assert.deepEqual(body, {
      method: 'eth_sendTransaction',
      caip2: 'eip155:8453',
      chain_type: 'ethereum',
      sponsor: true,
      params: {
        transaction: {
          to: '0xabcdef0123456789012345678901234567890abcd',
          data: '0xaabbcc',
          value: '0xf4240',
          gas_limit: '0x5208',
        },
      },
    })
  })

  it('builds authorization signature input for wallet rpc', () => {
    const rpcBody = buildPrivyEthSendTransactionRpcBody({
      chainId: 8453,
      to: '0xabcdef0123456789012345678901234567890abcd',
      data: '0x',
    })

    const input = buildPrivyAuthorizationSignatureInput({
      appId: 'app-id-test',
      privyWalletId: 'wallet-id-abc',
      rpcBody,
    })

    assert.equal(input.url, buildPrivyWalletRpcUrl('wallet-id-abc'))
    assert.equal(input.headers['privy-app-id'], 'app-id-test')
    assert.equal(input.body, rpcBody)
  })
})
