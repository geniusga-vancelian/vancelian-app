import { afterEach, describe, it } from 'node:test'
import assert from 'node:assert/strict'

import {
  buildPrivyDevMockWalletAddress,
  buildPrivyDevStubAccessToken,
  isPortalPrivyOtpDevMockCode,
} from './privyOtpDevMock'

describe('privyOtpDevMock', () => {
  const prevNodeEnv = process.env.NODE_ENV
  const prevEnabled = process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED
  const prevCode = process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE

  afterEach(() => {
    process.env.NODE_ENV = prevNodeEnv
    if (prevEnabled === undefined) {
      delete process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED
    } else {
      process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED = prevEnabled
    }
    if (prevCode === undefined) {
      delete process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE
    } else {
      process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE = prevCode
    }
  })

  it('builds stable stub token from email', () => {
    assert.equal(
      buildPrivyDevStubAccessToken('User@Example.com'),
      'stub:local-dev:user@example.com',
    )
  })

  it('builds distinct mock wallet addresses per email', () => {
    const a = buildPrivyDevMockWalletAddress('alice@local.dev')
    const b = buildPrivyDevMockWalletAddress('bob@local.dev')
    assert.match(a, /^0x[0-9a-f]{40}$/)
    assert.notEqual(a, b)
    assert.equal(buildPrivyDevMockWalletAddress('alice@local.dev'), a)
  })

  it('accepts fixed code only when mock enabled', () => {
    process.env.NODE_ENV = 'development'
    process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_MOCK_ENABLED = 'true'
    process.env.NEXT_PUBLIC_PORTAL_PRIVY_OTP_DEV_FIXED_CODE = '111111'
    assert.equal(isPortalPrivyOtpDevMockCode('111111'), true)
    assert.equal(isPortalPrivyOtpDevMockCode('222222'), false)
  })
})
